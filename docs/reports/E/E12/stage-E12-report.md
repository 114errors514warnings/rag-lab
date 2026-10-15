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

### 3.1 L2 · E 线指标（逐个列出；"标准"= 通过条件）

| 指标 | 它衡量什么 | 标准 | 进程内 | 经 HTTP | 结论 |
|---|---|---|---|---|---|
| `leakage_rate` | 检索结果里**不属于该用例项目**的块所占比例 | **必须 = 0** | 0 | 0 | 通过 |
| `recall@5` | 覆盖式召回：**至少一组充分证据**出现在检索 top-5 的题数 / 可答题数 | 经 HTTP 与进程内**一致** | 0.963（27 题中 26 题） | 0.963（26/27） | 一致 |
| `mrr@5` | 第一个命中证据的平均倒数排名（1/名次） | 不下降 | 0.8562 | 0.8562 | 一致 |
| `answer_accuracy` | rubric 代理：**召回覆盖 且 有引用** 的题数 / 全部题数 | 相对进程内降幅 ≤ 0.02 | 0.8857（35 题中 31 题） | 0.8857（31/35） | 一致（Δ=0） |
| `no_answer_accuracy` | **无答案题正确拒答**的题数 / 无答案题数 | 不下降 | 1.0（5 题全对） | 1.0（5/5） | 一致 |
| `p95_latency_ms` | 端到端第 95 百分位耗时（含网络） | 观察项（未设门禁） | 1504.7 ms | 1235.5 ms | — |

> **标准来源**：`configs/E12_http.yaml` 的 `gates`（`leakage_rate max 0`）+ 与 `configs/E12_inproc.yaml` 对照；运行器**退出码 0 = 通过**。

### 3.2 L1 · 服务端契约（5 项，离线）

| 用例 | 测什么 | 期望 | 实测 | 结论 |
|---|---|---|---|---|
| `GET /health` | 服务存活 + 索引规模 | 200 且 `chunks>0` | 200，`chunks = 81` | 通过 |
| `GET /search` | 返回字段完整 + **项目隔离** | 含 `chunk_id/source/score/snippet/project_id/start_line/end_line/symbol`；`project_id` 全等于请求项目 | 字段齐全；全为 `proj-auth` | 通过 |
| `POST /read_context` | **Token 预算** + 来源可追溯 | `tokens ≤ 预算(+容差)`；`citations` 与 `segments` 一一对应 | 通过 | 通过 |
| `GET /symbol` | 符号定位 + **跨项目隔离** | 正确项目 → 200；错误项目 → 404 | `validate_page@proj-alpha` → 200；`@proj-beta` → 404 | 通过 |
| `GET /symbol` | 未知符号 | 404 | 404 | 通过 |

### 3.3 L3 · 部署冒烟
启动 `uvicorn`（`RAG_*` env）→ `/health` 返回 `{"status":"ok","chunks":81}`；经 HTTP 跑 `E12_http` 端到端无 error → 通过。

## 4. 结论
- **HTTP 与进程内质量完全一致**（`recall/mrr/answer_accuracy/no_answer` 相同，`leakage_rate` 均为 0）⇒ 服务化**未引入质量退化**。
- 外部客户端可经**标准 HTTP 接口**检索并组装上下文；**多项目隔离经 HTTP 仍然成立**。
- 端到端可复现（L3 命令文档化）。

## 5. 边界与不做
- 本机**无 Docker 守护**，`docker compose up` 未实际执行（`Dockerfile`/`compose.yaml` 已就绪，命令见 test-plan）。
- **两套代码语料并存**：`/symbol` 走 `data/code_corpus`（proj-alpha/beta），主库为 `data/kb`（proj-auth/sched）——既有不一致，记 TODO。
- MCP 为极简 JSON-Lines stdio（S7），本次经 HTTP 验证；接 Cline/Codex 时可替换为官方 MCP SDK，工具签名不变。
- 无基线（选项 B）：以 `leakage_rate` 绝对门禁 + inproc 对照判定。
