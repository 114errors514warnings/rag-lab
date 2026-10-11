"""清洗与去重（阶段二）。

- 统一换行、去 BOM、去行尾空白、压缩连续空行；**保留缩进**（代码文件不破坏）。
- 内容哈希 ``content_hash`` 用于去重：同来源只留最新，不同来源内容相同只留一份。
"""

from __future__ import annotations

import hashlib
from dataclasses import replace

from ..schema import Document


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []
    blank = 0
    for line in text.split("\n"):
        line = line.rstrip()
        if not line.strip():
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(line)
    return "\n".join(out).strip()


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
