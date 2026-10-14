"""E03 · 符号级切块：以函数/类/方法为单位切块（仅代码文件），非代码退回定长。

块头写 ``symbol / kind / file / span``，并保留 ``start_line/end_line`` 供证据映射。

E03 修复（2026-10-14）：符号块只覆盖函数/类/方法体，会**丢失模块级区域**
（imports / module docstring / 常量 / 顶层语句），导致落在这些行的 ``gold_evidence`` 检索不到。
现补 **"模块剩余块"**（``kind="module"``）：把"不属于任何符号、且连续"的行区段各发一块。
所有块（符号块 + 模块块）按起始行排序后统一编号，``chunk_id`` 仍为 ``{doc_id}:{seq:04d}`` 连续稳定。
"""

from __future__ import annotations

import ast

from ..schema import Chunk, Document
from .chunker import chunk_document


def _node_span(node: ast.AST) -> tuple[int, int]:
    """返回 (start_line, end_line)，**含装饰器行**（装饰器在 def/class 的 lineno 之前）。"""
    start = getattr(node, "lineno", 1)
    for dec in getattr(node, "decorator_list", []) or []:
        start = min(start, getattr(dec, "lineno", start))
    end = getattr(node, "end_lineno", getattr(node, "lineno", start))
    return start, end


def _module_spans(lines: list[str], spans: list[tuple[int, int, str | None, str]]) -> list[tuple[int, int]]:
    """未被任何符号覆盖、且连续的行区段（去掉首尾空白行后仍非空）。"""
    n = len(lines)
    covered = [False] * (n + 2)
    for start, end, _, _ in spans:
        for line_no in range(max(1, start), min(n, end) + 1):
            covered[line_no] = True

    out: list[tuple[int, int]] = []
    line_no = 1
    while line_no <= n:
        if covered[line_no]:
            line_no += 1
            continue
        begin = line_no
        while line_no <= n and not covered[line_no]:
            line_no += 1
        end = line_no - 1
        while begin <= end and not lines[begin - 1].strip():
            begin += 1
        while end >= begin and not lines[end - 1].strip():
            end -= 1
        if begin <= end:
            out.append((begin, end))
    return out


def chunk_document_symbols(doc: Document) -> list[Chunk]:
    """解析单个 ``.py`` 文档为符号块 + 模块剩余块；非代码或语法错误返回空（由上层回退定长）。"""
    if doc.doc_type != "py":
        return []
    try:
        tree = ast.parse(doc.text)
    except SyntaxError:
        return []

    lines = doc.text.split("\n")
    offsets = [0]
    pos = 0
    for line in lines:
        pos += len(line) + 1
        offsets.append(pos)

    # 1) 收集符号跨度：(start_line, end_line, symbol, kind)
    spans: list[tuple[int, int, str | None, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start, end = _node_span(node)
            spans.append((start, end, node.name, "function"))
        elif isinstance(node, ast.ClassDef):
            start, end = _node_span(node)
            spans.append((start, end, node.name, "class"))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sub_start, sub_end = _node_span(sub)
                    spans.append((sub_start, sub_end, f"{node.name}.{sub.name}", "method"))

    # 2) 模块剩余块（补覆盖缺口）
    for begin, end in _module_spans(lines, spans):
        spans.append((begin, end, None, "module"))

    # 3) 按起始行排序后统一编号，保证 chunk_id 连续稳定
    spans.sort(key=lambda item: (item[0], item[1]))

    chunks: list[Chunk] = []
    for seq, (start_line, end_line, symbol, kind) in enumerate(spans):
        start = offsets[start_line - 1]
        end = offsets[end_line - 1] + len(lines[end_line - 1])
        text = "\n".join(lines[start_line - 1:end_line])
        chunks.append(Chunk(
            chunk_id=f"{doc.doc_id}:{seq:04d}", doc_id=doc.doc_id, text=text,
            meta={
                "source": doc.source, "doc_type": doc.doc_type,
                "symbol": symbol, "kind": kind, "file": doc.source,
                "start": start, "end": end,
                "start_line": start_line, "end_line": end_line, "order": seq,
                "updated_at": doc.updated_at, "project_id": doc.project_id,
            },
        ))
    return chunks


def chunk_documents_symbol(docs: list[Document], size: int = 400, overlap: int = 80) -> list[Chunk]:
    out: list[Chunk] = []
    for doc in docs:
        symbol_chunks = chunk_document_symbols(doc)
        out.extend(symbol_chunks if symbol_chunks else chunk_document(doc, size=size, overlap=overlap))
    return out
