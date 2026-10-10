"""v2 指标计算：证据制 + 宏/微平均 + 分组。

指标定义见 `rag_eval/evidence.py` 与 `rag_eval/metrics.py` 顶部注释。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean

from rag_eval.evidence import (
    evidence_coverage_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    normalize_gold_sets,
    precision_vs_evidence,
)
from rag_eval.metrics import mean_or_zero, micro_average, percentile

UNIT_KEYS = ("source", "start_line", "end_line", "symbol", "project_id")


@dataclass
class CaseScore:
    case_id: str
    query_type: str
    split: str
    coverage: float          # recall@k（覆盖式）
    precision: float
    mrr: float
    ndcg: float
    context_coverage: float
    answer_accuracy: float
    no_answer_correct: float | None
    citation_support: float | None
    latency_ms: float
    cost_usd: float


def _units(ans) -> list[dict]:
    return [{k: getattr(c, k) for k in UNIT_KEYS} for c in ans.retrieved]


def _context_units(ans) -> list[dict]:
    keep = set(ans.context_chunk_ids)
    return [{k: getattr(c, k) for k in UNIT_KEYS} for c in ans.retrieved if c.chunk_id in keep]


def score_case(case, ans, k: int) -> CaseScore:
    gold_sets = normalize_gold_sets(case.gold_evidence)
    units = _units(ans)
    ctx = _context_units(ans)

    base = dict(
        case_id=case.id,
        query_type=case.query_type or "unknown",
        split=case.split,
        latency_ms=round(ans.latency_ms, 3),
        cost_usd=ans.cost_usd,
    )

    if case.query_type == "no_answer":
        correct = 1.0 if ans.refused else 0.0
        return CaseScore(
            coverage=0.0, precision=0.0, mrr=0.0, ndcg=0.0, context_coverage=0.0,
            answer_accuracy=correct, no_answer_correct=correct, citation_support=None,
            latency_ms=base["latency_ms"], cost_usd=base["cost_usd"],
            case_id=case.id, query_type=base["query_type"], split=case.split,
        )

    coverage = evidence_coverage_at_k(units, gold_sets, k) if gold_sets else 0.0
    precision = precision_vs_evidence(units, gold_sets, k) if gold_sets else 0.0
    mrr = mean_reciprocal_rank(units, gold_sets) if gold_sets else 0.0
    ndcg = ndcg_at_k(units, gold_sets, k) if gold_sets else 0.0
    ctx_cov = evidence_coverage_at_k(ctx, gold_sets, len(ctx) or 1) if gold_sets else 0.0

    all_evidence = [e for s in gold_sets for e in s]

    def matches(unit: dict) -> bool:
        from rag_eval.evidence import unit_matches_evidence

        return any(unit_matches_evidence(unit, e) for e in all_evidence)

    # Citation Support：引用单元中命中证据的比例（无引用记 0）
    cite_units = [
        {k: getattr(c, k) for k in UNIT_KEYS}
        for c in ans.retrieved if c.chunk_id in set(ans.citations)
    ]
    citation_support = (
        sum(1 for u in cite_units if matches(u)) / len(cite_units) if cite_units else 0.0
    )

    # Answer Accuracy（rubric 代理）：召回覆盖 且 有引用
    answered = coverage == 1.0 and bool(ans.citations)
    answer_accuracy = 1.0 if answered else 0.0

    return CaseScore(
        case_id=case.id, query_type=base["query_type"], split=case.split,
        coverage=coverage, precision=precision, mrr=mrr, ndcg=ndcg,
        context_coverage=ctx_cov, answer_accuracy=answer_accuracy,
        no_answer_correct=None, citation_support=round(citation_support, 4),
        latency_ms=base["latency_ms"], cost_usd=base["cost_usd"],
    )


def aggregate(scores: list[CaseScore], k: int) -> dict:
    answerable = [s for s in scores if s.no_answer_correct is None]
    no_answer = [s for s in scores if s.no_answer_correct is not None]

    def col(rows, name):
        return [getattr(r, name) for r in rows if getattr(r, name) is not None]

    latencies = col(scores, "latency_ms")
    costs = col(scores, "cost_usd")
    metrics = {
        "cases": float(len(scores)),
        f"recall@{k}": round(micro_average(col(answerable, "coverage")), 4),
        f"precision@{k}": round(micro_average(col(answerable, "precision")), 4),
        f"mrr@{k}": round(micro_average(col(answerable, "mrr")), 4),
        f"ndcg@{k}": round(micro_average(col(answerable, "ndcg")), 4),
        "context_evidence_coverage": round(micro_average(col(answerable, "context_coverage")), 4),
        "answer_accuracy": round(micro_average(col(scores, "answer_accuracy")), 4),
        "no_answer_accuracy": round(micro_average(col(no_answer, "no_answer_correct")), 4),
        "citation_support": round(micro_average(col(answerable, "citation_support")), 4),
        "avg_latency_ms": round(mean_or_zero(latencies), 3),
        "p95_latency_ms": round(percentile(latencies, 0.95), 3),
        "cost_per_query_usd": round(mean_or_zero(costs), 8),
    }

    # 宏平均 + 分组
    groups: dict[str, dict[str, list[float]]] = {}
    for s in answerable:
        g = groups.setdefault(s.query_type, {})
        for name, key in (("coverage", f"recall@{k}"), ("precision", f"precision@{k}"),
                          ("mrr", f"mrr@{k}"), ("ndcg", f"ndcg@{k}"),
                          ("context_coverage", "context_evidence_coverage")):
            g.setdefault(key, []).append(getattr(s, name))
    for key in (f"recall@{k}", f"precision@{k}", f"mrr@{k}", f"ndcg@{k}", "context_evidence_coverage"):
        per_type = {t: round(mean(v[key]), 4) for t, v in groups.items() if v.get(key)}
        metrics[f"macro_{key}"] = round(mean_or_zero(list(per_type.values())), 4)
        for t, val in per_type.items():
            metrics[f"{key}[{t}]"] = val

    metrics["n_answerable"] = float(len(answerable))
    metrics["n_no_answer"] = float(len(no_answer))
    return metrics


def case_scores(scores: list[CaseScore]) -> list[dict]:
    return [asdict(s) for s in scores]
