"""rag-lab 知识服务（阶段七）。

FastAPI 封装：
- ``GET /health``：索引规模；
- ``GET /search``：``search_project``（多项目隔离，按 project_id 过滤）；
- ``POST /read_context``：``read_context``（Token 预算内组装可追溯上下文）；
- ``GET /symbol``：``get_symbol``（符号定义 + 调用点/被调用关系）。
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_engine.config import EngineConfig  # noqa: E402
from rag_engine.context.builder import ContextBuilder  # noqa: E402
from rag_engine.pipeline import load_or_build  # noqa: E402

app = FastAPI(title="RAG Knowledge Service", version="0.1.0")
_state: dict = {}


def _config_from_env() -> EngineConfig:
    """服务端引擎配置：默认离线；可用环境变量覆盖（便于经 HTTP 跑与 E 线同一配置）。"""
    import os

    kwargs: dict = {}
    for field, env, cast in (
        ("chunk_size", "RAG_CHUNK_SIZE", int),
        ("chunk_overlap", "RAG_CHUNK_OVERLAP", int),
        ("chunking", "RAG_CHUNKING", str),
        ("embed_provider", "RAG_EMBED_PROVIDER", str),
        ("embed_model", "RAG_EMBED_MODEL", str),
        ("embed_dim", "RAG_EMBED_DIM", int),
        ("retrieval", "RAG_RETRIEVAL", str),
        ("rerank", "RAG_RERANK", str),
        ("rerank_model", "RAG_RERANK_MODEL", str),
        ("rerank_candidates", "RAG_RERANK_CANDIDATES", int),
        ("min_relevance", "RAG_MIN_RELEVANCE", float),
        ("isolation", "RAG_ISOLATION", lambda v: v.strip().lower() in ("1", "true", "yes", "on")),
    ):
        value = os.environ.get(env)
        if value is not None:
            kwargs[field] = cast(value)
    return EngineConfig(**kwargs)


@app.on_event("startup")
def _startup() -> None:
    config = _config_from_env()
    _state["pipeline"] = load_or_build(config, ROOT / config.raw_dir)


def _pipeline():
    pipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(503, "index not ready")
    return pipeline


@app.get("/health")
def health() -> dict:
    pipeline = _pipeline()
    return {"status": "ok", "chunks": len(pipeline.store)}


@app.get("/search")
def search(query: str, k: int = 5, project_id: str | None = None) -> dict:
    pipeline = _pipeline()
    flt = {"project_id": project_id} if project_id else None
    hits = pipeline.retriever.retrieve(query, k, flt=flt)
    return {"results": [
        {"chunk_id": h.chunk.chunk_id, "source": h.chunk.meta.get("source"),
         "score": h.score, "snippet": h.chunk.text[:200],
         "project_id": h.chunk.meta.get("project_id"),
         "start_line": h.chunk.meta.get("start_line"),
         "end_line": h.chunk.meta.get("end_line"),
         "symbol": h.chunk.meta.get("symbol")}
        for h in hits
    ]}


class ContextBody(BaseModel):
    query: str
    token_budget: int = 600
    project_id: str | None = None


@app.post("/read_context")
def read_context(body: ContextBody) -> dict:
    pipeline = _pipeline()
    flt = {"project_id": body.project_id} if body.project_id else None
    hits = pipeline.retriever.retrieve(body.query, 8, flt=flt)
    context = ContextBuilder(max_tokens=body.token_budget).build(hits)
    return {
        "segments": [{"chunk_id": s.chunk_id, "source": s.source, "text": s.text}
                     for s in context.segments],
        "citations": [s.chunk_id for s in context.segments],
        "tokens": context.tokens,
    }


@app.get("/symbol")
def symbol(name: str = Query(...), project_id: str | None = None) -> dict:
    from rag_engine.code_rag import build_dependency_graph, index_code

    graph = build_dependency_graph(index_code(ROOT / "data" / "code_corpus"))
    info = graph.get(name)
    if not info or (project_id and info.get("project_id") != project_id):
        raise HTTPException(404, f"symbol not found: {name}")
    return {"def": name, "file": info.get("file"), "kind": info.get("kind"),
            "project_id": info.get("project_id"),
            "callers": info.get("callers", []), "callees": info.get("callees", [])}
