# E12 测试方案 · 知识服务与 Tool 接口

> 目的：验证"可运行的 Indexing/Retrieval/Answering 服务"能被**外部客户端经标准接口**调用，
> 且质量相对进程内不降、多项目隔离不破。分三层：L1 服务端契约 / L2 E 线门禁 / L3 部署冒烟。

## 0. 被测对象
- `service/api.py`（FastAPI）：`GET /health`、`GET /search`、`POST /read_context`、`GET /symbol`。
- `rag_engine/eval_http.py::HttpPipeline`：经真实 HTTP 调服务的被测系统（`Sut`）。
- 服务端引擎配置经**环境变量**注入（`RAG_*`），用于让服务与 E 线跑**同一配置**。

## 1. 环境变量（服务端）
| 变量 | 含义 |
|---|---|
| `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` / `RAG_CHUNKING` | 切块 |
| `RAG_EMBED_PROVIDER` / `RAG_EMBED_MODEL` / `RAG_EMBED_DIM` | Embedding |
| `RAG_RETRIEVAL` / `RAG_RERANK` / `RAG_RERANK_MODEL` / `RAG_RERANK_CANDIDATES` | 检索/重排 |
| `RAG_MIN_RELEVANCE` / `RAG_ISOLATION` | 拒答阈值 / 多项目隔离 |
| `SILICONFLOW_API_KEY` | 密钥（**不入库**） |

## 2. L1 · 服务端契约（离线，`pytest`）
文件：`tests/test_service_contract.py`（FastAPI `TestClient`，默认离线配置）。

| 用例 | 断言 |
|---|---|
| `/health` | 200；`status=="ok"`；`chunks>0` |
| `/search` schema + 隔离 | 字段齐全（`chunk_id/source/score/snippet/project_id/start_line/end_line/symbol`）；返回项 `project_id` 全等于请求项目 |
| `/read_context` 预算 + 来源 | `tokens <= budget + 容差`；`citations == [segment.chunk_id]`；每段含来源 |
| `/symbol` 命中 + 隔离 | 正确项目查 → 200 且 `project_id` 匹配；错误项目查 → **404** |
| `/symbol` 缺失 | 不存在的符号 → **404** |

## 3. L2 · E 线门禁（经 HTTP vs 进程内）
先启动服务（§1 env），再：
```powershell
python scripts/run_eval.py --config configs/E12_inproc.yaml                # 进程内（对照）
python scripts/run_eval.py --config configs/E12_http.yaml --baseline <E12_inproc run>
```
| 门禁 | 规则 |
|---|---|
| `leakage_rate` | `max 0`（经 HTTP 也必须零泄漏） |
| `answer_accuracy` | `max_delta -0.02`（HTTP 相对进程内不降超过 0.02） |
| `p95_latency_ms` | 观察项（HTTP 有网络开销） |

判据：**两系统质量差 ≤0.02 且 `leakage_rate=0` → 通过**。

## 4. L3 · 部署冒烟（可复现）
```powershell
# 启动服务（示例 env 见 §1）
python -m uvicorn service.api:app --host 127.0.0.1 --port 8099
curl http://127.0.0.1:8099/health     # 期望 {"status":"ok","chunks":N}
python scripts/run_eval.py --config configs/E12_http.yaml
# 可选：docker compose up（需本机 Docker 守护）
```
判据：`/health` 200；`E12_http` 端到端无 error；以上命令文档化可复现。

## 5. 安全回归（沿用 E11）
- 跨项目题经 HTTP 仍 `leakage_rate=0`；
- 注入文本（`QD05`）经 HTTP 仍当普通查询处理，不执行指令。

## 6. 通过标准与产物
- **退出码 0**；报告 `reports/{run_id}/{metrics.json,cases.jsonl,errors.csv,comparison.md}`；
- 记录 `docs/reports/E/E12/{stage-E12-report.md,stage-E12-architecture.md,test-plan.md}`。

## 7. 已知边界
- `/symbol` 走 `data/code_corpus`（proj-alpha/beta），主库是 `data/kb`（proj-auth/sched）——**两套代码语料**尚未统一（既有不一致，记 TODO）。
- 本机无 Docker 守护时，`docker compose up` 跳过，仅做本地 uvicorn 冒烟。
