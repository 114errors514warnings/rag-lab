"""Dense（语义/向量）Top-K 检索。

阶段一是纯向量检索；阶段三在此并列加入 BM25 与 Hybrid（融合、重排、改写）。
"""

from __future__ import annotations

from ..embed.embedder import Embedder
from ..index.vector_store import VectorStore
from ..schema import Retrieved


class DenseRetriever:
    def __init__(self, embedder: Embedder, store: VectorStore, min_relevance: float = 0.0) -> None:
        self.embedder = embedder
        self.store = store
        self.min_relevance = min_relevance

    def retrieve(self, question: str, k: int, flt: dict | None = None) -> list[Retrieved]:
        query_vec = self.embedder.embed([question])[0]
        hits = self.store.search(query_vec, k, flt=flt)
        return [h for h in hits if h.score > self.min_relevance]
