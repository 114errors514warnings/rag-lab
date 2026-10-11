"""S2 L1：Metadata Filtering——过滤后命中结果 100% 满足条件。"""

from __future__ import annotations

import numpy as np

from rag_engine.index.vector_store import NumpyVectorStore
from rag_engine.retrieve.filters import filter_chunks, matches, oversample_k
from rag_engine.schema import Chunk

DIM = 8


def _chunk(cid: str, project: str | None, source: str = "a.md") -> Chunk:
    return Chunk(chunk_id=cid, doc_id=cid.split(":")[0], text=f"text {cid}",
                 meta={"project_id": project, "source": source})


def _vec(*values: float) -> np.ndarray:
    v = np.array(values, dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def test_search_filter_returns_only_matching() -> None:
    store = NumpyVectorStore()
    chunks = [_chunk("a:0000", "proj-a"), _chunk("b:0000", "proj-b"), _chunk("a:0001", "proj-a")]
    store.add(chunks, np.vstack([_vec(1, 0, 0, 0, 0, 0, 0, 0)] * 3))

    hits = store.search(_vec(1, 0, 0, 0, 0, 0, 0, 0), k=10, flt={"project_id": "proj-a"})
    assert hits, "应命中 proj-a"
    assert all(h.chunk.meta["project_id"] == "proj-a" for h in hits)


def test_matches_semantics() -> None:
    meta = {"project_id": "a", "doc_type": "md"}
    assert matches(meta, None) is True
    assert matches(meta, {"project_id": "a"}) is True
    assert matches(meta, {"project_id": "b"}) is False
    assert matches(meta, {"project_id": "a", "doc_type": "py"}) is False
    assert matches(meta, {"project_id": "a", "doc_type": None}) is True  # None 表示不过滤


def test_filter_chunks_and_oversample() -> None:
    chunks = [_chunk("a:0000", "a"), _chunk("b:0000", "b")]
    kept = filter_chunks(chunks, {"project_id": "a"})
    assert [c.chunk_id for c in kept] == ["a:0000"]
    assert oversample_k(5, None) == 5
    assert oversample_k(5, {"project_id": "a"}, factor=3) == 15
