"""符号扫描与结构化切块（阶段五 Code RAG）。

以函数/类/方法为单位切块，块头写 ``symbol / kind / file / span / deps``；
``project_id`` 取代码语料根下的一级子目录名，用于多项目隔离。
"""

from __future__ import annotations

import ast
from pathlib import Path

from ..schema import Chunk


def scan_python_files(root: Path | str) -> list[Path]:
    root = Path(root)
    return sorted((p for p in root.rglob("*.py") if p.is_file()), key=lambda p: p.as_posix())


def _collect_deps(node: ast.AST) -> list[str]:
    deps: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Name):
                deps.add(func.id)
            elif isinstance(func, ast.Attribute):
                deps.add(func.attr)
        elif isinstance(sub, (ast.Import, ast.ImportFrom)):
            for alias in sub.names:
                deps.add(alias.asname or alias.name.split(".")[0])
    return sorted(deps)


def _segment(node: ast.AST, source: str) -> str:
    lines = source.splitlines()
    start = max(getattr(node, "lineno", 1) - 1, 0)
    end = getattr(node, "end_lineno", getattr(node, "lineno", 1))
    return "\n".join(lines[start:end])


def extract_symbols(path: Path | str, root: Path | str) -> list[Chunk]:
    """解析一个 .py 文件，返回函数/类/方法的结构化切片。"""
    path, root = Path(path), Path(root)
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    project_id = rel.split("/", 1)[0] if "/" in rel else "root"
    rel_in_project = rel.split("/", 1)[1] if "/" in rel else rel
    source = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source)

    chunks: list[Chunk] = []

    def add(name: str, kind: str, node: ast.AST) -> None:
        text = _segment(node, source)
        chunk_id = f"{project_id}:{rel_in_project}:{name}"
        chunks.append(Chunk(
            chunk_id=chunk_id, doc_id=f"{project_id}:{rel_in_project}", text=text,
            meta={
                "symbol": name, "kind": kind, "file": rel_in_project, "project_id": project_id,
                "source": rel,
                "start_line": getattr(node, "lineno", 1),
                "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                "deps": _collect_deps(node),
            },
        ))

    # 仅按 AST 顶层结构切分：顶层函数 → function；类 → class；类体函数 → method。
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add(node.name, "function", node)
        elif isinstance(node, ast.ClassDef):
            add(node.name, "class", node)
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add(f"{node.name}.{sub.name}", "method", sub)
    return chunks


def index_code(root: Path | str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in scan_python_files(root):
        chunks.extend(extract_symbols(path, root))
    return chunks
