"""向量索引：排序、metadata 过滤、持久化往返。"""

from __future__ import annotations

import numpy as np

from rag_engine.index.vector_store import NumpyVectorStore
from rag_engine.schema import Chunk


def _chunk(cid: str, meta: dict | None = None) -> Chunk:
    return Chunk(chunk_id=cid, doc_id="d", text=cid, meta=meta or {})


def test_search_ranks_by_inner_product() -> None:
    store = NumpyVectorStore()
    store.add(
        [_chunk("a"), _chunk("b")],
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
    )
    hits = store.search(np.array([1.0, 0.0], dtype=np.float32), k=2)
    assert [h.chunk.chunk_id for h in hits] == ["a", "b"]


def test_metadata_filter() -> None:
    store = NumpyVectorStore()
    store.add(
        [_chunk("a", {"project_id": "p1"}), _chunk("b", {"project_id": "p2"})],
        np.array([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32),
    )
    hits = store.search(np.array([1.0, 0.0], dtype=np.float32), k=2, flt={"project_id": "p2"})
    assert [h.chunk.chunk_id for h in hits] == ["b"]


def test_persist_roundtrip(tmp_path) -> None:
    store = NumpyVectorStore()
    store.add([_chunk("a", {"source": "x.md"})], np.array([[1.0, 0.0]], dtype=np.float32))
    store.save(tmp_path)

    loaded = NumpyVectorStore.load(tmp_path)
    assert len(loaded) == 1
    hits = loaded.search(np.array([1.0, 0.0], dtype=np.float32), k=1)
    assert hits[0].chunk.chunk_id == "a"
    assert hits[0].chunk.meta["source"] == "x.md"


def test_add_length_mismatch_raises() -> None:
    import pytest

    store = NumpyVectorStore()
    with pytest.raises(ValueError):
        store.add([_chunk("a")], np.zeros((2, 3), dtype=np.float32))
