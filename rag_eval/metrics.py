"""指标实现（固定资产：口径一旦修改必须 bump EVAL_VERSION）。

指标口径（固定约定）：
- recall@K     = |relevant ∩ topK| / |relevant|，无标注用例不计入均值
- precision@K  = |relevant ∩ topK| / |topK|
- mrr          = 1 / 首个相关结果的排名（无命中记 0）
- hit@1        = 命中即 1.0
- citation_precision    = |引用 ∩ 相关| / |引用|（仅统计有引用的用例）
- citation_missing_rate = 无引用用例占比（阶段 1 的"来源可回溯"护栏）
- error_rate   = 抛错用例占比
- leakage_rate = 检索结果中不属于该用例 project 的 chunk 占比（阶段 5 护栏，必须为 0）
"""

from __future__ import annotations

from statistics import mean
from typing import Sequence


def _div(a: float, b: float) -> float:
    return float(a) / float(b) if b else 0.0


def recall_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = set(ranked[:k])
    return _div(len(top & set(relevant)), len(set(relevant)))


def precision_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    top = list(ranked[:k])
    if not top:
        return 0.0
    return _div(len(set(top) & set(relevant)), len(top))


def mrr(ranked: Sequence[str], relevant: Sequence[str]) -> float:
    rel = set(relevant)
    for rank, cid in enumerate(ranked, start=1):
        if cid in rel:
            return 1.0 / rank
    return 0.0


def hit_at_1(ranked: Sequence[str], relevant: Sequence[str]) -> float:
    return 1.0 if ranked and ranked[0] in set(relevant) else 0.0


def citation_precision(citations: Sequence[str], relevant: Sequence[str]) -> float | None:
    if not citations:
        return None
    return _div(len(set(citations) & set(relevant)), len(set(citations)))


def leakage_rate(retrieved: Sequence[str], case_project: str | None, chunk_project: dict[str, str]) -> float | None:
    """检索结果里混入其它项目 chunk 的比例；无 project 信息时返回 None。"""
    if case_project is None or not retrieved:
        return None
    foreign = [c for c in retrieved if chunk_project.get(c, case_project) != case_project]
    return _div(len(foreign), len(retrieved))


def percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


def mean_or_zero(values: Sequence[float]) -> float:
    return float(mean(values)) if values else 0.0


# --------------------------------------------------------------------------- v2 聚合

def macro_average(groups: dict[str, list[float]]) -> float:
    """宏平均：先按组（题型）求均值，再对各组均值取平均。"""
    group_means = [mean(v) for v in groups.values() if v]
    return float(mean(group_means)) if group_means else 0.0


def micro_average(values: Sequence[float]) -> float:
    """微平均：按题量平均。"""
    return mean_or_zero(values)


def paired_bootstrap_ci(
    deltas: Sequence[float],
    n: int = 1000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, bool]:
    """对逐题差值做配对 bootstrap，返回 (lo, hi, 是否跨 0)。

    按 case 重采样 => 保留题与题的配对关系。CI 跨 0 视为"证据不足"。
    """
    import random

    vals = [float(d) for d in deltas]
    if not vals:
        return (0.0, 0.0, True)
    rng = random.Random(seed)
    size = len(vals)
    means: list[float] = []
    for _ in range(n):
        sample = [vals[rng.randrange(size)] for _ in range(size)]
        means.append(mean(sample))
    means.sort()
    lo = means[int((alpha / 2) * n)]
    hi = means[min(int((1 - alpha / 2) * n), n - 1)]
    return (round(lo, 4), round(hi, 4), lo <= 0.0 <= hi)

