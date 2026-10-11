"""S5 L1：多项目隔离——检索结果全部属于目标项目。"""

from __future__ import annotations

from pathlib import Path

from rag_engine.code_rag import index_code
from rag_engine.embed.embedder import build_embedder
from rag_engine.index.vector_store import NumpyVectorStore
from rag_engine.retrieve.dense import DenseRetriever

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "code_corpus"


def _retriever() -> DenseRetriever:
    chunks = index_code(CORPUS)
    embedder = build_embedder("hashing", 512, "", [c.text for c in chunks])
    store = NumpyVectorStore()
    store.add(chunks, embedder.embed([c.text for c in chunks]))
    return DenseRetriever(embedder, store, min_relevance=0.0)


def test_retrieval_is_isolated_by_project() -> None:
    retriever = _retriever()
    for project in ("proj-alpha", "proj-beta"):
        hits = retriever.retrieve("分页 校验 路由 解析", k=10, flt={"project_id": project})
        assert hits, f"{project} 应有命中"
        assert all(h.chunk.meta["project_id"] == project for h in hits)


def test_corpus_has_at_least_two_projects_for_leakage_test() -> None:
    projects = {c.meta["project_id"] for c in index_code(CORPUS)}
    assert {"proj-alpha", "proj-beta"} <= projects
