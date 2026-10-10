"""把 RAG 系统本体适配成评测协议的被测系统（Sut）。

这是 ``rag_engine`` 与 ``rag_eval`` 的**唯一连接点**：评测代码不认识流水线的内部
结构，只通过 ``answer(case, k) -> SystemAnswer`` 交互。
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from rag_eval.schema import EvalCase, RetrievedChunk, SystemAnswer

from .config import EngineConfig
from .pipeline import RAGPipeline, load_or_build

ROOT = Path(__file__).resolve().parents[1]


class MyPipeline:
    """阶段一最小系统的评测适配层。"""

    name = "rag_engine(hashing-tfidf + dense + extractive)"

    def __init__(self, config: EngineConfig | None = None) -> None:
        self.config = config or EngineConfig()
        self._root = ROOT
        self.pipeline: RAGPipeline | None = None

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
