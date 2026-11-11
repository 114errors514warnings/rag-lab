"""D3 L1：增量索引——只嵌入变化过的切片，旧向量逐字节复用。"""

from __future__ import annotations

import numpy as np

from rag_engine.config import EngineConfig
from rag_engine.pipeline import RAGPipeline
from rag_engine.schema import Document


class CountingEmbedder:
    """确定性假嵌入器：记录每次被要求嵌入多少条。"""

    def __init__(self) -> None:
        self.calls: list[int] = []

    def embed(self, texts):
        self.calls.append(len(texts))
        rows = []
        for index, text in enumerate(texts):
            rows.append([float(len(text)), float(index + 1), float(len(text) % 7), 1.0])
        return np.asarray(rows, dtype=np.float32) if rows else np.zeros((0, 4), dtype=np.float32)

    def save(self, directory) -> None:      # pragma: no cover - 测试不落盘
        return None


def _docs(pairs):
    return [Document(doc_id=name, source=f"{name}.md", doc_type="md", text=text,
                     project_id="demo")
            for name, text in pairs]


def _config(dim: int = 4) -> EngineConfig:
    return EngineConfig(embed_provider="siliconflow", embed_dim=dim,
                        chunk_size=60, chunk_overlap=0, retrieval="dense")


def test_incremental_embeds_only_changed_chunks():
    config = _config()
    embedder = CountingEmbedder()
    first = RAGPipeline.build_incremental(
        config, _docs([("a", "alpha " * 30), ("b", "beta " * 30)]), old=None, embedder=embedder)
    assert first.last_incremental["mode"] == "full"
    total = len(first.store.chunks)
    assert embedder.calls == [total]

    embedder.calls.clear()
    second = RAGPipeline.build_incremental(
        config,
        _docs([("a", "alpha " * 30), ("b", "beta " * 29 + "BETA ")]),
        old=first, embedder=embedder)

    assert second.last_incremental["mode"] == "incremental"
    assert second.last_incremental["reused"] > 0
    assert second.last_incremental["embedded"] == sum(embedder.calls)
    assert sum(embedder.calls) < total          # 只嵌入了变化文件的那部分


def test_unchanged_vectors_are_reused_byte_for_byte():
    config = _config()
    first = RAGPipeline.build_incremental(
        config, _docs([("a", "alpha " * 30), ("b", "beta " * 30)]),
        old=None, embedder=CountingEmbedder())
    old_vec = {chunk.chunk_id: first.store._matrix[i]
               for i, chunk in enumerate(first.store.chunks)}

    second = RAGPipeline.build_incremental(
        config, _docs([("a", "alpha " * 30), ("b", "beta " * 30), ("c", "gamma " * 20)]),
        old=first, embedder=CountingEmbedder())

    for index, chunk in enumerate(second.store.chunks):
        if chunk.chunk_id in old_vec:
            assert np.array_equal(second.store._matrix[index], old_vec[chunk.chunk_id])
    assert second.last_incremental["embedded"] > 0      # 只有新文件被嵌入


def test_same_chunk_id_but_changed_text_is_not_reused():
    """位置没变、内容变了（同 chunk_id）必须重新嵌入。"""
    config = _config()
    first = RAGPipeline.build_incremental(
        config, _docs([("a", "one two three four five six seven eight nine ten")]),
        old=None, embedder=CountingEmbedder())

    embedder = CountingEmbedder()
    second = RAGPipeline.build_incremental(
        config, _docs([("a", "one two three four five six seven eight nine ELEVEN")]),
        old=first, embedder=embedder)

    assert second.last_incremental["reused"] == 0
    assert second.last_incremental["embedded"] == len(second.store.chunks)


def test_removed_documents_disappear():
    config = _config()
    first = RAGPipeline.build_incremental(
        config, _docs([("a", "alpha " * 30), ("b", "beta " * 30)]),
        old=None, embedder=CountingEmbedder())
    second = RAGPipeline.build_incremental(
        config, _docs([("a", "alpha " * 30)]), old=first, embedder=CountingEmbedder())
    assert {chunk.doc_id for chunk in second.store.chunks} == {"a"}
