"""Context Engineering（阶段四）。

按序处理，保证"固定预算下可追溯"：
1. 去重（chunk_id + 文本近似）；
2. 相关性阈值过滤；
3. 分组（按 source）→ 每文档至少 1 块；
4. Token Budget 分配：剩余预算按分数排序填充，超预算截断（截断仍带来源与定位）；
5. 冲突/过期/低可信度标注（供生成器降权）。

输出 ``Context{segments:[{chunk_id, source, text, tokens, notes}], tokens, dropped}``。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..schema import Retrieved
from ..utils import estimate_tokens


@dataclass
class ContextSegment:
    chunk_id: str
    source: str | None
    text: str
    tokens: int
    score: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class Context:
    segments: list[ContextSegment] = field(default_factory=list)
    tokens: int = 0
    dropped: list[str] = field(default_factory=list)


def _source_of(hit: Retrieved) -> str:
    return str(hit.chunk.meta.get("source") or hit.chunk.doc_id)


def _dedupe(hits: list[Retrieved]) -> list[Retrieved]:
    seen_ids: set[str] = set()
    seen_text: list[str] = []
    out: list[Retrieved] = []
    for hit in hits:
        cid = hit.chunk.chunk_id
        if cid in seen_ids:
            continue
        fingerprint = " ".join(hit.chunk.text.split())[:120]
        if any(fingerprint == t for t in seen_text):
            continue
        seen_ids.add(cid)
        seen_text.append(fingerprint)
        out.append(hit)
    return out


def _fit(text: str, remaining: int) -> str:
    """把 text 截断到 estimated tokens ≤ remaining（保留前缀）。"""
    if estimate_tokens(text) <= remaining:
        return text
    lo, hi = 1, len(text)
    best = text[:1]
    while lo <= hi:
        mid = (lo + hi) // 2
        if estimate_tokens(text[:mid]) <= remaining:
            best = text[:mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


class ContextBuilder:
    def __init__(self, max_tokens: int = 1000, relevance_threshold: float = 0.0,
                 per_doc_min: int = 1) -> None:
        self.max_tokens = max_tokens
        self.relevance_threshold = relevance_threshold
        self.per_doc_min = max(0, per_doc_min)

    def build(self, hits: list[Retrieved]) -> Context:
        hits = _dedupe([h for h in hits if h.score >= self.relevance_threshold])
        if not hits:
            return Context()

        ordered = sorted(hits, key=lambda h: (-h.score, h.chunk.chunk_id))
        by_source: dict[str, list[Retrieved]] = {}
        for hit in ordered:
            by_source.setdefault(_source_of(hit), []).append(hit)

        chosen: list[Retrieved] = []
        used: set[str] = set()
        for items in by_source.values():
            for pick in items[: self.per_doc_min]:
                if pick.chunk.chunk_id not in used:
                    chosen.append(pick)
                    used.add(pick.chunk.chunk_id)
        for hit in ordered:
            if hit.chunk.chunk_id not in used:
                chosen.append(hit)
                used.add(hit.chunk.chunk_id)

        newest = max((h.chunk.meta.get("updated_at") or "" for h in hits), default="")
        segments: list[ContextSegment] = []
        total = 0
        dropped: list[str] = []
        for hit in chosen:
            text = hit.chunk.text
            tokens = estimate_tokens(text)
            notes: list[str] = []
            updated = str(hit.chunk.meta.get("updated_at") or "")
            if newest and updated and updated < newest:
                notes.append("stale")
            if float(hit.chunk.meta.get("trust", 1.0) or 1.0) < 1.0:
                notes.append("low_trust")
            if total + tokens <= self.max_tokens:
                segments.append(ContextSegment(hit.chunk.chunk_id, _source_of(hit), text, tokens, hit.score, notes))
                total += tokens
                continue
            remaining = self.max_tokens - total
            if remaining > 8:
                truncated = _fit(text, remaining)
                tok = estimate_tokens(truncated)
                notes.append("truncated")
                segments.append(ContextSegment(hit.chunk.chunk_id, _source_of(hit), truncated, tok, hit.score, notes))
                total += tok
            dropped.append(hit.chunk.chunk_id)
        return Context(segments=segments, tokens=total, dropped=dropped)
