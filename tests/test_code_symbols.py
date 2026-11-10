"""S5 L1：AST 符号提取与依赖关系。"""

from __future__ import annotations

from pathlib import Path

from rag_engine.code_rag import build_dependency_graph, index_code

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "code_corpus"


def _symbols() -> dict:
    chunks = index_code(CORPUS)
    return {c.meta["symbol"]: c for c in chunks}


def test_extracts_functions_classes_methods() -> None:
    symbols = _symbols()
    assert "validate_page" in symbols
    assert "paginate" in symbols
    assert "PageQuery" in symbols
    assert "PageQuery.validate" in symbols
    assert "handle_request" in symbols
    assert "Router.dispatch" in symbols
    assert symbols["validate_page"].meta["kind"] == "function"
    assert symbols["PageQuery"].meta["kind"] == "class"
    assert symbols["Router.dispatch"].meta["kind"] == "method"


def test_chunk_ids_are_project_scoped_and_stable() -> None:
    first = {c.chunk_id: c.meta for c in index_code(CORPUS)}
    second = {c.chunk_id: c.meta for c in index_code(CORPUS)}
    assert first == second                                     # 确定性
    assert "proj-alpha:utils.py:validate_page" in first
    assert first["proj-alpha:utils.py:validate_page"]["project_id"] == "proj-alpha"
    assert first["proj-beta:handlers.py:Router.dispatch"]["project_id"] == "proj-beta"


def test_dependency_graph_callers_and_callees() -> None:
    graph = build_dependency_graph(index_code(CORPUS))
    assert "parse_query" in graph["handle_request"]["callees"]
    assert "handle_request" in graph["parse_query"]["callers"]
    assert "validate_page" in graph["PageQuery.validate"]["callees"]


def test_bom_and_broken_files_do_not_break_index(tmp_path) -> None:
    """含 BOM 或语法错误的文件应被跳过，而不是让整个索引失败。"""
    (tmp_path / "good.py").write_text("def good_fn():\n    return 1\n", encoding="utf-8")
    (tmp_path / "bom.py").write_text("def bom_fn():\n    return 2\n", encoding="utf-8-sig")
    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    symbols = {chunk.meta["symbol"] for chunk in index_code(tmp_path)}
    assert "good_fn" in symbols
    assert "bom_fn" in symbols          # BOM 不再导致解析失败
