"""切块：稳定 id、overlap、长度上界（阶段一核心不变量）。"""

from __future__ import annotations

import pytest

from rag_engine.ingest.chunker import chunk_document
from rag_engine.schema import Document


def _doc(text: str) -> Document:
    return Document(doc_id="d1", source="a.md", doc_type="md", text=text)


def test_chunk_ids_are_stable() -> None:
    doc = _doc("x" * 1000)
    first = [c.chunk_id for c in chunk_document(doc, size=100, overlap=20)]
    second = [c.chunk_id for c in chunk_document(doc, size=100, overlap=20)]
    assert first == second
    assert first[0] == "d1:0000"
    assert len(first) == len(set(first))  # 无重复 id


def test_windows_overlap() -> None:
    doc = _doc("".join(str(i % 10) for i in range(500)))
    chunks = chunk_document(doc, size=100, overlap=20)
    assert len(chunks) >= 2
    for prev, cur in zip(chunks, chunks[1:]):
        assert cur.meta["start"] < prev.meta["end"]  # 相邻窗口有重叠


def test_length_bound() -> None:
    doc = _doc("a" * 1000)
    for chunk in chunk_document(doc, size=100, overlap=0):
        assert len(chunk.text) <= 100


def test_metadata_carries_source_and_position() -> None:
    chunks = chunk_document(_doc("hello world " * 50), size=64, overlap=8)
    for chunk in chunks:
        assert chunk.meta["source"] == "a.md"
        assert chunk.meta["start"] < chunk.meta["end"]


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, 10), (10, 20)])
def test_rejects_bad_params(size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_document(_doc("x" * 100), size=size, overlap=overlap)
