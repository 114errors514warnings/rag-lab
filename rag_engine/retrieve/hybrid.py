"""Hybrid 检索：Dense + Sparse 的 RRF 融合（阶段三）。

RRF：``score = Σ 1/(k + rank)``（rank 从 1 开始），无需量纲归一化；融合结果确定。
"""

from __future__ import annotations

from ..schema import Retrieved


def rrf_fuse(rank_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """把若干「按名次排列的 id 列表」融合为 ``[(id, score)]``（降序，同分按 id 升序）。"""
    scores: dict[str, float] = {}
    for ranking in rank_lists:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


class HybridRetriever:
    def __init__(self, dense, sparse, rrf_k: int = 60, candidates: int = 50) -> None:
        self.dense = dense
        self.sparse = sparse
        self.rrf_k = rrf_k
        self.candidates = candidates

    def retrieve(self, question: str, k: int, flt: dict | None = None) -> list[Retrieved]:
        n = max(k, self.candidates)
        dense_hits = self.dense.retrieve(question, n, flt=flt)
        sparse_hits = self.sparse.retrieve(question, n, flt=flt)
        by_id = {h.chunk.chunk_id: h.chunk for h in dense_hits}
        by_id.update({h.chunk.chunk_id: h.chunk for h in sparse_hits})
        fused = rrf_fuse(
            [[h.chunk.chunk_id for h in dense_hits], [h.chunk.chunk_id for h in sparse_hits]],
            k=self.rrf_k,
        )
        out: list[Retrieved] = []
        for chunk_id, score in fused[:k]:
            chunk = by_id.get(chunk_id)
            if chunk is not None:
                out.append(Retrieved(chunk=chunk, score=round(score, 6)))
        return out
