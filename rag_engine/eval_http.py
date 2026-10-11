"""阶段七：走 HTTP 的被测系统（S7 部署冒烟）。

评测框架**直接调用**被测进程（in-process）会绕过网络/协议层；本适配器改为经真实 HTTP
调用本地服务，验证"服务真的跑得起来、可复现"。
"""

from __future__ import annotations

import os
import time

import httpx

from rag_eval.schema import RetrievedChunk, SystemAnswer

from .eval_adapter import MyPipeline


class HttpPipeline(MyPipeline):
    name = "rag_engine via HTTP service"
    base_url = os.getenv("RAG_SERVICE_URL", "http://127.0.0.1:8099")

    @property
    def config_hash(self) -> str:
        return self.config.fingerprint() + "-http"

    def _ensure(self):  # 不构建本地索引，索引在服务进程内
        return None

    def answer(self, case, k: int) -> SystemAnswer:
        params: dict = {"query": case.question, "k": k}
        if case.project_id:
            params["project_id"] = case.project_id
        started = time.perf_counter()
        results: list[dict] = []
        try:
            resp = httpx.get(f"{self.base_url}/search", params=params, timeout=30.0)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception:  # noqa: BLE001 - 服务不可达 → 记 0 命中（success_rate 会反映）
            results = []
        retrieved = [
            RetrievedChunk(chunk_id=x["chunk_id"], score=float(x.get("score", 0.0)),
                           source=x.get("source"), project_id=x.get("project_id"))
            for x in results
        ]
        answer = " ".join(x.get("snippet", "") for x in results[:3])
        citations = [x["chunk_id"] for x in results[:3]]
        return SystemAnswer(
            answer=answer,
            retrieved=retrieved,
            citations=citations,
            prompt_tokens=max(1, len(case.question)),
            completion_tokens=max(1, len(answer) // 2),
            cost_usd=0.0,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
