"""S3 L1（补充）：Query Rewrite 扩展 与 IDF 加权重排。"""

from __future__ import annotations

from rag_engine.retrieve.rerank import IdfReranker
from rag_engine.retrieve.rewrite import multi_query, rewrite
from rag_engine.schema import Chunk, Retrieved


def test_rewrite_expands_domain_terms() -> None:
    assert rewrite("精排环节太慢怎么办")[0] == "精排环节太慢怎么办"
    expanded = rewrite("长回答要怎么压缩才省钱")
    assert len(expanded) == 2
    assert "成本" in expanded[1] or "预算" in expanded[1] or "token" in expanded[1]
    assert multi_query("代码库怎么做检索")[1]  # 有扩展


def test_rewrite_is_deterministic() -> None:
    assert rewrite("怎么防止跨项目越权检索") == rewrite("怎么防止跨项目越权检索")


def _hit(cid: str, text: str, score: float = 1.0) -> Retrieved:
    return Retrieved(chunk=Chunk(chunk_id=cid, doc_id=cid, text=text, meta={}), score=score)


def test_idf_reranker_prefers_rare_term() -> None:
    hits = [
        _hit("common:0000", "耗时 时间 项目 的常见说明", score=0.9),      # 常见词命中多
        _hit("rare:0000", "Token Budget 用于限制上下文长度", score=0.5),  # 稀有词命中
    ]
    reranked = IdfReranker().rerank("token budget 上下文长度", hits, top_k=2)
    assert reranked[0].chunk.chunk_id == "rare:0000"


def test_idf_reranker_is_deterministic() -> None:
    hits = [_hit("a:0000", "内容 甲"), _hit("b:0000", "内容 乙")]
    assert [h.chunk.chunk_id for h in IdfReranker().rerank("内容", hits)] == \
           [h.chunk.chunk_id for h in IdfReranker().rerank("内容", hits)]
