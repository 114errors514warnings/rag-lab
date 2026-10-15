"""E05/E06 · L1：检索模式选择、拒答阈值、重排器（离线，不联网）。"""

from __future__ import annotations

import pytest

from rag_engine.config import EngineConfig
from rag_engine.embed.embedder import HashingTfidfEmbedder
from rag_engine.generate.generator import build_generator
from rag_engine.index.vector_store import NumpyVectorStore
from rag_engine.pipeline import RAGPipeline, _make_retriever
from rag_engine.retrieve.rerank import RerankedRetriever, SiliconFlowReranker
from rag_engine.schema import Chunk, Retrieved


def _store():
    chunks = [
        Chunk(chunk_id="d:0000", doc_id="d", text="alpha beta gamma", meta={"project_id": "p"}),
        Chunk(chunk_id="d:0001", doc_id="d", text="delta epsilon", meta={"project_id": "p"}),
    ]
    emb = HashingTfidfEmbedder(dim=64).fit([c.text for c in chunks])
    store = NumpyVectorStore()
    store.add(chunks, emb.embed([c.text for c in chunks]))
    return emb, store


def test_retrieval_mode_selects_retriever() -> None:
    emb, store = _store()
    assert type(_make_retriever(EngineConfig(retrieval="dense"), emb, store)).__name__ == "DenseRetriever"
    assert type(_make_retriever(EngineConfig(retrieval="bm25"), emb, store)).__name__ == "SparseRetriever"
    assert type(_make_retriever(EngineConfig(retrieval="hybrid"), emb, store)).__name__ == "HybridRetriever"


def test_rerank_wraps_base_retriever() -> None:
    emb, store = _store()
    r = _make_retriever(EngineConfig(retrieval="hybrid", rerank="idf"), emb, store)
    assert isinstance(r, RerankedRetriever)


def test_refusal_by_threshold_clears_citations() -> None:
    emb, store = _store()
    cfg = EngineConfig(retrieval="dense", min_relevance=0.99)  # 阈值高于任何余弦 → 必拒答
    retr = _make_retriever(cfg, emb, store)
    gen = build_generator("extractive", "", 5)
    pipe = RAGPipeline(cfg, emb, store, retr, gen)
    ans = pipe.answer("alpha beta", k=2)
    assert ans.refused is True
    assert ans.citations == []
    assert ans.retrieved  # 检索结果仍保留（供 trace）


def test_no_refusal_when_threshold_zero() -> None:
    emb, store = _store()
    cfg = EngineConfig(retrieval="dense", min_relevance=0.0)
    retr = _make_retriever(cfg, emb, store)
    gen = build_generator("extractive", "", 5)
    pipe = RAGPipeline(cfg, emb, store, retr, gen)
    ans = pipe.answer("alpha beta", k=2)
    assert ans.refused is False
    assert ans.citations


def test_reranked_retriever_delegates_to_reranker() -> None:
    emb, store = _store()
    base = _make_retriever(EngineConfig(retrieval="dense"), emb, store)

    class _FakeReranker:
        def rerank(self, question, hits, top_k=None):
            ordered = sorted(hits, key=lambda h: h.chunk.chunk_id, reverse=True)
            return ordered[:top_k] if top_k else ordered

    hits = RerankedRetriever(base, _FakeReranker(), candidates=10).retrieve("alpha", 1)
    assert len(hits) == 1


def test_siliconflow_reranker_requires_key(monkeypatch) -> None:
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    chunk = Chunk(chunk_id="c", doc_id="d", text="x", meta={})
    with pytest.raises(RuntimeError, match="SILICONFLOW_API_KEY"):
        SiliconFlowReranker().rerank("q", [Retrieved(chunk=chunk, score=1.0)])


def test_multiquery_retriever_fuses_deterministically() -> None:
    from rag_engine.retrieve.rewrite import MultiQueryRetriever

    emb, store = _store()
    base = _make_retriever(EngineConfig(retrieval="dense"), emb, store)
    r = MultiQueryRetriever(base, queries_fn=lambda q: [q, q + " gamma"], candidates=10)
    a = [h.chunk.chunk_id for h in r.retrieve("alpha", 2)]
    b = [h.chunk.chunk_id for h in r.retrieve("alpha", 2)]
    assert a == b  # RRF 融合确定
    assert len(a) <= 2


def test_rewrite_multi_wraps_retriever() -> None:
    from rag_engine.retrieve.rewrite import MultiQueryRetriever

    emb, store = _store()
    r = _make_retriever(EngineConfig(retrieval="dense", rewrite="multi"), emb, store)
    assert isinstance(r, MultiQueryRetriever)


def test_adjacent_context_expansion() -> None:
    from rag_engine.pipeline import _expand_context

    emb, store = _store()  # 两个块同 doc，order 0/1
    hits = store.search(emb.embed(["alpha beta gamma"])[0], 1)
    assert len(hits) == 1
    ctx = _expand_context(EngineConfig(context="adjacent", context_window=1), hits, store)
    ids = {h.chunk.chunk_id for h in ctx}
    assert {h.chunk.chunk_id for h in hits} <= ids  # 命中块保留
    assert len(ids) > len(hits)  # 邻近块被并入


def test_context_none_is_identity() -> None:
    from rag_engine.pipeline import _expand_context

    emb, store = _store()
    hits = store.search(emb.embed(["alpha beta gamma"])[0], 2)
    ctx = _expand_context(EngineConfig(context="none"), hits, store)
    assert [h.chunk.chunk_id for h in ctx] == [h.chunk.chunk_id for h in hits]
