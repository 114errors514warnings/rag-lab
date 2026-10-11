"""Rerank（阶段三）：在候选集（如 top-50）上重排，控制成本。

离线默认用**词面重排器**（Cross-Encoder 的确定性替身）：按查询词项与候选文本的
重叠度重排，同分回落到原检索分。真实项目可换 Cross-Encoder / Rerank API，接口不变。
"""

from __future__ import annotations

from ..index.bm25_store import tokenize
from ..schema import Retrieved


class LexicalReranker:
    def __init__(self, top_n: int = 50) -> None:
        self.top_n = top_n

    def rerank(self, question: str, hits: list[Retrieved], top_k: int | None = None) -> list[Retrieved]:
        query_terms = set(tokenize(question))
        scored = []
        for hit in hits[: self.top_n]:
            doc_terms = set(tokenize(hit.chunk.text))
            overlap = len(query_terms & doc_terms)
            scored.append((overlap, hit.score, hit))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2].chunk.chunk_id))
        out = [hit for _, _, hit in scored]
        return out[:top_k] if top_k else out
