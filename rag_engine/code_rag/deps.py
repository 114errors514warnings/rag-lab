"""跨文件依赖关系（阶段五）。

从结构化切片中抽取"符号 → 被调用符号"的关系，供 ``get_symbol`` 的 callers/callees 使用。
"""

from __future__ import annotations

from ..schema import Chunk


def build_dependency_graph(chunks: list[Chunk]) -> dict:
    """返回 ``{symbol: {"callees": [...], "callers": [...]}}``（project 内解析）。"""
    graph: dict[str, dict] = {}
    for chunk in chunks:
        symbol = chunk.meta.get("symbol")
        if not symbol:
            continue
        graph.setdefault(symbol, {"callees": [], "callers": [], "kind": chunk.meta.get("kind"),
                                  "file": chunk.meta.get("file"), "project_id": chunk.meta.get("project_id")})
        graph[symbol]["callees"] = sorted(set(chunk.meta.get("deps", [])))

    for symbol, info in graph.items():
        for callee in info["callees"]:
            if callee in graph:
                graph[callee]["callers"].append(symbol)
    for info in graph.values():
        info["callers"] = sorted(set(info["callers"]))
        info["callees"] = sorted(set(info["callees"]))
    return graph


def callers_of(graph: dict, symbol: str) -> list[str]:
    return list(graph.get(symbol, {}).get("callers", []))


def callees_of(graph: dict, symbol: str) -> list[str]:
    return list(graph.get(symbol, {}).get("callees", []))
