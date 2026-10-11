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
