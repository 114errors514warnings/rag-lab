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
