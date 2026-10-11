"""请求处理与路由（proj-beta）。"""

from __future__ import annotations


def parse_query(query: str) -> dict:
    """把 k=v&k2=v2 解析成字典。"""
    out: dict[str, str] = {}
    for part in query.split("&"):
        if "=" in part:
            key, value = part.split("=", 1)
            out[key] = value
    return out


def handle_request(path: str, query: str) -> dict:
    """处理一次请求：解析查询串并返回结果信封。"""
    params = parse_query(query)
    return {"path": path, "params": params, "ok": True}


class Router:
    def __init__(self) -> None:
        self.routes: dict[str, str] = {}

    def register(self, path: str, handler: str) -> None:
        self.routes[path] = handler

    def dispatch(self, path: str) -> str:
        """按路径查找处理函数。"""
        return self.routes.get(path, "")
