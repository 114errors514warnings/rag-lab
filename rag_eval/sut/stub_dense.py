"""桩系统 A：纯"稠密式"重叠检索（无 IDF、无同义扩展、无重排）。

对应清单阶段一，用作 S1 的 Baseline。
"""

from __future__ import annotations

import hashlib
import json
import time

from ..schema import EvalCase, RetrievedChunk, SystemAnswer
from ._stub_common import CORPUS_PATH, load_corpus, overlap_score, tokenize


class StubDense:
    name = "stub_dense (占位件，非真实 Dense 检索)"

    def __init__(self, corpus_path=CORPUS_PATH, top_k: int = 3) -> None:
        self.corpus = load_corpus(corpus_path)
        self.top_k = top_k
        cfg = {"impl": "overlap", "top_k": top_k, "corpus": str(corpus_path)}
        self.config_hash = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]

    def retrieve(self, question: str, k: int) -> list[RetrievedChunk]:
        # 弱匹配：只做单字/单词重叠，无短语信息、无 IDF、无同义扩展、无重排
        q_tokens = tokenize(question, bigrams=False)
        scored = []
        for row in self.corpus:
            score = overlap_score(q_tokens, tokenize(row["text"], bigrams=False), normalize=False)
            scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], item[1]["chunk_id"]))
        return [
            RetrievedChunk(chunk_id=row["chunk_id"], score=round(score, 4),
                           source=row.get("source"), project_id=row.get("project_id"))
            for score, row in scored[:k]
        ]

    def answer(self, case: EvalCase, k: int) -> SystemAnswer:
        started = time.perf_counter()
        chunks = self.retrieve(case.question, k)
        # 桩系统：用命中的最高分 chunk 文本当"答案"，并引用它
        top = chunks[0] if chunks else None
        text = ""
        if top is not None:
            text = next(r["text"] for r in self.corpus if r["chunk_id"] == top.chunk_id)
        return SystemAnswer(
            answer=text,
            retrieved=chunks,
            citations=[top.chunk_id] if top is not None and top.score > 0 else [],
            prompt_tokens=len(tokenize(case.question)),
            completion_tokens=len(tokenize(text)),
            cost_usd=0.0,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
