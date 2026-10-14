"""把各层组装成一条可运行的 RAG 流水线。

阶段一能力：从目录建索引并持久化 -> 载入 -> Top-K 检索 -> 带引用回答。
持久化带 **来源清单（manifest）**：源文件或配置一变就重建；阶段二会把这里的
"整目录重建"细化为"只重建受影响的文档"。
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import EngineConfig
from .embed.embedder import HashingTfidfEmbedder, OpenAIEmbedder, SiliconFlowEmbedder, build_embedder
from .generate.generator import Generation, build_generator
from .index.vector_store import NumpyVectorStore
from .ingest.chunker import chunk_documents
from .ingest.clean import clean_documents, dedupe_documents
from .ingest.loader import iter_source_files, load_tree
from .ingest.metadata import build_chunk_meta
from .retrieve.dense import DenseRetriever
from .schema import Document, Retrieved


@dataclass
class Answer:
    answer: str
    retrieved: list[Retrieved] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    context_chunk_ids: list[str] = field(default_factory=list)
    refused: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_manifest(raw_dir: Path | str) -> dict[str, str]:
    """来源文件 -> 内容 sha256，用于判断索引是否需要重建。"""
    raw_dir = Path(raw_dir)
    return {p.relative_to(raw_dir).as_posix(): _file_sha256(p) for p in iter_source_files(raw_dir)}


def _make_retriever(config: EngineConfig, embedder, store):
    """按 ``config.retrieval`` / ``config.rerank`` 组装检索器（``build`` 与 ``load`` 共用）。

    - retrieval: dense | bm25 | hybrid（Dense+BM25 RRF）
    - rerank:    none | lexical | idf | siliconflow（在候选集上重排）
    拒答阈值在 pipeline 层统一处理，此处的 dense 不预过滤。
    """
    from .index.bm25_store import BM25Store
    from .retrieve.hybrid import HybridRetriever
    from .retrieve.rerank import IdfReranker, LexicalReranker, RerankedRetriever, SiliconFlowReranker
    from .retrieve.sparse import SparseRetriever

    dense = DenseRetriever(embedder, store, min_relevance=0.0)
    mode = getattr(config, "retrieval", "dense")
    if mode == "dense":
        base = dense
    elif mode in ("bm25", "hybrid"):
        bm25 = BM25Store()
        bm25.add(list(store.chunks))
        base = SparseRetriever(bm25) if mode == "bm25" else HybridRetriever(
            dense, SparseRetriever(bm25), candidates=config.rerank_candidates)
    else:
        raise ValueError(f"未知 retrieval：{mode}")

    kind = getattr(config, "rerank", "none")
    if kind == "none":
        return base
    factories = {
        "lexical": lambda: LexicalReranker(top_n=config.rerank_candidates),
        "idf": lambda: IdfReranker(top_n=config.rerank_candidates),
        "siliconflow": lambda: SiliconFlowReranker(top_n=config.rerank_candidates),
    }
    if kind not in factories:
        raise ValueError(f"未知 rerank：{kind}")
    return RerankedRetriever(base, factories[kind](), candidates=config.rerank_candidates)


class RAGPipeline:
    def __init__(self, config: EngineConfig, embedder, store, retriever, generator) -> None:
        self.config = config
        self.embedder = embedder
        self.store = store
        self.retriever = retriever
        self.generator = generator

    # ------------------------------------------------------------ 构建
    @classmethod
    def build(cls, config: EngineConfig, docs: list[Document]) -> "RAGPipeline":
        # 阶段二：清洗 + 去重 + 元数据 enrichment（切块边界契约不变，chunk_id 仍稳定）
        docs = dedupe_documents(clean_documents(docs))[0]
        if getattr(config, "chunking", "fixed") == "symbol":
            from .ingest.symbol_chunker import chunk_documents_symbol

            chunks = chunk_documents_symbol(docs, size=config.chunk_size, overlap=config.chunk_overlap)
        elif getattr(config, "chunking", "fixed") == "symbol_union":
            from .ingest.symbol_chunker import chunk_documents_symbol_union

            chunks = chunk_documents_symbol_union(docs, size=config.chunk_size, overlap=config.chunk_overlap)
        else:
            chunks = chunk_documents(docs, size=config.chunk_size, overlap=config.chunk_overlap)
        by_id = {doc.doc_id: doc for doc in docs}
        for chunk in chunks:
            if chunk.meta.get("kind"):
                continue  # 符号块/模块块自带 meta（symbol/kind/file/span），不覆盖
            doc = by_id.get(chunk.doc_id)
            if doc is not None:
                chunk.meta.update(build_chunk_meta(
                    doc, doc.text, chunk.meta.get("start", 0), chunk.meta.get("end", 0),
                    chunk.meta.get("order", 0)))
        texts = [c.text for c in chunks]
        embedder = build_embedder(config.embed_provider, config.embed_dim, config.embed_model, texts)
        vectors = embedder.embed(texts)
        store = NumpyVectorStore()
        store.add(chunks, vectors)
        retriever = _make_retriever(config, embedder, store)
        generator = build_generator(config.generator, config.gen_model, config.max_context_chunks)
        return cls(config, embedder, store, retriever, generator)

    # ------------------------------------------------------------ 查询
    def answer(self, question: str, k: int | None = None,
               project_id: str | None = None) -> Answer:
        started = time.perf_counter()
        k = k or self.config.top_k
        flt = {"project_id": project_id} if project_id else None
        hits = self.retriever.retrieve(question, k, flt=flt)
        gen: Generation = self.generator.generate(question, hits)
        min_rel = self.config.min_relevance
        low = bool(min_rel) and (not hits or hits[0].score < min_rel)
        refused = low or (not hits) or (not gen.citations)
        latency = (time.perf_counter() - started) * 1000.0
        if low:
            # 拒答：不返回引用/答案，避免引用无关证据（检索结果仍保留在 trace 中）
            return Answer(
                answer="", retrieved=hits,
                context_chunk_ids=[h.chunk.chunk_id for h in hits], refused=True,
                prompt_tokens=gen.prompt_tokens, completion_tokens=0,
                cost_usd=gen.cost_usd, latency_ms=latency,
            )
        return Answer(
            answer=gen.answer,
            retrieved=hits,
            citations=gen.citations,
            context_chunk_ids=[h.chunk.chunk_id for h in hits],
            refused=refused,
            prompt_tokens=gen.prompt_tokens,
            completion_tokens=gen.completion_tokens,
            cost_usd=gen.cost_usd,
            latency_ms=latency,
        )

    # ------------------------------------------------------------ 持久化
    def persist(self, index_dir: Path | str, manifest: dict[str, str]) -> None:
        index_dir = Path(index_dir)
        index_dir.mkdir(parents=True, exist_ok=True)
        self.embedder.save(index_dir)
        self.store.save(index_dir)
        (index_dir / "index.json").write_text(
            json.dumps(
                {"config_fingerprint": self.config.fingerprint(), "manifest": manifest},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, config: EngineConfig, index_dir: Path | str) -> "RAGPipeline":
        index_dir = Path(index_dir)
        if config.embed_provider == "siliconflow":
            use_model = config.embed_model if "/" in config.embed_model else SiliconFlowEmbedder.DEFAULT_MODEL
            embedder = SiliconFlowEmbedder(model=use_model, dim=config.embed_dim)
        elif config.embed_provider == "openai":
            embedder = OpenAIEmbedder(model=config.embed_model, dim=config.embed_dim)
        else:
            embedder = HashingTfidfEmbedder.load(index_dir)
        store = NumpyVectorStore.load(index_dir)
        retriever = _make_retriever(config, embedder, store)
        generator = build_generator(config.generator, config.gen_model, config.max_context_chunks)
        return cls(config, embedder, store, retriever, generator)


def load_or_build(config: EngineConfig, raw_dir: Path | str | None = None) -> RAGPipeline:
    """有可用索引则载入，否则从 ``raw_dir`` 重建并持久化。"""
    raw_dir = Path(raw_dir or config.raw_dir)
    index_dir = Path(config.index_dir)
    manifest = compute_manifest(raw_dir)

    index_meta = index_dir / "index.json"
    if index_meta.exists() and (index_dir / "chunks.jsonl").exists():
        try:
            meta = json.loads(index_meta.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
        if meta.get("config_fingerprint") == config.fingerprint() and meta.get("manifest") == manifest:
            return RAGPipeline.load(config, index_dir)

    docs = load_tree(raw_dir)
    pipeline = RAGPipeline.build(config, docs)
    pipeline.persist(index_dir, manifest)
    return pipeline
