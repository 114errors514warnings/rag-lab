# rag-lab · S7 阶段报告 · 工程集成与服务化

- 阶段：S7｜轮次：R3
- 状态：✅ 完成（L1 + L2/L3 通过，1 次通过）
- 日期：2026-10-11
- 架构说明：[`stage-S7-architecture.md`](stage-S7-architecture.md)

## 1. 目标
FastAPI 封装、多项目知识库管理、持久化、Docker、MCP（`search_project`/`get_symbol`/`read_context`）、
经真实客户端调用验证可复现。

## 2. 交付物
| 文件 | 职责 |
|---|---|
| `service/api.py` | FastAPI：`/health`、`/search`、`/read_context`、`/symbol` |
| `service/mcp_server.py` | MCP 三工具（签名冻结）+ 极简 JSON-Lines stdio |
| `rag_engine/eval_http.py` | `HttpPipeline`：经真实 HTTP 调服务的被测系统 |
| `Dockerfile` / `compose.yaml` | 容器化 + 一键运行/评测 |
| `requirements.txt` | 增 `fastapi`、`uvicorn`、`httpx` |

## 3. 测试方法
- L1：`python -m pytest -q` → **72 passed**。
- L2/L3：启动服务后 `python -m rag_eval.runner --stage S7 --system http_pipeline --baseline S1__my_pipeline`
  （smoke_v1，k=3，经真实 HTTP）。

## 4. 结果
| 门禁 | 基线 | 本次 | Δ | 判定 |
|---|---|---|---|---|
| `success_rate`（主） | 1.0 | 1.0 | +0.0000 | **PASS** |

退出码 0。**1 次通过**。
服务 `GET /health` → `{"status":"ok","chunks":111}`；`http_pipeline` 经 `http://127.0.0.1:8099/search` 取回结果并全部成功。

## 5. 边界与不做
- MCP 用极简 JSON-Lines stdio 暴露三工具（工具函数与冻结签名一致）；接入 Cline/Codex 时替换为官方 MCP SDK，工具不变。
- 未在本机执行 `docker compose`（无 Docker 守护）；`Dockerfile`/`compose.yaml` 已就绪，命令已文档化。

## 6. 里程碑映射
- M3 = S5 + S6 + S7：`code_v1` + 回归 + 服务化 → 均已落地。
