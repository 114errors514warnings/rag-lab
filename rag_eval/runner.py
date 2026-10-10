"""固定评测协议运行器。

用法（每完成一个阶段跑一次，参数完全相同）：
    python -m rag_eval.runner --stage S1 --system stub_dense --freeze
    python -m rag_eval.runner --stage S3 --system stub_hybrid --baseline S3__stub_dense

`--baseline` 可以是：报告 json 路径 / 冻结名（baselines/<name>.json）/ "latest"。
报告写入 reports/，冻结副本写入 baselines/。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import EVAL_VERSION
from .metrics import (
    citation_precision,
    hit_at_1,
    leakage_rate,
    mean_or_zero,
    mrr,
    percentile,
    precision_at_k,
    recall_at_k,
)
from .schema import EvalCase, Report, SuiteResult, SystemAnswer
from .sut import REGISTRY

ROOT = Path(__file__).resolve().parents[1]
SUITE_DIR = ROOT / "data" / "eval_suites"
GATES_PATH = ROOT / "rag_eval" / "gates.json"
REPORTS_DIR = ROOT / "reports"
BASELINES_DIR = ROOT / "baselines"


# --------------------------------------------------------------------------- 加载

def load_suite(name: str) -> tuple[list[EvalCase], str]:
    path = SUITE_DIR / f"{name}.jsonl"
    if not path.exists():
        raise SystemExit(f"[suite 缺失] {path} 不存在。该阶段的测试套件需先编写。")
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()[:16]
    cases: list[EvalCase] = []
    for lineno, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            cases.append(EvalCase(**json.loads(line)))
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"[suite 格式错误] {path}:{lineno} -> {exc}") from exc
    return cases, sha


def load_gates() -> dict:
    return json.loads(GATES_PATH.read_text(encoding="utf-8"))


def resolve_baseline(ref: str | None) -> Report | None:
    if not ref:
        return None
    if ref == "latest":
        path = BASELINES_DIR / "latest.json"
    else:
        candidate = Path(ref)
        if candidate.exists():
            path = candidate
        else:
            path = BASELINES_DIR / f"{ref}.json"
    if not path.exists():
        raise SystemExit(f"[baseline 缺失] {path} 不存在。")
    return Report(**json.loads(path.read_text(encoding="utf-8")))


def git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
    except Exception:  # noqa: BLE001
        return None
    return (out.stdout.strip() or None) if out.returncode == 0 else None


# --------------------------------------------------------------------------- 评测

def evaluate_suite(sut, suite: str, cases: list[EvalCase], sha: str, k: int) -> SuiteResult:
    per_case: list[dict] = []
    recall_all: list[float] = []
    precision_all: list[float] = []
    mrr_all: list[float] = []
    hit_all: list[float] = []
    cite_prec: list[float] = []
    missing_cite: list[float] = []
    leakage: list[float] = []
    recall_by_split: dict[str, list[float]] = {"dev": [], "holdout": []}
    errors = 0

    for case in cases:
        started = time.perf_counter()
        try:
            ans: SystemAnswer = sut.answer(case, k)
        except Exception as exc:  # noqa: BLE001
            ans = SystemAnswer(error=f"{type(exc).__name__}: {exc}")
        measured_ms = (time.perf_counter() - started) * 1000.0
        ranked = [c.chunk_id for c in ans.retrieved]
        row: dict = {
            "case_id": case.id,
            "split": case.split,
            "question": case.question,
            "retrieved": ranked,
            "relevant": case.relevant_chunk_ids,
            "citations": ans.citations,
            "latency_ms": round(ans.latency_ms or measured_ms, 3),
            "cost_usd": ans.cost_usd,
            "prompt_tokens": ans.prompt_tokens,
            "error": ans.error,
        }

        if ans.error:
            errors += 1
        else:
            if case.relevant_chunk_ids:
                r = recall_at_k(ranked, case.relevant_chunk_ids, k)
                recall_all.append(r)
                precision_all.append(precision_at_k(ranked, case.relevant_chunk_ids, k))
                mrr_all.append(mrr(ranked, case.relevant_chunk_ids))
                hit_all.append(hit_at_1(ranked, case.relevant_chunk_ids))
                recall_by_split.setdefault(case.split, []).append(r)
                row["recall@k"] = round(r, 4)

            cp = citation_precision(ans.citations, case.relevant_chunk_ids)
            if cp is not None:
                cite_prec.append(cp)
                row["citation_precision"] = round(cp, 4)
            missing_cite.append(0.0 if ans.citations else 1.0)

            lr = leakage_rate(
                ranked,
                case.project_id,
                {c.chunk_id: (c.project_id or case.project_id or "") for c in ans.retrieved},
            )
            if lr is not None:
                leakage.append(lr)
                row["leakage_rate"] = round(lr, 4)

        per_case.append(row)

    latencies = [row["latency_ms"] for row in per_case]
    costs = [row["cost_usd"] for row in per_case]
    n = len(cases) or 1

    metrics: dict[str, float] = {
        "cases": float(len(cases)),
        "success_rate": round(1.0 - errors / n, 4),
        "error_rate": round(errors / n, 4),
        f"recall@{k}": round(mean_or_zero(recall_all), 4),
        f"precision@{k}": round(mean_or_zero(precision_all), 4),
        "mrr": round(mean_or_zero(mrr_all), 4),
        "hit@1": round(mean_or_zero(hit_all), 4),
        "citation_precision": round(mean_or_zero(cite_prec), 4),
        "citation_missing_rate": round(mean_or_zero(missing_cite), 4),
        "leakage_rate": round(mean_or_zero(leakage), 4),
        "avg_latency_ms": round(mean_or_zero(latencies), 3),
        "p50_latency_ms": round(percentile(latencies, 0.5), 3),
        "p95_latency_ms": round(percentile(latencies, 0.95), 3),
        "avg_prompt_tokens": round(mean_or_zero([r["prompt_tokens"] for r in per_case]), 2),
        "cost_per_query_usd": round(mean_or_zero(costs), 8),
        "total_cost_usd": round(sum(costs), 8),
    }
    for split, values in recall_by_split.items():
        if values:
            metrics[f"recall@{k}[{split}]"] = round(mean_or_zero(values), 4)

    return SuiteResult(
        suite=suite,
        sha256=sha,
        n_cases=len(cases),
        n_cases_with_labels=sum(1 for c in cases if c.relevant_chunk_ids),
        k=k,
        metrics=metrics,
        per_case=per_case,
    )


# --------------------------------------------------------------------------- 判定

def _verdict(current: float | None, baseline: float | None, rule: dict) -> tuple[str, str, float | None]:
    if current is None:
        return "NO_GATE", "指标未产出", None
    delta = None if baseline is None else round(current - baseline, 4)
    checks: list[tuple[bool, str]] = []

    if "max" in rule:
        checks.append((current <= rule["max"], f"绝对上限 {rule['max']}"))
    if "min_delta" in rule:
        if baseline is None:
            return "BASELINE", "缺少 baseline，无法判定增量", None
        checks.append((delta >= rule["min_delta"], f"需提升 >={rule['min_delta']}"))
    if "max_delta" in rule:
        if baseline is None:
            return "BASELINE", "缺少 baseline，无法判定回退", None
        checks.append((delta >= rule["max_delta"], f"回退不得超过 {abs(rule['max_delta'])}"))
    if not checks:
        return "NO_GATE", "该阶段未定义门禁", delta

    failed = [desc for ok, desc in checks if not ok]
    if failed:
        return "FAIL", "未满足：" + "；".join(failed), delta
    if baseline is None:
        return "PASS", "（无 baseline，仅按绝对上限判定）", None
    return "PASS", "全部满足", delta


def gate_check(stage: str, cfg: dict, suite: SuiteResult, baseline: Report | None) -> list[dict]:
    findings: list[dict] = []
    base_suite = None
    if baseline is not None:
        base_suite = baseline.suites.get(suite.suite)
        if base_suite is not None and base_suite.sha256 != suite.sha256:
            findings.append({
                "suite": suite.suite, "metric": "(suite_sha256)", "role": "integrity",
                "baseline": base_suite.sha256, "current": suite.sha256, "delta": None,
                "verdict": "FAIL",
                "note": "数据集已被修改：历史对比失效（固定测试方法要求数据集冻结）",
            })
            base_suite = None

    for role, rules in (("primary", cfg.get("primary", {})), ("guardrail", cfg.get("guardrails", {}))):
        for metric, rule in rules.items():
            current = suite.metrics.get(metric)
            base_value = base_suite.metrics.get(metric) if base_suite else None
            verdict, note, delta = _verdict(current, base_value, rule)
            findings.append({
                "suite": suite.suite, "metric": metric, "role": role,
                "baseline": base_value, "current": current, "delta": delta,
                "rule": rule, "verdict": verdict, "note": note,
            })
    return findings


# --------------------------------------------------------------------------- 报告

def render_markdown(report: Report, baseline: Report | None, findings: list[dict]) -> str:
    lines: list[str] = []
    lines.append(f"# 阶段评测报告 · {report.stage}")
    lines.append("")
    lines.append(f"- 系统：`{report.system}`")
    lines.append(f"- 配置指纹：`{report.system_config_hash}`")
    lines.append(f"- 评测协议版本：`{report.eval_version}`　生成时间：`{report.generated_at}`")
    lines.append(f"- git commit：`{report.git_commit or 'n/a'}`")
    if baseline is not None:
        lines.append(f"- 对比基线：`{baseline.stage} / {baseline.system}`")
    else:
        lines.append("- 对比基线：**无（本次结果即 baseline 数值）**")
    lines.append("")

    for name, suite in report.suites.items():
        base_suite = baseline.suites.get(name) if baseline else None
        lines.append(f"## 套件 `{name}`（sha256 `{suite.sha256}`，k={suite.k}）")
        lines.append("")
        lines.append(f"用例数 {suite.n_cases}，其中带标注 {suite.n_cases_with_labels} 条。")
        lines.append("")
        lines.append("| 指标 | 基线 | 本次 | Δ | 判定 | 说明 |")
        lines.append("|---|---|---|---|---|---|")
        rows = [f for f in findings if f["suite"] == name]
        shown = {f["metric"] for f in rows}
        for f in rows:
            base_txt = "-" if f["baseline"] is None else f"{f['baseline']}"
            cur_txt = "-" if f["current"] is None else f"{f['current']}"
            delta_txt = "-" if f["delta"] is None else f"{f['delta']:+.4f}"
            lines.append(f"| {f['metric']} | {base_txt} | {cur_txt} | {delta_txt} | "
                         f"{f['verdict']} | {f['note']} |")
        for metric, cur in suite.metrics.items():
            if metric in shown or metric == "cases":
                continue
            base = base_suite.metrics.get(metric) if base_suite else None
            base_txt = "-" if base is None else f"{base}"
            delta_txt = "-" if base is None else f"{cur - base:+.4f}"
            lines.append(f"| {metric} | {base_txt} | {cur} | {delta_txt} | 观察项 | 未设门禁 |")
        lines.append("")

    fails = [f for f in findings if f["verdict"] == "FAIL"]
    lines.append("## 结论")
    lines.append("")
    if fails:
        for f in fails:
            lines.append(f"- **FAIL**：`{f['suite']}` / `{f['metric']}` — {f['note']}")
    else:
        lines.append("- 全部门禁通过（或该阶段未定义门禁）。")
    for f in findings:
        if f["verdict"] in ("BASELINE", "WARN", "NO_GATE"):
            lines.append(f"- 提示：`{f['suite']}` / `{f['metric']}` — {f['note']}")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="固定评测协议运行器")
    parser.add_argument("--stage", required=True, help="阶段标识，如 S1 / S3 / M2")
    parser.add_argument("--system", required=True, help=f"被测系统，可选：{', '.join(REGISTRY)}")
    parser.add_argument("--baseline", default=None, help="基线报告路径 / 冻结名 / latest")
    parser.add_argument("--k", type=int, default=None, help="覆盖 gates.json 中的 k")
    parser.add_argument("--suite", default=None, help="只跑指定套件（默认跑阶段配置的全部）")
    parser.add_argument("--freeze", action="store_true", help="把本次报告冻结为基线")
    args = parser.parse_args(argv)

    gates = load_gates()
    stage_cfg = gates["stages"].get(args.stage)
    if stage_cfg is None:
        raise SystemExit(f"[未定义阶段] {args.stage}；可选：{', '.join(gates['stages'])}")
    if args.system not in REGISTRY:
        raise SystemExit(f"[未注册系统] {args.system}；可选：{', '.join(REGISTRY)}")

    suite_names = [args.suite] if args.suite else list(stage_cfg.get("suites", []))
    if not suite_names:
        print(f"[跳过] 阶段 {args.stage} 尚未配置测试套件：{stage_cfg.get('note', '')}")
        return 0

    k = args.k or int(stage_cfg.get("k", 3))
    baseline = resolve_baseline(args.baseline)
    sut = REGISTRY[args.system]()

    report = Report(
        stage=args.stage,
        system=getattr(sut, "name", args.system),
        system_config_hash=getattr(sut, "config_hash", "n/a"),
        eval_version=EVAL_VERSION,
        generated_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        git_commit=git_commit(),
    )

    findings: list[dict] = []
    for suite_name in suite_names:
        cases, sha = load_suite(suite_name)
        result = evaluate_suite(sut, suite_name, cases, sha, k)
        report.suites[suite_name] = result
        findings.extend(gate_check(args.stage, stage_cfg, result, baseline))
    report.findings = findings

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    json_path = REPORTS_DIR / f"{stamp}_{args.stage}_{args.system}.json"
    md_path = REPORTS_DIR / f"{stamp}_{args.stage}_{args.system}.md"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report, baseline, findings), encoding="utf-8")

    print(f"== stage={args.stage} system={args.system} cfg={report.system_config_hash} k={k} ==")
    for f in findings:
        base = "-" if f["baseline"] is None else f"{f['baseline']}"
        cur = "-" if f["current"] is None else f"{f['current']}"
        delta = "-" if f["delta"] is None else f"{f['delta']:+.4f}"
        print(f"[{f['verdict']:<8}] {f['metric']:<24} base={base:<10} cur={cur:<10} "
              f"delta={delta:<9} | {f['note']}")
    print(f"report -> {json_path}")
    print(f"report -> {md_path}")

    if args.freeze:
        BASELINES_DIR.mkdir(parents=True, exist_ok=True)
        name = f"{args.stage}__{args.system}"
        payload = report.model_dump_json(indent=2)
        (BASELINES_DIR / f"{name}.json").write_text(payload, encoding="utf-8")
        (BASELINES_DIR / "latest.json").write_text(payload, encoding="utf-8")
        print(f"frozen -> {BASELINES_DIR / (name + '.json')}")

    return 1 if any(f["verdict"] == "FAIL" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())




