"""稀疏（BM25 关键词）检索（阶段三）。"""

from __future__ import annotations

from ..index.bm25_store import BM25Store
from ..schema import Retrieved


class SparseRetriever:
    def __init__(self, store: BM25Store) -> None:
        self.store = store

    def retrieve(self, question: str, k: int, flt: dict | None = None) -> list[Retrieved]:
        return self.store.search(question, k, flt=flt)
