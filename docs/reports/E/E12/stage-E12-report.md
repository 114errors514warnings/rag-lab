# E12 阶段报告 · 服务化与 Tool 接口（HTTP 端到端）

- 实验：E12（E 计划，R3；**E 线收官**）
- 状态：✅ **通过**（经 HTTP 与进程内质量一致、`leakage_rate=0`、服务端契约全绿）
- 日期：2026-10-15
- 配置：`configs/E12_inproc.yaml`（进程内，对照）· `configs/E12_http.yaml`（经 HTTP）
- 实现：复用 S7 的 `service/api.py` + `rag_engine/eval_http.py::HttpPipeline`（未新造服务）
- run_id：inproc `…162704…` · http `…162924…`
- 记录：[`test-plan.md`](test-plan.md)（测试方案）· [`stage-E12-architecture.md`](stage-E12-architecture.md)

## 1. 目标与主变量
**主变量**：接入方式（进程内调用 → 经**真实 HTTP** 调用服务）。验证"外部客户端能通过标准接口检索项目知识，且质量不降、隔离不破"。

## 2. 测试方法（三层，详见 test-plan）
- **L1 服务端契约**：`tests/test_service_contract.py`（`/health`、`/search` schema+隔离、`/read_context` 预算+来源、`/symbol` 命中+跨项目 404+缺失 404）。全仓 `pytest` → **116 passed**。
- **L2 E 线门禁**：`run_eval --config configs/E12_{inproc,http}.yaml`；门禁 `leakage_rate max 0`。
- **L3 部署冒烟**：启动 uvicorn（`RAG_*` env）→ `/health` 200 → `E12_http` 端到端。

## 3. 结果

| 系统 | `recall@5` | `mrr@5` | `answer_accuracy` | `no_answer` | `leakage_rate` | `p95(ms)` | 判定 |
|---|---|---|---|---|---|---|---|
| E12_inproc（进程内，对照） | 0.963 | 0.8562 | 0.8857 | 1.0 | **0.0** | 1504.7 | PASS |
| E12_http（经真实 HTTP） | 0.963 | 0.8562 | 0.8857 | 1.0 | **0.0** | 1235.5 | PASS |

服务端契约：`/health` → `{"status":"ok","chunks":81}`；`/search`/`/read_context`/`/symbol` 均按预期（含跨项目 404）。

## 4. 结论
- **HTTP 与进程内质量完全一致**（`recall/mrr/answer_accuracy/no_answer` 相同，`leakage_rate` 均为 0）⇒ 服务化**未引入质量退化**。
- 外部客户端可经**标准 HTTP 接口**检索并组装上下文；**多项目隔离经 HTTP 仍然成立**。
- 端到端可复现（L3 命令文档化）。

## 5. 边界与不做
- 本机**无 Docker 守护**，`docker compose up` 未实际执行（`Dockerfile`/`compose.yaml` 已就绪，命令见 test-plan）。
- **两套代码语料并存**：`/symbol` 走 `data/code_corpus`（proj-alpha/beta），主库为 `data/kb`（proj-auth/sched）——既有不一致，记 TODO。
- MCP 为极简 JSON-Lines stdio（S7），本次经 HTTP 验证；接 Cline/Codex 时可替换为官方 MCP SDK，工具签名不变。
- 无基线（选项 B）：以 `leakage_rate` 绝对门禁 + inproc 对照判定。
