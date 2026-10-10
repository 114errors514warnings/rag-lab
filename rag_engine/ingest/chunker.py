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
