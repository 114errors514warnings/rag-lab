"""S3 · Rerank 方案（demo 语料）：Hybrid 候选（top-N）+ 词面重排。"""

from __future__ import annotations

from .eval_adapter import DemoDensePipeline, DemoHybridPipeline
from .pipeline import RAGPipeline
from .retrieve.rerank import LexicalReranker
from .retrieve.rewrite import multi_query
from .schema import Retrieved


class _RerankRetriever:
    """把任意检索器包一层重排（Cross-Encoder 的离线确定性替身）。"""

    def __init__(self, base, reranker: LexicalReranker, top_n: int = 50) -> None:
        self.base = base
        self.reranker = reranker
        self.top_n = top_n

    def retrieve(self, question: str, k: int, flt: dict | None = None):
        hits = self.base.retrieve(question, max(k, self.top_n), flt=flt)
        return self.reranker.rerank(question, hits, top_k=k)


class DemoRerankPipeline(DemoHybridPipeline):
    name = "rag_engine(demo corpus: dense+bm25 RRF + lexical rerank)"

    @property
    def config_hash(self) -> str:
        return self.config.fingerprint() + "-demo-rerank"

    def _ensure(self) -> RAGPipeline:
        pipeline = super()._ensure()
        if getattr(pipeline, "_rerank_installed", False):
            return pipeline
        pipeline.retriever = _RerankRetriever(pipeline.retriever, LexicalReranker(top_n=50), top_n=50)
        pipeline._rerank_installed = True
        return pipeline


class _MultiQueryRetriever:
    """对改写后的多条查询分别检索，再用 RRF 融合。"""

    def __init__(self, base, per_query: int = 30) -> None:
        self.base = base
        self.per_query = per_query

    def retrieve(self, question: str, k: int, flt: dict | None = None):
        from .retrieve.hybrid import rrf_fuse

        queries = multi_query(question)
        rankings: list[list[str]] = []
        by_id = {}
        for query in queries:
            hits = self.base.retrieve(query, max(k, self.per_query), flt=flt)
            rankings.append([h.chunk.chunk_id for h in hits])
            by_id.update({h.chunk.chunk_id: h.chunk for h in hits})
        fused = rrf_fuse(rankings)
        return [Retrieved(chunk=by_id[cid], score=round(score, 6))
                for cid, score in fused[:k] if cid in by_id]


class DemoMultiPipeline(DemoHybridPipeline):
    name = "rag_engine(demo corpus: multi-query dense+bm25 RRF + rerank)"

    @property
    def config_hash(self) -> str:
        return self.config.fingerprint() + "-demo-multi"

    def _ensure(self) -> RAGPipeline:
        pipeline = super()._ensure()
        if getattr(pipeline, "_multi_installed", False):
            return pipeline
        pipeline.retriever = _RerankRetriever(_MultiQueryRetriever(pipeline.retriever, per_query=30),
                                             LexicalReranker(top_n=50), 50)
        pipeline._multi_installed = True
        return pipeline


class DemoContextPipeline(DemoDensePipeline):
    """demo 语料 + Context Builder（阶段四）：在 Token 预算内组装可追溯上下文。"""

    name = "rag_engine(demo corpus: dense + context builder)"

    @property
    def config_hash(self) -> str:
        return self.config.fingerprint() + "-demo-context"

    def _ensure(self) -> RAGPipeline:
        pipeline = super()._ensure()
        if getattr(pipeline, "_context_installed", False):
            return pipeline
        from .generate.context_generator import ContextExtractiveGenerator

        pipeline.generator = ContextExtractiveGenerator(max_tokens=600, max_chunks=5)
        pipeline._context_installed = True
        return pipeline
