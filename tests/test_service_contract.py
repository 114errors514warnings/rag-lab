"""E12 · L1：知识服务契约（离线；FastAPI TestClient）。

覆盖：/health、/search（schema + project 隔离）、/read_context（预算 + 来源）、/symbol（命中 + 跨项目隔离 + 404）。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from service.api import app

    with TestClient(app) as c:  # 触发 startup：构建默认离线索引
        yield c


def test_health(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["chunks"] > 0


def test_search_schema_and_project_isolation(client) -> None:
    r = client.get("/search", params={"query": "登录 校验 口令", "project_id": "proj-auth", "k": 5})
    assert r.status_code == 200
    for item in r.json()["results"]:
        assert {"chunk_id", "source", "score", "snippet", "project_id"} <= set(item)
        assert item["project_id"] == "proj-auth"  # 隔离


def test_read_context_budget_and_citations(client) -> None:
    r = client.post("/read_context",
                    json={"query": "切块 overlap", "token_budget": 120, "project_id": "proj-auth"})
    assert r.status_code == 200
    body = r.json()
    assert body["tokens"] <= 120 + 80  # 允许最后一截断块略超
    assert body["citations"] == [s["chunk_id"] for s in body["segments"]]  # 来源可追溯
    assert all("chunk_id" in s and "source" in s for s in body["segments"])


def test_symbol_found_and_project_isolated(client) -> None:
    ok = client.get("/symbol", params={"name": "validate_page", "project_id": "proj-alpha"})
    assert ok.status_code == 200 and ok.json()["project_id"] == "proj-alpha"
    iso = client.get("/symbol", params={"name": "validate_page", "project_id": "proj-beta"})
    assert iso.status_code == 404  # 跨项目不可见


def test_symbol_missing_is_404(client) -> None:
    assert client.get("/symbol", params={"name": "no_such_symbol_xyz"}).status_code == 404
