# rag-lab · S7 架构说明 · 工程集成与服务化

> 报告：[`stage-S7-report.md`](stage-S7-report.md)

## 1. 组件与职责
| 组件 | 职责 | 文件 |
|---|---|---|
| HTTP 服务 | `/health` `/search` `/read_context` `/symbol` | `service/api.py` |
| MCP 工具 | `search_project` / `get_symbol` / `read_context`（签名冻结） | `service/mcp_server.py` |
| HTTP 适配器 | 评测框架经真实 HTTP 调服务 | `rag_engine/eval_http.py` |
| 容器 | app + gates | `Dockerfile`、`compose.yaml` |

## 2. 服务数据流
```
客户端 ──HTTP──▶ /search ──▶ pipeline.retriever(dense, flt=project_id)
             └─▶ /read_context ──▶ ContextBuilder(token_budget).build(hits)
             └─▶ /symbol ──▶ code_rag.build_dependency_graph
```

## 3. MCP 工具签名（冻结）
```
search_project(project_id, query, k=5, filters?) -> [{chunk_id, source, score, snippet}]
get_symbol(project_id, symbol, kind?)            -> {def, file, span, callers[], callees[]}
read_context(project_id, query, token_budget)    -> {segments:[{chunk_id,source,text}], citations[]}
```

## 4. 部署
```
docker compose up --build     # app → http://127.0.0.1:8099/health
docker compose run --rm gates # pytest（L1）
```

## 5. 可复现性
- `HttpPipeline` 走真实 HTTP（非 in-process），使 L3 冒烟成立；`success_rate` 与本地一致。
- `data/index` 由 manifest + config 指纹决定是否重建；容器内挂载 `data/` 持久化。

## 6. 边界
- MCP stdio 为极简实现；生产接入用官方 SDK（工具函数不变）。
- 未做鉴权/多租户（本地服务，回环监听）。
