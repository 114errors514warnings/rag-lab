"""S3 L1：RRF 融合的确定性与 Hybrid 合并。"""

from __future__ import annotations

from rag_engine.retrieve.hybrid import HybridRetriever, rrf_fuse
from rag_engine.schema import Chunk, Retrieved


def test_rrf_fuse_deterministic_and_expected_order() -> None:
    lists = [["a", "b", "c"], ["b", "a", "d"]]
    first = rrf_fuse(lists, k=60)
    second = rrf_fuse(lists, k=60)
    assert first == second                      # 确定性
    assert [cid for cid, _ in first] == ["a", "b", "c", "d"]
    # a、b 同分（1/61+1/62），c、d 同分（1/63）
    scores = dict(first)
    assert abs(scores["a"] - scores["b"]) < 1e-12
    assert abs(scores["c"] - scores["d"]) < 1e-12
    assert scores["a"] > scores["c"]


def test_rrf_single_list_is_identity() -> None:
    fused = rrf_fuse([["x", "y"]])
    assert [cid for cid, _ in fused] == ["x", "y"]


class _StubRetriever:
    def __init__(self, ids: list[str], text_map: dict[str, str]) -> None:
        self.ids = ids
        self.text_map = text_map

    def retrieve(self, question: str, k: int, flt=None):
        out = []
        for cid in self.ids[:k]:
            chunk = Chunk(chunk_id=cid, doc_id=cid.split(":")[0],
                          text=self.text_map.get(cid, cid), meta={})
            out.append(Retrieved(chunk=chunk, score=1.0))
        return out


def test_hybrid_merges_dense_and_sparse() -> None:
    text = {"a:0000": "alpha", "b:0000": "bravo", "c:0000": "charlie"}
    dense = _StubRetriever(["a:0000", "b:0000"], text)
    sparse = _StubRetriever(["b:0000", "c:0000"], text)
    hybrid = HybridRetriever(dense, sparse, candidates=10)
    hits = hybrid.retrieve("q", k=3)
    ids = [h.chunk.chunk_id for h in hits]
    # b 在两路都出现 => 融合分最高；a、c 各一路
    assert ids[0] == "b:0000"
    assert set(ids) == {"a:0000", "b:0000", "c:0000"}
