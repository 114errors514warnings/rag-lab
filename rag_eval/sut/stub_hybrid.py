"""桩系统 B：IDF 加权 + 同义扩展 + 模拟重排开销（对应清单阶段三）。

重要说明（避免误读）：
- 检索部分仍是**占位实现**，不是真实 Hybrid/Cross-Encoder。
- `SIMULATED_RERANK_MS_PER_CANDIDATE` 是**人为注入的模拟延迟**，目的是验证报告里的
  "护栏越线 → WARN" 这条判定链确实会触发，而不是声称本系统真的慢 600ms。
"""

from __future__ import annotations

import hashlib
import json
import time

from ..schema import EvalCase, RetrievedChunk, SystemAnswer
from ._stub_common import CORPUS_PATH, idf, load_corpus, overlap_score, tokenize

#: 每条候选的模拟重排耗时（毫秒），仅在桩系统中使用
SIMULATED_RERANK_MS_PER_CANDIDATE = 200.0

#: 同义扩展表：模拟 Query Rewrite / 语义召回带来的召回增益
SYNONYM_GROUPS: list[set[str]] = [
    {"rerank", "重排", "cross-encoder", "精排"},
    {"合并", "融合", "rrf", "倒数", "排名", "多路"},
    {"开销", "延迟", "成本", "耗时", "慢", "预算"},
    {"上下文", "token", "长度", "预算", "截断"},
    {"项目", "隔离", "串味", "多项目", "越权", "仓库", "归属", "边界"},
    {"全量", "重建", "增量", "更新", "变更", "改动"},
    {"函数", "类", "方法", "符号", "ast", "符号索引", "定义"},
    {"切块", "切片", "chunk", "分块", "重叠", "overlap"},
    {"压缩", "精简", "截断", "变短", "省", "限制"},
    {"稀疏", "bm25", "关键词", "词频"},
    {"向量", "嵌入", "embedding", "稠密", "语义"},
]


def _expand(tokens: list[str]) -> list[str]:
    out = list(tokens)
    for group in SYNONYM_GROUPS:
        if group & set(tokens):
            out.extend(group)
    return out


class StubHybrid:
    name = "stub_hybrid (占位件：IDF 加权 + 同义扩展 + 模拟重排)"

    def __init__(self, corpus_path=CORPUS_PATH, top_k: int = 3,
                 rerank_ms_per_candidate: float = SIMULATED_RERANK_MS_PER_CANDIDATE) -> None:
        self.corpus = load_corpus(corpus_path)
        self.top_k = top_k
        self.rerank_ms = rerank_ms_per_candidate
        self.weights = idf(self.corpus)
        cfg = {"impl": "idf+synonym+sim-rerank", "top_k": top_k,
               "corpus": str(corpus_path), "synonyms": len(SYNONYM_GROUPS)}
        self.config_hash = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]

    def retrieve(self, question: str, k: int) -> list[RetrievedChunk]:
        base_tokens = tokenize(question)
        q_tokens = _expand(base_tokens)
        base_set = set(base_tokens)
        # 查询原词按 IDF 计权；仅由同义扩展带来的词降权 0.5，避免扩展淹没原查询
        weights = {tok: self.weights.get(tok, 1.0) * (1.0 if tok in base_set else 0.5)
                   for tok in set(q_tokens)}
        scored = []
        for row in self.corpus:
            score = overlap_score(q_tokens, tokenize(row["text"]), weights)
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
        top = chunks[0] if chunks else None
        text = ""
        if top is not None:
            text = next(r["text"] for r in self.corpus if r["chunk_id"] == top.chunk_id)
        retrieved_ms = (time.perf_counter() - started) * 1000.0
        return SystemAnswer(
            answer=text,
            retrieved=chunks,
            citations=[top.chunk_id] if top is not None and top.score > 0 else [],
            prompt_tokens=len(tokenize(case.question)) * 2,
            completion_tokens=len(tokenize(text)),
            cost_usd=round((len(tokenize(case.question)) * 2 + len(tokenize(text))) * 2e-6, 8),
            latency_ms=retrieved_ms + len(chunks) * self.rerank_ms,
        )
