"""MCP 工具（阶段七，签名冻结）。

```
search_project(project_id, query, k=5, filters?) -> [{chunk_id, source, score, snippet}]
get_symbol(project_id, symbol, kind?)            -> {def, file, span, callers[], callees[]}
read_context(project_id, query, token_budget)    -> {segments:[{chunk_id,source,text}], citations[]}
```

以**极简 JSON-Lines stdio** 协议暴露：每行一个 ``{"tool": name, "args": {...}}`` 请求，
输出一行 JSON 结果。接入 Cline/Codex 时替换为官方 MCP SDK 即可，下列工具函数不变。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_engine.config import EngineConfig  # noqa: E402
from rag_engine.context.builder import ContextBuilder  # noqa: E402
from rag_engine.pipeline import load_or_build  # noqa: E402

_PIPELINE = None


def _pipeline():
    global _PIPELINE
    if _PIPELINE is None:
        config = EngineConfig()
        _PIPELINE = load_or_build(config, ROOT / config.raw_dir)
    return _PIPELINE


def search_project(project_id: str | None, query: str, k: int = 5, filters: dict | None = None) -> list[dict]:
    flt = dict(filters or {})
    if project_id:
        flt["project_id"] = project_id
    hits = _pipeline().retriever.retrieve(query, k, flt=flt or None)
    return [{"chunk_id": h.chunk.chunk_id, "source": h.chunk.meta.get("source"),
             "score": h.score, "snippet": h.chunk.text[:200]} for h in hits]


def get_symbol(project_id: str | None, symbol: str, kind: str | None = None) -> dict:
    from rag_engine.code_rag import build_dependency_graph, index_code

    graph = build_dependency_graph(index_code(ROOT / "data" / "code_corpus"))
    info = graph.get(symbol)
    if not info or (project_id and info.get("project_id") != project_id):
        return {"error": f"symbol not found: {symbol}"}
    return {"def": symbol, "file": info.get("file"), "kind": kind or info.get("kind"),
            "span": None, "callers": info.get("callers", []), "callees": info.get("callees", [])}


def read_context(project_id: str | None, query: str, token_budget: int = 600) -> dict:
    flt = {"project_id": project_id} if project_id else None
    hits = _pipeline().retriever.retrieve(query, 8, flt=flt)
    context = ContextBuilder(max_tokens=token_budget).build(hits)
    return {"segments": [{"chunk_id": s.chunk_id, "source": s.source, "text": s.text}
                         for s in context.segments],
            "citations": [s.chunk_id for s in context.segments]}


TOOLS = {"search_project": search_project, "get_symbol": get_symbol, "read_context": read_context}


def serve() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            result = TOOLS[request["tool"]](**request.get("args", {}))
        except Exception as exc:  # noqa: BLE001
            result = {"error": str(exc)}
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    serve()
