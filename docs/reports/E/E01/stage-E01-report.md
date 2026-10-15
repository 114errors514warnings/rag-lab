# rag-lab · E01 阶段报告 · 解析器契约基线

**结论：E01 测试通过（L1 82 passed；L2 三项门禁全 PASS，exit 0）。**

- 阶段：R1 · E01（解析 / 切块 / 召回）
- 日期：2026-10-11
- 架构说明：[`stage-E01-architecture.md`](stage-E01-architecture.md)
- 配置：`configs/E01.yaml`　基线：`E00`（`483d64cf78e9`，`recall@5=0.8148`）

## 1. 目标
把 E00 里**隐式的解析**变成**有显式断言与回归门禁**的基线：确认 `.md/.txt/.py` 解析正确、
`doc_id` 与来源稳定、`load_tree` 多项目隔离正确，并且解析口径**不使召回回退**。

## 2. 交付物
| 文件 | 职责 |
|---|---|
| `tests/test_parser_contract.py` | L1：`doc_id` 稳定且由来源派生；不同文件不同 id；`load_tree` 项目隔离；`.py` 完整解析；`.md` 支持 |
| `configs/E01.yaml` | L2：与 E00 同系统参数 + 回归门禁 |
| 本报告 + `stage-E01-architecture.md` | 阶段两份文档 |

## 3. 测试方法
- **L1**：`python -m pytest -q` → **82 passed**（新增 5 项）。
- **L2**：`python scripts/run_eval.py --config configs/E01.yaml --baseline <E00 run_id>`
  - 门禁：`recall@5 max_delta -0.01`、`context_evidence_coverage max_delta -0.01`、`p95_latency_ms max 500`。

## 4. 结果（逐指标：含义 / 标准 / 实测 / 结论）

| 指标 | 它衡量什么 | 标准 | 基线（E00） | 本次（E01） | 结论 |
|---|---|---|---|---|---|
| `recall@5` | 覆盖式召回：**至少一组充分证据**落入检索 top-5 的题数 ÷ 可答题数 | 不得回退超过 0.01 | 0.8148 | 0.8148 | ✅ 通过 |
| `context_evidence_coverage` | 送进生成的**上下文**覆盖全部必要证据的题数 ÷ 可答题数 | 不得回退超过 0.01 | 0.8148 | 0.8148 | ✅ 通过 |
| `p95_latency_ms` | 端到端第 95 百分位耗时 | ≤ 500 ms | — | 0.25 ms | ✅ 通过 |

退出码 0，**通过**（首跑把 E 线不产出的 `error_rate`/`trace_completeness` 误当门禁 → `NO_GATE`；改用 E 线实际指标后复跑全通过）。

## 5. 边界与不做
- 本阶段**不改系统行为**（与 E00 同参数），只建立解析口径的显式锚点；因此 `config_hash` 与 E00 相同（`483d64cf78e9`）。
- PDF 未实测（环境缺 PyMuPDF/pypdf）。

## 6. 演进映射
- E02 在此基线上改**切块参数**（size/overlap）；E03 增**符号级切块**。
