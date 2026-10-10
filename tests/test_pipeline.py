"""端到端：真实语料上建索引、检索、带引用回答。"""

from __future__ import annotations

import pytest

from rag_engine.config import EngineConfig
from rag_engine.pipeline import load_or_build


@pytest.fixture(scope="module")
def pipeline():
    return load_or_build(EngineConfig())


def test_index_is_nonempty(pipeline) -> None:
    assert len(pipeline.store) > 0


def test_answer_has_citations_from_retrieved(pipeline) -> None:
    answer = pipeline.answer("RAG 的基本流程包含哪些步骤？", k=3)
    assert answer.retrieved, "应至少检索到一条片段"
    assert answer.citations, "带引用生成必须给出 citations"
    assert set(answer.citations) <= {h.chunk.chunk_id for h in answer.retrieved}


def test_deterministic(pipeline) -> None:
    a = pipeline.answer("什么是稀疏检索？", k=3)
    b = pipeline.answer("什么是稀疏检索？", k=3)
    assert [h.chunk.chunk_id for h in a.retrieved] == [h.chunk.chunk_id for h in b.retrieved]
    assert a.citations == b.citations


def test_self_reported_latency(pipeline) -> None:
    answer = pipeline.answer("增量索引有什么好处？", k=3)
    assert answer.latency_ms >= 0.0
