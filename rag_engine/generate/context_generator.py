"""使用 Context Builder 的抽取式生成（阶段四）。

先经 ``ContextBuilder`` 在预算内组装上下文，再据此生成回答并逐条标注 ``chunk_id`` 来源，
使"压缩/裁剪后来源不丢"可由评测的 citations 验证。
"""

from __future__ import annotations

from typing import Sequence

from ..context.builder import ContextBuilder
from ..schema import Retrieved
from ..utils import estimate_tokens
from .generator import Generation


class ContextExtractiveGenerator:
    def __init__(self, max_tokens: int = 600, max_chunks: int = 5,
                 relevance_threshold: float = 0.0) -> None:
        self.builder = ContextBuilder(max_tokens=max_tokens, relevance_threshold=relevance_threshold)
        self.max_chunks = max_chunks

    def generate(self, question: str, retrieved: Sequence[Retrieved]) -> Generation:
        context = self.builder.build(list(retrieved))
        segments = context.segments[: self.max_chunks]
        if not segments:
            return Generation(answer="", citations=[], prompt_tokens=estimate_tokens(question))
        parts = [f"{seg.text}（来源：{seg.chunk_id}）" for seg in segments]
        answer = " ".join(parts)
        citations = [seg.chunk_id for seg in segments]
        prompt_tokens = estimate_tokens(question) + sum(seg.tokens for seg in segments)
        return Generation(
            answer=answer,
            citations=citations,
            prompt_tokens=prompt_tokens,
            completion_tokens=estimate_tokens(answer),
            cost_usd=0.0,
        )
