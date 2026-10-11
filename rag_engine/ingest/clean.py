"""清洗与去重（阶段二）。

- 统一换行、去 BOM、去行尾空白、压缩连续空行；**保留缩进**（代码文件不破坏）。
- 内容哈希 ``content_hash`` 用于去重：同来源只留最新，不同来源内容相同只留一份。
"""

from __future__ import annotations

import hashlib
from dataclasses import replace

from ..schema import Document


def normalize_text(text: str) -> str:
    """格式统一（阶段二）：去 BOM、统一换行。

    **刻意保持行数不变**：不做空行压缩、不 strip、不逐行 rstrip——否则行号整体位移，
    会使证据制评测（`gold_evidence` 的 file/line 区间）错位，导致 recall 假性下降。

    见 `docs/reports/R1/stage-S2-report.md` 的「后续变更」：本函数在 2026-10-11 由
    "压缩空行 + 逐行 rstrip" 改为"仅 BOM/换行归一"，以修复 E00 基线不复现问题。
    """
    if not text:
        return text
    text = text.replace("\ufeff", "")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def clean_document(doc: Document) -> Document:
    return replace(doc, text=normalize_text(doc.text))


def clean_documents(docs: list[Document]) -> list[Document]:
    return [clean_document(d) for d in docs]


def dedupe_documents(docs: list[Document]) -> tuple[list[Document], list[str]]:
    """返回 (保留的文档, 被丢弃的来源列表)。

    规则：先把同一 ``source`` 收敛为 ``updated_at`` 最新的一份；再按 ``content_hash``
    全局去重，保留来源名排序后最先出现的一份（保证确定性）。
    """
    latest: dict[str, Document] = {}
    for doc in docs:
        prev = latest.get(doc.source)
        if prev is None or (doc.updated_at or "") >= (prev.updated_at or ""):
            latest[doc.source] = doc

    kept: list[Document] = []
    dropped: list[str] = []
    seen: dict[str, str] = {}
    for source in sorted(latest):
        doc = latest[source]
        digest = content_hash(doc.text)
        if digest in seen:
            dropped.append(source)
            continue
        seen[digest] = source
        kept.append(doc)
    return kept, dropped
