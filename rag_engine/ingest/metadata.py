"""Chunk Metadata 构造（阶段二）。

元数据是「过滤前置」与「来源回溯」的基础，字段固定为：
``source / section / position / updated_at / project_id / trust``（外加定位用 start/end/行号）。
"""

from __future__ import annotations

import re
from typing import Any

from ..schema import Document

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def section_at(text: str, offset: int) -> str:
    """返回 ``offset`` 之前最近的 Markdown 标题文本（无则空串）。"""
    if not text:
        return ""
    section = ""
    for line in text[: max(0, offset)].split("\n"):
        match = _HEADING.match(line.strip())
        if match:
            section = match.group(2).strip()
    return section


def build_chunk_meta(doc: Document, text: str, start: int, end: int, order: int,
                     kind: str = "text", parent_id: str | None = None,
                     trust: float = 1.0) -> dict[str, Any]:
    return {
        "source": doc.source,
        "doc_type": doc.doc_type,
        "section": section_at(text, start),
        "position": order,
        "start": start,
        "end": end,
        "start_line": text.count("\n", 0, start) + 1,
        "end_line": text.count("\n", 0, end) + 1,
        "updated_at": doc.updated_at,
        "project_id": doc.project_id,
        "trust": trust,
        "kind": kind,
        "parent_id": parent_id,
    }
