"""固定长度切块 + Overlap（阶段一）。

- 字符级滑动窗口，中英通用、结果确定。
- 在窗口末端附近**优先回退到换行/句读边界**，减少硬切断；找不到边界则按定长切。
- ``chunk_id = f"{doc_id}:{seq:04d}"``：同文档同参数稳定不变。
"""

from __future__ import annotations

from ..schema import Chunk, Document

#: 结尾附近优先断句的搜索窗口（字符）
_BOUNDARY = "\n。！？.!?；;"


def _pick_end(text: str, start: int, size: int) -> int:
    """在 [start+size*0.6, start+size] 内寻找最后一个换行/句读作为切点。"""
    hard_end = min(start + size, len(text))
    if hard_end >= len(text):
        return len(text)
    floor = start + int(size * 0.6)
    best = -1
    for idx in range(hard_end - 1, floor - 1, -1):
        if text[idx] in _BOUNDARY:
            best = idx + 1
            break
    return best if best > start else hard_end


def chunk_document(doc: Document, size: int = 400, overlap: int = 80) -> list[Chunk]:
    if size <= 0:
        raise ValueError("chunk size 必须为正")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap 必须满足 0 <= overlap < size")

    text = doc.text or ""
    step = size - overlap
    chunks: list[Chunk] = []
    start = 0
    seq = 0
    while start < len(text):
        end = _pick_end(text, start, size)
        piece = text[start:end]
        if piece.strip():
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}:{seq:04d}",
                    doc_id=doc.doc_id,
                    text=piece.strip(),
                    meta={
                        "source": doc.source,
                        "doc_type": doc.doc_type,
                        # 字符偏移（切块内部使用）
                        "start": start,
                        "end": end,
                        # 行区间（证据映射使用；1-based，闭区间）
                        "start_line": text.count("\n", 0, start) + 1,
                        "end_line": text.count("\n", 0, end) + 1,
                        "order": seq,
                        "updated_at": doc.updated_at,
                        "project_id": doc.project_id,
                    },
                )
            )
            seq += 1
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_documents(docs: list[Document], size: int = 400, overlap: int = 80) -> list[Chunk]:
    out: list[Chunk] = []
    for doc in docs:
        out.extend(chunk_document(doc, size=size, overlap=overlap))
    return out


def chunk_hierarchical(doc: Document, parent_size: int = 1600, child_size: int = 400,
                        overlap: int = 80) -> tuple[list[Chunk], list[Chunk]]:
    """层级切块（阶段二 Parent-Child）：返回 (父块, 子块)。

    - 父块：较大窗口，作为生成上下文。
    - 子块：在父块内部再切，``meta['parent_id']`` 指回父块 ``chunk_id``。
    - id 稳定且不与定长切块冲突：``{doc_id}:P{seq:04d}`` / ``{doc_id}:P{seq:04d}:C{seq:03d}``。
    """
    from .metadata import build_chunk_meta

    text = doc.text or ""
    parents: list[Chunk] = []
    children: list[Chunk] = []
    pseq = 0
    start = 0
    while start < len(text):
        end = _pick_end(text, start, parent_size)
        piece = text[start:end]
        if piece.strip():
            parent_id = f"{doc.doc_id}:P{pseq:04d}"
            parents.append(Chunk(
                chunk_id=parent_id, doc_id=doc.doc_id, text=piece.strip(),
                meta=build_chunk_meta(doc, text, start, end, pseq, kind="parent"),
            ))
            cseq = 0
            cstart = start
            while cstart < end:
                cend = _pick_end(text, cstart, child_size)
                cend = min(cend, end)
                cpiece = text[cstart:cend]
                if cpiece.strip():
                    children.append(Chunk(
                        chunk_id=f"{parent_id}:C{cseq:03d}", doc_id=doc.doc_id, text=cpiece.strip(),
                        meta=build_chunk_meta(doc, text, cstart, cend, cseq,
                                              kind="child", parent_id=parent_id),
                    ))
                    cseq += 1
                if cend >= end:
                    break
                cstart = max(cend - overlap, cstart + 1)
            pseq += 1
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return parents, children


def chunk_hierarchical_documents(docs: list[Document], parent_size: int = 1600,
                                 child_size: int = 400, overlap: int = 80,
                                 ) -> tuple[list[Chunk], list[Chunk]]:
    parents: list[Chunk] = []
    children: list[Chunk] = []
    for doc in docs:
        p, c = chunk_hierarchical(doc, parent_size=parent_size, child_size=child_size, overlap=overlap)
        parents.extend(p)
        children.extend(c)
    return parents, children
