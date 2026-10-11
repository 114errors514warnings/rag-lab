"""E02 · L1：切块参数（size / overlap）与 chunk_id 稳定性。"""

from __future__ import annotations

from rag_engine.ingest.chunker import chunk_document
from rag_engine.schema import Document


def _doc(text: str) -> Document:
    return Document(doc_id="d1", source="a.md", doc_type="md", text=text)


def test_size_controls_chunk_count() -> None:
    text = "句子。" * 600
    small = chunk_document(_doc(text), size=256, overlap=80)
    large = chunk_document(_doc(text), size=512, overlap=80)
    assert len(small) > len(large)


def test_overlap_does_not_reduce_chunks() -> None:
    text = "abcdefghij" * 300
    no_overlap = chunk_document(_doc(text), size=400, overlap=0)
    with_overlap = chunk_document(_doc(text), size=400, overlap=128)
    assert len(with_overlap) >= len(no_overlap)


def test_chunk_id_stable_for_same_params() -> None:
    text = "内容" * 800
    a = [c.chunk_id for c in chunk_document(_doc(text), size=400, overlap=80)]
    b = [c.chunk_id for c in chunk_document(_doc(text), size=400, overlap=80)]
    assert a == b and a[0] == "d1:0000"


def test_chunk_ids_sequence_is_contiguous() -> None:
    text = "x" * 2000
    ids = [c.chunk_id for c in chunk_document(_doc(text), size=256, overlap=80)]
    assert ids == [f"d1:{i:04d}" for i in range(len(ids))]
    assert len(ids) != len(chunk_document(_doc(text), size=512, overlap=80))  # 参数影响块数


def test_invalid_params_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        chunk_document(_doc("abc"), size=0)
    with pytest.raises(ValueError):
        chunk_document(_doc("abc"), size=100, overlap=100)
