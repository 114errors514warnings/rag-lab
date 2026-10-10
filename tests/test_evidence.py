"""证据映射与 v2 指标口径（阶段 M0 固定资产）。"""

from __future__ import annotations

from rag_eval.evidence import (
    evidence_coverage_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    normalize_gold_sets,
    precision_vs_evidence,
    unit_matches_evidence,
)
from rag_eval.metrics import macro_average, paired_bootstrap_ci


def _u(file, start=None, end=None, symbol=None):
    return {"source": file, "start_line": start, "end_line": end, "symbol": symbol}


def test_normalize_gold_sets_forms() -> None:
    # 一个充分集（需全部覆盖）
    one = normalize_gold_sets([{"file": "a.py", "start": 1, "end": 5}])
    assert len(one) == 1 and len(one[0]) == 1
    # 多个等价充分集
    many = normalize_gold_sets([[{"file": "a.py"}], [{"file": "b.py"}]])
    assert len(many) == 2
    assert normalize_gold_sets([]) == []


def test_match_by_line_overlap_and_symbol() -> None:
    assert unit_matches_evidence(_u("a.py", 10, 20), {"file": "a.py", "start": 15, "end": 25})
    assert not unit_matches_evidence(_u("a.py", 1, 5), {"file": "a.py", "start": 15, "end": 25})
    assert unit_matches_evidence(_u("a.py", symbol="foo"), {"file": "a.py", "symbol": "foo"})
    assert not unit_matches_evidence(_u("b.py", 10, 20), {"file": "a.py", "start": 15, "end": 25})


def test_coverage_multiple_sufficient_sets() -> None:
    gold = [[{"file": "a.py", "start": 1, "end": 2}], [{"file": "b.py", "start": 5, "end": 6}]]
    units = [_u("b.py", 5, 6)]  # 命中第二个充分集
    assert evidence_coverage_at_k(units, gold, 5) == 1.0
    assert precision_vs_evidence(units, gold, 5) == 1.0


def test_coverage_requires_all_in_a_set() -> None:
    gold = [[{"file": "a.py", "start": 1, "end": 2}, {"file": "b.py", "start": 5, "end": 6}]]
    only_a = [_u("a.py", 1, 2)]
    assert evidence_coverage_at_k(only_a, gold, 5) == 0.0
    both = only_a + [_u("b.py", 5, 6)]
    assert evidence_coverage_at_k(both, gold, 5) == 1.0


def test_mrr_uses_first_hit() -> None:
    gold = [[{"file": "a.py", "start": 1, "end": 2}]]
    assert mean_reciprocal_rank([_u("x.py"), _u("a.py", 1, 2)], gold) == 0.5
    assert mean_reciprocal_rank([_u("x.py")], gold) == 0.0


def test_ndcg_bounded() -> None:
    gold = [[{"file": "a.py", "start": 1, "end": 2}]]
    val = ndcg_at_k([_u("a.py", 1, 2), _u("a.py", 3, 4)], gold, 2)
    assert 0.0 <= val <= 1.0


def test_macro_and_bootstrap() -> None:
    assert macro_average({"a": [1.0, 1.0], "b": [0.0]}) == 0.5
    lo, hi, crosses = paired_bootstrap_ci([0.1] * 20)
    assert lo <= hi
    assert not crosses  # 全为正 => 不跨 0
    _, _, crosses2 = paired_bootstrap_ci([0.1] * 10 + [-0.1] * 10)
    assert crosses2
