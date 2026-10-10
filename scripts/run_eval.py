"""配置驱动的实验运行器（E00–E12）。

一条命令：加载配置 -> 构建被测系统 -> 跑 Golden -> 打分 -> 落 trace/report -> 判定。
产物：``reports/{run_id}/{metrics.json, cases.jsonl, errors.csv, comparison.md}`` 与
``traces/{run_id}.jsonl``。

``--baseline`` 可给另一个 run_id 或 metrics.json 路径，做 A/B 配对 + bootstrap CI。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_engine.config import EngineConfig  # noqa: E402
from rag_engine.eval_adapter import MyPipeline  # noqa: E402
from rag_eval import EVAL_VERSION  # noqa: E402
from rag_eval.metrics import paired_bootstrap_ci  # noqa: E402
from rag_lab.config import ExperimentConfig  # noqa: E402
from rag_lab.golden import by_query_type, filter_split, load_cases  # noqa: E402
from rag_lab.scoring import aggregate, case_scores, score_case  # noqa: E402
from rag_lab.trace import build_trace, write_traces  # noqa: E402

REPORTS = ROOT / "reports"
TRACES = ROOT / "traces"
SNAPSHOTS = ROOT / "snapshots"


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
    except Exception:  # noqa: BLE001
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def _snapshot_digest() -> str:
    path = SNAPSHOTS / "kb.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")).get("digest", "none")
    return "none"


def resolve_baseline(ref: str | None) -> dict | None:
    if not ref:
        return None
    candidate = Path(ref)
    if candidate.is_file():
        return json.loads(candidate.read_text(encoding="utf-8"))
    path = REPORTS / ref / "metrics.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    raise SystemExit(f"[baseline 缺失] 找不到 run_id 或 metrics.json：{ref}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="实验运行器")
    parser.add_argument("--config", required=True, help="configs/E0x.yaml 路径")
    parser.add_argument("--baseline", default=None, help="对比 run_id 或 metrics.json")
    parser.add_argument("--run-id", default=None, help="自定义 run_id")
    args = parser.parse_args(argv)

    cfg = ExperimentConfig.from_file(ROOT / args.config if not Path(args.config).is_absolute()
                                     else args.config)

    engine = EngineConfig(**cfg.system)
    sut = MyPipeline(engine)
    actual = sut._ensure().config  # noqa: SLF001 - 取实际生效配置用于 run_id

    cases, data_sha = load_cases(ROOT / cfg.dataset)
    cases = filter_split(cases, cfg.suite_split)

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_id = args.run_id or f"{stamp}_{cfg.experiment_id}_{actual.fingerprint()}"
    commit = _git_commit() or "nogit"
    snap = _snapshot_digest()
    full_run_id = f"{run_id}_{commit}_{snap}_{data_sha}" if not args.run_id else run_id

    traces: list[dict] = []
    scores = []
    errors: list[dict] = []
    for case in cases:
        try:
            ans = sut.answer(case, cfg.k)
        except Exception as exc:  # noqa: BLE001
            from rag_eval.schema import SystemAnswer

            ans = SystemAnswer(error=f"{type(exc).__name__}: {exc}")
        score = score_case(case, ans, cfg.k)
        scores.append(score)
        trace = build_trace(case, ans, k=cfg.k, system=sut.name, config_hash=actual.fingerprint())
        traces.append(trace)
        if trace["first_failure_stage"]:
            errors.append({
                "case_id": case.id, "query_type": case.query_type, "split": case.split,
                "first_failure_stage": trace["first_failure_stage"],
                "question": case.question,
                "gold_evidence": json.dumps(case.gold_evidence, ensure_ascii=False),
                "retrieved": json.dumps(trace["retrieval"], ensure_ascii=False),
            })

    metrics = aggregate(scores, cfg.k)
    baseline = resolve_baseline(args.baseline)

    findings = _gate_findings(cfg.gates, metrics, baseline)
    deltas = _paired(baseline, scores) if baseline else {}

    out_dir = REPORTS / full_run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    trace_path = TRACES / f"{full_run_id}.jsonl"
    write_traces(trace_path, traces)

    report = {
        "run_id": full_run_id,
        "experiment_id": cfg.experiment_id,
        "description": cfg.description,
        "suite_split": cfg.suite_split,
        "k": cfg.k,
        "eval_version": EVAL_VERSION,
        "system": sut.name,
        "config_hash": actual.fingerprint(),
        "git_commit": _git_commit(),
        "snapshot_digest": snap,
        "dataset": cfg.dataset,
        "dataset_sha256": data_sha,
        "n_cases": len(cases),
        "query_types": {t: len(v) for t, v in by_query_type(cases).items()},
        "trace_completeness": round(
            sum(1 for t in traces if t.get("retrieval")) / (len(traces) or 1), 4
        ),
        "metrics": metrics,
        "findings": findings,
        "paired_vs_baseline": deltas,
        "baseline": args.baseline,
        "config": cfg.system,
    }
    (out_dir / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(out_dir / "cases.jsonl", "w", encoding="utf-8") as fh:
        for row in case_scores(scores):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(out_dir / "errors.csv", "w", encoding="utf-8") as fh:
        fh.write("case_id,query_type,split,first_failure_stage,question\n")
        for e in errors:
            fh.write(f"{e['case_id']},{e['query_type']},{e['split']},{e['first_failure_stage']},"
                     f"\"{e['question']}\"\n")
    (out_dir / "comparison.md").write_text(
        _render_md(report, findings, deltas), encoding="utf-8")

    print(f"== run_id={full_run_id} ==")
    for metric in ("recall@5", "precision@5", "mrr@5", "ndcg@5",
                   "context_evidence_coverage", "answer_accuracy",
                   "no_answer_accuracy", "citation_support", "p95_latency_ms"):
        if metric in metrics:
            print(f"  {metric:<28} = {metrics[metric]}")
    for f in findings:
        print(f"  [{f['verdict']:<8}] {f['metric']:<26} cur={f['current']} {f['note']}")
    print(f"  trace_completeness = {report['trace_completeness']}")
    print(f"report -> {out_dir / 'metrics.json'}")
    print(f"trace  -> {trace_path}")

    return 1 if any(f["verdict"] == "FAIL" for f in findings) else 0


def _gate_findings(gates: dict, metrics: dict, baseline: dict | None) -> list[dict]:
    findings: list[dict] = []
    for metric, rule in (gates or {}).items():
        current = metrics.get(metric)
        base_value = (baseline or {}).get("metrics", {}).get(metric) if baseline else None
        verdict, note = "PASS", "全部满足"
        if current is None:
            findings.append({"metric": metric, "current": None, "baseline": base_value,
                             "verdict": "NO_GATE", "note": "指标未产出"})
            continue
        if "max" in rule and current > rule["max"]:
            verdict, note = "FAIL", f"越绝对上限 {rule['max']}"
        if "min_delta" in rule:
            if base_value is None:
                verdict, note = "BASELINE", "缺 baseline，无法判定增量"
            elif current - base_value < rule["min_delta"]:
                verdict, note = "FAIL", f"Δ<{rule['min_delta']}"
        if "max_delta" in rule and base_value is not None and current - base_value < rule["max_delta"]:
            verdict, note = "FAIL", f"回退超过 {abs(rule['max_delta'])}"
        findings.append({"metric": metric, "current": current, "baseline": base_value,
                         "verdict": verdict, "note": note})
    return findings


def _paired(baseline: dict, scores) -> dict:
    """与基线的逐题配对 + bootstrap CI（按 case_id 对齐）。"""
    base_run = baseline.get("run_id")
    if not base_run:
        return {}
    cases_path = REPORTS / base_run / "cases.jsonl"
    if not cases_path.exists():
        return {}
    base_cases = {}
    with open(cases_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                row = json.loads(line)
                base_cases[row["case_id"]] = row
    out: dict = {}
    for metric in ("coverage", "ndcg", "context_coverage", "answer_accuracy"):
        deltas = []
        for s in scores:
            if s.no_answer_correct is not None and metric != "answer_accuracy":
                continue
            b = base_cases.get(s.case_id)
            if b is None:
                continue
            deltas.append(getattr(s, metric) - b.get(metric, 0.0))
        if deltas:
            lo, hi, crosses = paired_bootstrap_ci(deltas)
            out[metric] = {
                "mean_delta": round(sum(deltas) / len(deltas), 4),
                "ci95": [lo, hi],
                "inconclusive": crosses,
                "n": len(deltas),
            }
    return out


def _render_md(report: dict, findings: list[dict], deltas: dict) -> str:
    lines = [
        f"# 实验报告 · {report['experiment_id']}", "",
        f"- run_id：`{report['run_id']}`",
        f"- 系统：`{report['system']}`　配置指纹：`{report['config_hash']}`",
        f"- 协议版本：`{report['eval_version']}`　数据快照：`{report['snapshot_digest']}`　"
        f"数据集 sha：`{report['dataset_sha256']}`",
        f"- 套件：`{report['dataset']}`（split={report['suite_split']}, k={report['k']}, "
        f"n={report['n_cases']}）",
        f"- trace 完整率：`{report['trace_completeness']}`", "",
        f"- 题型分布：`{report['query_types']}`", "",
        "## 指标", "", "| 指标 | 值 |", "|---|---|",
    ]
    for metric, value in report["metrics"].items():
        lines.append(f"| {metric} | {value} |")
    lines += ["", "## 门槛判定", "", "| 指标 | 基线 | 本次 | 判定 | 说明 |", "|---|---|---|---|---|"]
    for f in findings:
        lines.append(f"| {f['metric']} | {f.get('baseline')} | {f.get('current')} | "
                     f"{f['verdict']} | {f['note']} |")
    if deltas:
        lines += ["", "## 与基线配对（95% CI）", "", "| 指标 | 均值Δ | CI95 | 结论 |", "|---|---|---|---|"]
        for metric, d in deltas.items():
            concl = "证据不足（跨 0）" if d["inconclusive"] else "显著"
            lines.append(f"| {metric} | {d['mean_delta']:+.4f} | "
                         f"[{d['ci95'][0]}, {d['ci95'][1]}] | {concl} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
