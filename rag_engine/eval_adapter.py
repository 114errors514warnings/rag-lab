"""把 RAG 系统本体适配成评测协议的被测系统（Sut）。

这是 ``rag_engine`` 与 ``rag_eval`` 的**唯一连接点**：评测代码不认识流水线的内部
结构，只通过 ``answer(case, k) -> SystemAnswer`` 交互。
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from rag_eval.schema import EvalCase, RetrievedChunk, SystemAnswer

from .config import EngineConfig
from .pipeline import RAGPipeline, load_or_build
from .schema import Chunk

ROOT = Path(__file__).resolve().parents[1]


class MyPipeline:
    """系统本体的评测适配层（``name`` 随配置动态反映真实模型/切块/检索）。"""

    def __init__(self, config: EngineConfig | None = None) -> None:
        self.config = config or EngineConfig()
        self._root = ROOT
        self.pipeline: RAGPipeline | None = None

    @property
    def name(self) -> str:
        cfg = self.config
        if cfg.embed_provider == "siliconflow":
            emb = f"siliconflow:{cfg.embed_model}"
        elif cfg.embed_provider == "openai":
            emb = f"openai:{cfg.embed_model}"
        else:
            emb = "hashing-tfidf"
        parts = [emb, cfg.chunking, getattr(cfg, "retrieval", "dense")]
        rerank = getattr(cfg, "rerank", "none")
        if rerank != "none":
            tag = f"rerank:{rerank}"
            if rerank == "siliconflow":
                tag += f":{cfg.rerank_model}"
            parts.append(tag)
        parts.append("extractive")
        return "rag_engine(" + " + ".join(parts) + ")"

    @property
    def config_hash(self) -> str:
        return self.config.fingerprint()

    def _ensure(self) -> RAGPipeline:
        if self.pipeline is None:
            raw_dir = self._root / self.config.raw_dir
            index_dir = self._root / self.config.index_dir
            cfg = replace(self.config, index_dir=str(index_dir))
            self.pipeline = load_or_build(cfg, raw_dir)
        return self.pipeline

    def answer(self, case: EvalCase, k: int) -> SystemAnswer:
        result = self._ensure().answer(case.question, k=k, project_id=case.project_id)
        return SystemAnswer(
            answer=result.answer,
            retrieved=[
                RetrievedChunk(
                    chunk_id=hit.chunk.chunk_id,
                    score=hit.score,
                    source=hit.chunk.meta.get("source"),
                    project_id=hit.chunk.meta.get("project_id"),
                    start_line=hit.chunk.meta.get("start_line"),
                    end_line=hit.chunk.meta.get("end_line"),
                    symbol=hit.chunk.meta.get("symbol"),
                )
                for hit in result.retrieved
            ],
            citations=result.citations,
            context_chunk_ids=result.context_chunk_ids,
            refused=result.refused,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
        )


class MyHybridPipeline(MyPipeline):
    """阶段三：Dense + BM25 的 RRF 融合检索（其余与 S1 相同）。"""

    name = "rag_engine(hashing-tfidf + dense+bm25 RRF + extractive)"

    @property
    def config_hash(self) -> str:
        return self.config.fingerprint() + "-hybrid"

    def _ensure(self) -> RAGPipeline:
        pipeline = super()._ensure()
        if getattr(pipeline, "_hybrid_installed", False):
            return pipeline
        from .index.bm25_store import BM25Store
        from .retrieve.hybrid import HybridRetriever
        from .retrieve.sparse import SparseRetriever

        bm25 = BM25Store()
        bm25.add(pipeline.store.chunks)
        pipeline.retriever = HybridRetriever(pipeline.retriever, SparseRetriever(bm25), candidates=50)
        pipeline._hybrid_installed = True
        return pipeline


class DemoDensePipeline(MyPipeline):
    """在 ``retrieval_v1`` 对齐的 demo 语料上运行**真实 Dense**（hashing-tfidf）。

    说明：``retrieval_v1`` 的 ``relevant_chunk_ids``（c01…）对齐 ``data/corpus/demo.jsonl``，
    而 ``my_pipeline`` 索引的是项目 kb（chunk_id 形如 ``rag-md-…:0000``），二者不对齐。
    本系统直接用 demo 语料的 chunk_id 建真实向量索引，使 S3 的四方案对比在同一语料上成立。
    """

    name = "rag_engine(demo corpus: hashing-tfidf dense)"
    corpus = "data/corpus/demo.jsonl"

    def _build_demo(self) -> RAGPipeline:
        from .embed.embedder import build_embedder
        from .generate.generator import build_generator
        from .index.vector_store import NumpyVectorStore
        from .retrieve.dense import DenseRetriever

        rows = [json.loads(line) for line in (ROOT / self.corpus).read_text(encoding="utf-8").splitlines()
                if line.strip()]
        chunks = [Chunk(chunk_id=r["chunk_id"], doc_id=r["chunk_id"], text=r["text"],
                        meta={"source": r.get("source"), "project_id": r.get("project_id")}) for r in rows]
        texts = [c.text for c in chunks]
        embedder = build_embedder("hashing", self.config.embed_dim, "", texts)
        vectors = embedder.embed(texts)
        store = NumpyVectorStore()
        store.add(chunks, vectors)
        retriever = DenseRetriever(embedder, store, min_relevance=self.config.min_relevance)
        generator = build_generator("extractive", "", self.config.max_context_chunks)
        return RAGPipeline(self.config, embedder, store, retriever, generator)

    def _ensure(self) -> RAGPipeline:
        if self.pipeline is None:
            self.pipeline = self._build_demo()
        return self.pipeline


class DemoHybridPipeline(DemoDensePipeline):
    """demo 语料上的真实 Dense + BM25 的 RRF 融合（S3 Hybrid 方案）。"""

    name = "rag_engine(demo corpus: hashing-tfidf + bm25 RRF)"

    @property
    def config_hash(self) -> str:
        return self.config.fingerprint() + "-demo-hybrid"

    def _ensure(self) -> RAGPipeline:
        pipeline = super()._ensure()
        if getattr(pipeline, "_hybrid_installed", False):
            return pipeline
        from .index.bm25_store import BM25Store
        from .retrieve.hybrid import HybridRetriever
        from .retrieve.sparse import SparseRetriever

        bm25 = BM25Store()
        bm25.add(pipeline.store.chunks)
        pipeline.retriever = HybridRetriever(pipeline.retriever, SparseRetriever(bm25), candidates=50)
        pipeline._hybrid_installed = True
        return pipeline
