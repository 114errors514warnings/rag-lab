"""Rerank（阶段三）：在候选集（如 top-50）上重排，控制成本。

离线默认用**词面重排器**（Cross-Encoder 的确定性替身）：按查询词项与候选文本的
重叠度重排，同分回落到原检索分。真实项目可换 Cross-Encoder / Rerank API，接口不变。
"""

from __future__ import annotations

import math

from ..index.bm25_store import tokenize
from ..schema import Retrieved


class LexicalReranker:
    def __init__(self, top_n: int = 50) -> None:
        self.top_n = top_n

    def rerank(self, question: str, hits: list[Retrieved], top_k: int | None = None) -> list[Retrieved]:
        query_terms = set(tokenize(question))
        scored = []
        for hit in hits[: self.top_n]:
            doc_terms = set(tokenize(hit.chunk.text))
            overlap = len(query_terms & doc_terms)
            scored.append((overlap, hit.score, hit))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2].chunk.chunk_id))
        out = [hit for _, _, hit in scored]
        return out[:top_k] if top_k else out


class IdfReranker:
    """按查询词项的 **IDF 加权命中** 重排（在候选集内估计 df）。

    与朴素"命中计数"相比，稀有词（重排 / Project_id / Token）权重高，
    常见词（耗时 / 项目 / 时间）权重低，避免被长文档"碰巧命中"挤掉真正相关的候选。
    """

    def __init__(self, top_n: int = 50) -> None:
        self.top_n = top_n

    def rerank(self, question: str, hits: list[Retrieved], top_k: int | None = None) -> list[Retrieved]:
        candidates = list(hits[: self.top_n])
        if not candidates:
            return []
        query_terms = set(tokenize(question))
        docs = [set(tokenize(h.chunk.text)) for h in candidates]
        total = len(docs)
        df: dict[str, int] = {}
        for doc in docs:
            for term in doc:
                df[term] = df.get(term, 0) + 1

        scored = []
        for hit, doc in zip(candidates, docs):
            score = 0.0
            for term in query_terms & doc:
                score += math.log(1.0 + total / df.get(term, 1))
            scored.append((score, hit.score, hit))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2].chunk.chunk_id))
        out = [hit for _, _, hit in scored]
        return out[:top_k] if top_k else out


class SiliconFlowReranker:
    """SiliconFlow 免费 Rerank API（默认 ``BAAI/bge-reranker-v2-m3``）。

    密钥只从环境变量 ``SILICONFLOW_API_KEY`` 读取，不入库；返回的 relevance_score
    既用于重排排序，也用作拒答信号。
    """

    BASE_URL = "https://api.siliconflow.cn/v1/rerank"
    DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"

    def __init__(self, model: str = DEFAULT_MODEL, top_n: int = 50,
                 api_key_env: str = "SILICONFLOW_API_KEY") -> None:
        self.model = model or self.DEFAULT_MODEL
        self.top_n = top_n
        self.api_key_env = api_key_env
        self.name = f"siliconflow:{self.model}"

    def _key(self) -> str:
        import os

        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(f"未设置环境变量 {self.api_key_env}（密钥不入库）")
        return key

    def rerank(self, question: str, hits: list[Retrieved], top_k: int | None = None) -> list[Retrieved]:
        import httpx

        candidates = list(hits[: self.top_n])
        if not candidates:
            return []
        resp = httpx.post(
            self.BASE_URL,
            headers={"Authorization": "Bearer " + self._key()},
            json={"model": self.model, "query": question,
                  "documents": [h.chunk.text for h in candidates]},
            timeout=60,
        )
        resp.raise_for_status()
        results = resp.json()["results"]
        order = sorted(results, key=lambda x: (-float(x["relevance_score"]), int(x["index"])))
        out = [Retrieved(chunk=candidates[int(x["index"])].chunk,
                         score=round(float(x["relevance_score"]), 6)) for x in order]
        return out[:top_k] if top_k else out


class RerankedRetriever:
    """先召回 ``candidates`` 个候选，再用 reranker 重排到 ``k``。"""

    def __init__(self, base, reranker, candidates: int = 50) -> None:
        self.base = base
        self.reranker = reranker
        self.candidates = max(candidates, 1)

    def retrieve(self, question: str, k: int, flt: dict | None = None) -> list[Retrieved]:
        candidates = self.base.retrieve(question, max(k, self.candidates), flt=flt)
        return self.reranker.rerank(question, candidates, top_k=k)
