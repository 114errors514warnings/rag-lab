"""E03 · 符号级切块：以函数/类/方法为单位切块（仅代码文件），非代码退回定长。

块头写 ``symbol / kind / file / span``，并保留 ``start_line/end_line`` 供证据映射。
"""

from __future__ import annotations

import ast

from ..schema import Chunk, Document
from .chunker import chunk_document


def chunk_document_symbols(doc: Document) -> list[Chunk]:
    """解析单个 ``.py`` 文档为符号块；非代码或语法错误返回空（由上层回退定长）。"""
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

    chunks: list[Chunk] = []
    seq = 0

    def add(symbol: str, kind: str, node: ast.AST) -> None:
        nonlocal seq
        start_line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", start_line)
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
        seq += 1

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add(node.name, "function", node)
        elif isinstance(node, ast.ClassDef):
            add(node.name, "class", node)
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add(f"{node.name}.{sub.name}", "method", sub)
    return chunks


def chunk_documents_symbol(docs: list[Document], size: int = 400, overlap: int = 80) -> list[Chunk]:
    out: list[Chunk] = []
    for doc in docs:
        symbol_chunks = chunk_document_symbols(doc)
        out.extend(symbol_chunks if symbol_chunks else chunk_document(doc, size=size, overlap=overlap))
    return out
