"""Code RAG 方案（阶段五）：在独立代码语料上做符号级检索。"""

from __future__ import annotations

from .eval_adapter import MyPipeline
from .pipeline import RAGPipeline


class CodeRagPipeline(MyPipeline):
    """AST 结构化切块 + Dense 检索（按 project_id 过滤，保证零泄漏）。"""

    name = "rag_engine(code corpus: AST symbols + dense)"
    corpus = "data/code_corpus"

    @property
    def config_hash(self) -> str:
        return self.config.fingerprint() + "-code"

    def _ensure(self) -> RAGPipeline:
        if self.pipeline is not None:
            return self.pipeline
        from .code_rag import index_code
        from .embed.embedder import build_embedder
        from .generate.generator import build_generator
        from .index.vector_store import NumpyVectorStore
        from .retrieve.dense import DenseRetriever

        chunks = index_code(self._root / self.corpus)
        texts = [c.text for c in chunks]
        embedder = build_embedder("hashing", self.config.embed_dim, "", texts)
        store = NumpyVectorStore()
        store.add(chunks, embedder.embed(texts))
        retriever = DenseRetriever(embedder, store, min_relevance=self.config.min_relevance)
        generator = build_generator("extractive", "", 10)
        self.pipeline = RAGPipeline(self.config, embedder, store, retriever, generator)
        return self.pipeline

    def answer(self, case, k: int):
        # 代码检索固定按 project_id 过滤（隔离护栏），k 由 gates 给到 10
        return super().answer(case, k)


class CodeRagHybridPipeline(CodeRagPipeline):
    """符号 Dense + BM25 RRF（阶段五 Hybrid 变体，用于 recall@10 不下降对比）。"""

    name = "rag_engine(code corpus: AST symbols + dense+bm25 RRF)"

    @property
    def config_hash(self) -> str:
        return self.config.fingerprint() + "-code-hybrid"

    def _ensure(self) -> RAGPipeline:
        pipeline = super()._ensure()
        if getattr(pipeline, "_code_hybrid", False):
            return pipeline
        from .index.bm25_store import BM25Store
        from .retrieve.hybrid import HybridRetriever
        from .retrieve.sparse import SparseRetriever

        bm25 = BM25Store()
        bm25.add(pipeline.store.chunks)
        pipeline.retriever = HybridRetriever(pipeline.retriever, SparseRetriever(bm25), candidates=30)
        pipeline._code_hybrid = True
        return pipeline
