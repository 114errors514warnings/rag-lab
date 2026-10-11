"""代码扫描与符号结构化索引（阶段五）。"""

from .ast_indexer import extract_symbols, index_code, scan_python_files
from .deps import build_dependency_graph, callees_of, callers_of

__all__ = ["scan_python_files", "extract_symbols", "index_code",
           "build_dependency_graph", "callers_of", "callees_of"]
