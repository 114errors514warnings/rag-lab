"""E03 · L1：符号级切块（函数/类/方法），非代码/语法错误回退定长。"""

from __future__ import annotations

from rag_engine.ingest.symbol_chunker import chunk_document_symbols, chunk_documents_symbol
from rag_engine.schema import Document

PY = '''\
import os

MAX = 10


def validate_page(page):
    return 1 <= page <= MAX


class PageQuery:
    def __init__(self, page=1):
        self.page = page

    def validate(self):
        return validate_page(self.page)
'''


def _doc(text: str, doc_type: str = "py") -> Document:
    return Document(doc_id="d1", source=f"proj-a/a.{doc_type}", doc_type=doc_type,
                    text=text, project_id="proj-a")


def test_extracts_functions_classes_methods() -> None:
    chunks = chunk_document_symbols(_doc(PY))
    symbols = {c.meta["symbol"]: c.meta["kind"] for c in chunks}
    assert symbols["validate_page"] == "function"
    assert symbols["PageQuery"] == "class"
    assert symbols["PageQuery.__init__"] == "method"
    assert symbols["PageQuery.validate"] == "method"


def test_symbol_chunks_have_span_and_source() -> None:
    chunks = chunk_document_symbols(_doc(PY))
    vp = next(c for c in chunks if c.meta["symbol"] == "validate_page")
    assert vp.meta["start_line"] >= 1 and vp.meta["end_line"] >= vp.meta["start_line"]
    assert vp.meta["source"] == "proj-a/a.py" and vp.meta["project_id"] == "proj-a"
    assert "return 1 <= page <= MAX" in vp.text


def test_chunk_ids_are_sequential_and_stable() -> None:
    a = [c.chunk_id for c in chunk_document_symbols(_doc(PY))]
    b = [c.chunk_id for c in chunk_document_symbols(_doc(PY))]
    assert a == b == [f"d1:{i:04d}" for i in range(len(a))]


def test_non_code_falls_back_to_fixed() -> None:
    assert chunk_document_symbols(_doc("普通文本" * 100, doc_type="md")) == []
    fixed = chunk_documents_symbol([_doc("普通文本" * 200, doc_type="md")], size=400, overlap=80)
    assert fixed and all(c.doc_id == "d1" for c in fixed)


def test_syntax_error_falls_back() -> None:
    bad = _doc("def broken(:\n    pass")
    assert chunk_document_symbols(bad) == []
    assert chunk_documents_symbol([bad])  # 回退定长后仍有块
