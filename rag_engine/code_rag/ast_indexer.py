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


#: 支持符号索引的语言（与 `index_code` 的分派保持一致）
_CODE_SUFFIXES = (".py", ".cs")


def scan_code_files(root: Path | str, extensions=None, exclude_dirs=None) -> list[Path]:
    """列出要建符号索引的源码文件；``extensions`` 缺省 = 只有 ``.py``（保持原行为）。

    ``exclude_dirs`` 与检索侧同口径（目录名或相对路径），否则 ``Release/`` 里的
    构建副本会和正本撞符号名。
    """
    from ..ingest.loader import _SKIP_DIR_NAMES, _is_excluded

    root = Path(root)
    allowed = tuple(extensions or (".py",))
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        relative = path.relative_to(root)
        if any(part.startswith(".") or part in _SKIP_DIR_NAMES for part in relative.parts[:-1]):
            continue
        if _is_excluded(relative, exclude_dirs):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.as_posix())


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


def extract_symbols(path: Path | str, root: Path | str,
                    project_id: str | None = None) -> list[Chunk]:
    """解析一个 .py 文件，返回函数/类/方法的结构化切片。"""
    path, root = Path(path), Path(root)
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    default_project = rel.split("/", 1)[0] if "/" in rel else "root"
    project = project_id or default_project
    rel_in_project = rel.split("/", 1)[1] if (project_id is None and "/" in rel) else rel
    source = path.read_text(encoding="utf-8-sig", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # 单个文件语法错误（含非法编码/半截文件）不应让整库索引失败
        return []

    chunks: list[Chunk] = []

    def add(name: str, kind: str, node: ast.AST) -> None:
        text = _segment(node, source)
        chunk_id = f"{project}:{rel_in_project}:{name}"
        chunks.append(Chunk(
            chunk_id=chunk_id, doc_id=f"{project}:{rel_in_project}", text=text,
            meta={
                "symbol": name, "kind": kind, "file": rel_in_project, "project_id": project,
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


def index_code(root: Path | str, extensions=None,
               project_id: str | None = None, exclude_dirs=None) -> list[Chunk]:
    """按后缀分派建符号索引；``extensions`` 缺省 = 只有 ``.py``（保持原行为）。"""
    from .csharp_indexer import extract_csharp_symbols

    chunks: list[Chunk] = []
    for path in scan_code_files(root, extensions, exclude_dirs):
        if path.suffix.lower() == ".cs":
            chunks.extend(extract_csharp_symbols(path, root, project_id=project_id))
        else:
            chunks.extend(extract_symbols(path, root, project_id=project_id))
    return chunks
