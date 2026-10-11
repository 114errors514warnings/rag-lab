"""S2 L1：增量索引——只重建受影响切片，其余 chunk 与向量逐字节不变。"""

from __future__ import annotations

import hashlib

import numpy as np

from rag_engine.index.indexer import IncrementalIndexer
from rag_engine.index.vector_store import NumpyVectorStore
from rag_engine.schema import Document

DIM = 16


class CountingEmbedder:
    """确定性向量 + 记录被嵌入的文本数（用来断言"只重建受影响切片"）。"""

    def __init__(self) -> None:
        self.embedded_texts: list[str] = []

    def embed(self, texts: list[str]) -> np.ndarray:
        self.embedded_texts.extend(texts)
        rows = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
            vec = rng.random(DIM).astype(np.float32)
            rows.append(vec / (np.linalg.norm(vec) + 1e-9))
        return np.vstack(rows) if rows else np.zeros((0, DIM), dtype=np.float32)


def _doc(doc_id: str, text: str) -> Document:
    return Document(doc_id=doc_id, source=f"{doc_id}.md", doc_type="md", text=text)


def _long(tag: str, n: int = 1200) -> str:
    return (f"{tag} " * (n // (len(tag) + 1)))


def _vector_for(store: NumpyVectorStore, chunk_id: str) -> np.ndarray:
    idx = [c.chunk_id for c in store.chunks].index(chunk_id)
    return store._matrix[idx].copy()


def test_incremental_rebuild_only_affected() -> None:
    store = NumpyVectorStore()
    embedder = CountingEmbedder()
    indexer = IncrementalIndexer(store, embedder)

    docs = [_doc("d1", _long("alpha")), _doc("d2", _long("bravo")), _doc("d3", _long("charlie"))]
    first = indexer.update(docs)
    assert sorted(first.added) == ["d1", "d2", "d3"]
    assert first.chunks_rebuilt == len(store.chunks) > 3
    embedded_after_first = len(embedder.embedded_texts)

    # 记录 d1/d3 的 chunk 与向量
    before = {c.chunk_id: _vector_for(store, c.chunk_id)
              for c in store.chunks if c.doc_id in ("d1", "d3")}
    assert before

    # 改动 d2
    docs2 = [_doc("d1", _long("alpha")), _doc("d2", _long("bravo") + " 改动"), _doc("d3", _long("charlie"))]
    second = indexer.update(docs2)
    assert second.changed == ["d2"]
    assert second.added == [] and second.removed == []
    assert sorted(second.reused) == ["d1", "d3"]

    # d1/d3 的 chunk_id 与向量逐字节不变
    after = {c.chunk_id: _vector_for(store, c.chunk_id)
             for c in store.chunks if c.doc_id in ("d1", "d3")}
    assert set(after) == set(before)
    for chunk_id, vec in before.items():
        assert np.array_equal(vec, after[chunk_id])

    # 只嵌入了 d2 的切片
    d2_chunks = [c for c in store.chunks if c.doc_id == "d2"]
    assert embedder.embedded_texts[embedded_after_first:] == [c.text for c in d2_chunks]
    assert not any(c.doc_id == "d2" and c.chunk_id in before for c in store.chunks)


def test_incremental_add_and_remove() -> None:
    store = NumpyVectorStore()
    indexer = IncrementalIndexer(store, CountingEmbedder())
    indexer.update([_doc("d1", _long("alpha")), _doc("d2", _long("bravo"))])

    upd = indexer.update([_doc("d1", _long("alpha")), _doc("d3", _long("delta"))])
    assert upd.removed == ["d2"] and upd.added == ["d3"] and upd.changed == []
    assert upd.reused == ["d1"]
    assert all(c.doc_id != "d2" for c in store.chunks)

    upd2 = indexer.update([_doc("d1", _long("alpha")), _doc("d3", _long("delta")), _doc("d4", _long("echo"))])
    assert upd2.added == ["d4"] and upd2.changed == [] and upd2.removed == []


def test_indexer_state_roundtrip(tmp_path) -> None:
    store = NumpyVectorStore()
    indexer = IncrementalIndexer(store, CountingEmbedder())
    indexer.update([_doc("d1", _long("alpha"))])
    indexer.save(tmp_path)

    fresh = IncrementalIndexer(NumpyVectorStore(), CountingEmbedder())
    fresh.load(tmp_path)
    # 载入状态后，同样的文档应被视为 reused（不重建）
    upd = fresh.update([_doc("d1", _long("alpha"))])
    assert upd.reused == ["d1"] and upd.changed == [] and upd.added == []
