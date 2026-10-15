# E12 架构说明 · 服务化与 Tool 接口

> 报告：[`stage-E12-report.md`](stage-E12-report.md)　· 测试方案：[`test-plan.md`](test-plan.md)

## 1. 服务端（`service/api.py`，复用 S7）
```
GET  /health         → {status, chunks}
GET  /search         → search_project(query,k,project_id)  # 返回 chunk_id/source/score/snippet/project_id/start_line/end_line/symbol
POST /read_context   → read_context(query, token_budget, project_id)  # ContextBuilder 预算 + 引用
GET  /symbol         → get_symbol(name, project_id)         # 命中/跨项目 404/缺失 404
```
服务端引擎配置经环境变量（`RAG_*`）注入，便于与 E 线跑**同一配置**；`SILICONFLOW_API_KEY` 仅环境变量。

## 2. 客户端适配（`rag_engine/eval_http.py::HttpPipeline`）
- 继承 `MyPipeline`，但**不建本地索引**；`answer()` 经 `GET /search` 取回结果。
- 把返回的 `start_line/end_line/symbol` 映射进 `RetrievedChunk`（供 E 线证据映射）。
- 按 `min_relevance` 在客户端复现**拒答**行为，与进程内一致。
- `base_url` 取 `RAG_SERVICE_URL`（默认 `http://127.0.0.1:8099`）。

## 3. 契约与注意
- `sut: http`（实验配置）→ 运行器选 `HttpPipeline`；`sut: inproc`（默认）→ `MyPipeline`。
- `/search` 的响应**新增** `start_line/end_line/symbol`（additive；否则 E 线无法映射证据）。
- 隔离沿用 `project_id`：`/search` 与 `/symbol` 都按项目过滤。

## 4. 边界
- 无 Docker 守护时不跑容器，仅本地 uvicorn 冒烟。
- `/symbol` 与主库语料不同源（`data/code_corpus` vs `data/kb`）——待统一。
