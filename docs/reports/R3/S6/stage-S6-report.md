# rag-lab · S6 阶段报告 · Evaluation 与自动化回归

- 阶段：S6｜轮次：R3
- 状态：✅ 完成（L1 + L2 通过，1 次通过）
- 日期：2026-10-11
- 架构说明：[`stage-S6-architecture.md`](stage-S6-architecture.md)

## 1. 目标
配置改动后自动产出质量/延迟/成本对比报告；CI 红绿分明（回归门禁）。

## 2. 交付物
| 文件 | 职责 |
|---|---|
| `scripts/run_gates.ps1` | 一条命令跑 L1（pytest）+ L2（S6 回归），聚合退出码 |
| `rag_eval/gates.json`（S5 补齐） | S5 套件由 `[]` → `["code_v1"]`（套件已建，属计划内的补齐而非放宽） |
| 既有 `rag_eval/runner.py` | 报告同时落 `.json` + `.md`；退出码 = 是否有 FAIL |

## 3. 测试方法
- L1：`python -m pytest -q` → **72 passed**。
- L2：`python -m rag_eval.runner --stage S6 --system my_pipeline --baseline S1__my_pipeline`
  - 套件 `smoke_v1` + `retrieval_v1`，k=3；主指标空；护栏 `recall@3 max_delta -0.01`、`error_rate = 0`。

## 4. 结果
| 套件 | 门禁 | 基线 | 本次 | Δ | 判定 |
|---|---|---|---|---|---|
| smoke_v1 | `recall@3` | 0.0 | 0.0 | +0.0000 | PASS |
| smoke_v1 | `error_rate` | 0.0 | 0.0 | +0.0000 | PASS |
| retrieval_v1 | `recall@3` | — | 0.0 | — | BASELINE（该套件未冻结基线） |
| retrieval_v1 | `error_rate` | — | 0.0 | — | PASS |

退出码 0（无 FAIL）。**1 次通过**。

## 5. 边界与不做
- `retrieval_v1` 对 `my_pipeline`（项目 kb 语料）不对齐，其 `recall@3` 恒为 0；本阶段只作回归护栏，不做效果判定。
- 忠实度/答案正确性需 LLM 裁判，**只作观察项**，未纳入门禁（协议既定）。

## 6. 演进映射
- 服务化（S7）：`service/api.py`、`service/mcp_server.py`、`Dockerfile`、`compose.yaml`。
