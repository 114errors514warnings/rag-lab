"""评测协议自检：指标口径、门禁与套件一致性、被测系统契约。

这一层不依赖任何真实 RAG 实现，保证"固定测试方法"本身不会悄悄跑偏。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from rag_eval import EVAL_VERSION
from rag_eval.metrics import (
    citation_precision,
    hit_at_1,
    leakage_rate,
    mrr,
    percentile,
    precision_at_k,
    recall_at_k,
)
from rag_eval.sut import REGISTRY
from rag_eval.sut.base import Sut

ROOT = Path(__file__).resolve().parents[1]
_METRIC_NAME = re.compile(
    r"^(success_rate|error_rate|mrr|hit@1|citation_precision|citation_missing_rate"
    r"|leakage_rate|avg_latency_ms|p50_latency_ms|p95_latency_ms|avg_prompt_tokens"
    r"|cost_per_query_usd|total_cost_usd|recall@\d+(\[[a-z_]+\])?|precision@\d+)$"
)


# --------------------------------------------------------------------- 指标口径
def test_recall_and_precision() -> None:
    ranked = ["a", "b", "c", "d"]
    relevant = ["b", "d", "z"]
    assert recall_at_k(ranked, relevant, 3) == pytest.approx(1 / 3)
    assert recall_at_k(ranked, relevant, 4) == pytest.approx(2 / 3)
    assert precision_at_k(ranked, relevant, 2) == pytest.approx(0.5)


def test_mrr_and_hit() -> None:
    assert mrr(["x", "b", "c"], ["b"]) == pytest.approx(0.5)
    assert mrr(["x", "y"], ["z"]) == 0.0
    assert hit_at_1(["b", "x"], ["b"]) == 1.0
    assert hit_at_1(["x", "b"], ["b"]) == 0.0


def test_citation_precision_and_leakage() -> None:
    assert citation_precision([], ["a"]) is None
    assert citation_precision(["a", "z"], ["a"]) == pytest.approx(0.5)
    assert leakage_rate(["a", "b"], "p1", {"a": "p1", "b": "p2"}) == pytest.approx(0.5)
    assert leakage_rate(["a"], None, {"a": "p1"}) is None


def test_percentile() -> None:
    assert percentile([1, 2, 3, 4], 0.5) == pytest.approx(2.5)
    assert percentile([], 0.95) == 0.0


# --------------------------------------------------------------------- 门禁一致性
def _gates() -> dict:
    return json.loads((ROOT / "rag_eval" / "gates.json").read_text(encoding="utf-8"))


def test_eval_version_matches_gates() -> None:
    assert _gates()["eval_version"] == EVAL_VERSION


def test_every_gated_suite_exists() -> None:
    for stage, cfg in _gates()["stages"].items():
        for suite in cfg.get("suites", []):
            path = ROOT / "data" / "eval_suites" / f"{suite}.jsonl"
            assert path.exists(), f"阶段 {stage} 引用的套件缺失：{suite}"


def test_gate_metric_names_are_known() -> None:
    for stage, cfg in _gates()["stages"].items():
        rules = {**cfg.get("primary", {}), **cfg.get("guardrails", {})}
        for metric in rules:
            assert _METRIC_NAME.match(metric), f"阶段 {stage} 出现未知指标：{metric}"


# --------------------------------------------------------------------- 被测系统契约
@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_registered_sut_contract(name: str) -> None:
    instance = REGISTRY[name]()
    assert isinstance(instance, Sut)
    assert isinstance(instance.name, str) and instance.name
    assert isinstance(instance.config_hash, str) and instance.config_hash
