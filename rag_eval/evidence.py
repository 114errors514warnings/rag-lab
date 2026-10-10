"""证据映射与覆盖判定（v2 固定资产，改动需 bump EVAL_VERSION）。

口径（固定约定）：
- 一个检索单元（chunk）先映射到 (source, start_line, end_line, symbol)，再与 gold 证据比较。
- **匹配**：文件相同，且（行区间相交 或 symbol 相同）。
- **一个充分集被覆盖**：该集合内每条证据都能被前 K 个单元中的某一条匹配。
- ``evidence_coverage@K``：至少一个充分集被覆盖 => 1.0，否则 0.0（题目级二值，再取均值）。
- ``precision@K``：前 K 个单元里匹配到任意证据的比例。

这避免"直接把 chunk_id 当唯一标准"，支持多组等价证据。
"""

from __future__ import annotations

from typing import Sequence


def _norm(path: str | None) -> str:
    return (path or "").replace("\\", "/").strip().lstrip("./").lower()


def _lines_overlap(a_start, a_end, b_start, b_end) -> bool:
    if a_start is None or a_end is None or b_start is None or b_end is None:
        return False
    return a_start <= b_end and b_start <= a_end


def unit_matches_evidence(unit: dict, evidence: dict) -> bool:
    """unit: {source,start_line,end_line,symbol}; evidence: {file,start,end,symbol}."""
    if _norm(unit.get("source")) != _norm(evidence.get("file")):
        return False
    if _lines_overlap(unit.get("start_line"), unit.get("end_line"),
                      evidence.get("start"), evidence.get("end")):
        return True
    sym_u, sym_e = (unit.get("symbol") or "").strip(), (evidence.get("symbol") or "").strip()
    return bool(sym_u) and sym_u == sym_e


def normalize_gold_sets(gold_evidence: Sequence) -> list[list[dict]]:
    """把 gold_evidence 规范成『充分集的列表』。

    - ``[{file,...}, {file,...}]``   -> 视为一个充分集（需全部覆盖）
    - ``[[{...}], [{...}]]``         -> 两个等价充分集（覆盖任一即可）
    """
    if not gold_evidence:
        return []
    if all(isinstance(item, dict) for item in gold_evidence):
        return [list(gold_evidence)]
    sets: list[list[dict]] = []
    for item in gold_evidence:
        if isinstance(item, dict):
            sets.append([item])
        else:
            sets.append(list(item))
    return sets


def _covered_by(unit_dicts: Sequence[dict], evidence_set: Sequence[dict]) -> bool:
    return all(
        any(unit_matches_evidence(u, e) for u in unit_dicts)
        for e in evidence_set
    )


def evidence_coverage_at_k(units: Sequence[dict], gold_sets: list[list[dict]], k: int) -> float:
    """前 K 个单元是否覆盖了至少一个充分集（二值）。"""
    top = list(units[:k])
    if not gold_sets:
        return 0.0
    return 1.0 if any(_covered_by(top, s) for s in gold_sets) else 0.0


def first_hit_rank(units: Sequence[dict], gold_sets: list[list[dict]]) -> int | None:
    """首个匹配到任意证据的单元排名（1-based）；无命中返回 None。"""
    all_evidence = [e for s in gold_sets for e in s]
    for rank, unit in enumerate(units, start=1):
        if any(unit_matches_evidence(unit, e) for e in all_evidence):
            return rank
    return None


def mean_reciprocal_rank(units: Sequence[dict], gold_sets: list[list[dict]]) -> float:
    rank = first_hit_rank(units, gold_sets)
    return 1.0 / rank if rank else 0.0


def precision_vs_evidence(units: Sequence[dict], gold_sets: list[list[dict]], k: int) -> float:
    top = list(units[:k])
    if not top:
        return 0.0
    all_evidence = [e for s in gold_sets for e in s]
    hit = sum(1 for u in top if any(unit_matches_evidence(u, e) for e in all_evidence))
    return hit / len(top)


def ndcg_at_k(units: Sequence[dict], gold_sets: list[list[dict]], k: int) -> float:
    """0/1/2 相关性等级的 nDCG@K。

    每条证据只计一次（避免多个 chunk 命中同一证据导致 DCG>IDCG）：
    匹配到**新证据**记 2，仅同文件命中记 1，其余 0。
    """
    import math

    top = list(units[:k])
    all_evidence = [e for s in gold_sets for e in s]

    def matched_id(unit: dict) -> int | None:
        for idx, e in enumerate(all_evidence):
            if unit_matches_evidence(unit, e):
                return idx
        return None

    credited: set[int] = set()
    gains: list[int] = []
    for unit in top:
        eid = matched_id(unit)
        if eid is not None and eid not in credited:
            credited.add(eid)
            gains.append(2)
        elif eid is not None:
            gains.append(1)  # 重复命中同一证据
        elif any(_norm(unit.get("source")) == _norm(e.get("file")) for e in all_evidence):
            gains.append(1)
        else:
            gains.append(0)

    dcg = sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted([2] * min(len(all_evidence), k) + [0] * max(0, k - len(all_evidence)), reverse=True)
    idcg = sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(ideal[:k]))
    return min(dcg / idcg, 1.0) if idcg else 0.0
