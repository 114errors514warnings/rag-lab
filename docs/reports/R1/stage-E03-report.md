# rag-lab · E03 阶段报告 · 符号级切块（**未通过**）

**结论：E03 测试未通过——`recall@5` 由 0.8519 回退到 0.5926（`mrr@5` 0.7914→0.6698）；已按准则停下汇报。**

- 阶段：R1 · E03　·　日期：2026-10-11
- 架构说明：[`stage-E03-architecture.md`](stage-E03-architecture.md)
- 配置：`configs/E03.yaml`（`chunking: symbol`）　基线：`E02`（定长 512/80，`recall@5=0.8519`）

> 本阶段**未达标**，依《统一开发准则》第 7 条"测试未通过先停下汇报"记录在案；代码/测试/配置已提交，
> 后续按"模块剩余块"方案修复后复测。

## 1. 目标与实施
以 AST 的**函数/类/方法**为单位切块（`meta.symbol/kind/file/span`），非代码退回定长；
对照 E02 定长，期望"代码子集召回提升、整体不回退"。

交付物：
| 文件 | 职责 |
|---|---|
| `rag_engine/config.py` | 新增 `chunking`（`fixed`\|`symbol`）语义参数 |
| `rag_lab/config.py` | `ENGINE_FIELDS` 纳入 `chunking` |
| `rag_engine/ingest/symbol_chunker.py` | `chunk_document_symbols` / `chunk_documents_symbol` |
| `rag_engine/pipeline.py` | `build` 按 `chunking` 选切块；符号块跳过定长元数据 enrichment |
| `tests/test_symbol_chunking.py` | L1：符号提取、span/source、id 连续稳定、非代码/语法错误回退 |
| `configs/E03.yaml` | L2：`chunking: symbol` + 门禁 |

## 2. 测试方法
- L1：`python -m pytest -q` → **92 passed**。
- L2：`python scripts/run_eval.py --config configs/E03.yaml --baseline <E02 run_id>`；
  门禁：`recall@5 max_delta -0.01`、`mrr@5 max_delta -0.01`、`p95_latency_ms max 500`。

## 3. 结果（未通过）

| 门禁 | 基线(E02) | 本次(E03) | Δ | 判定 |
|---|---|---|---|---|
| `recall@5`（主） | 0.8519 | 0.5926 | **−0.2593** | **FAIL** |
| `mrr@5`（护栏） | 0.7914 | 0.6698 | −0.1216 | **FAIL** |
| `p95_latency_ms` | 0.318 | 0.294 | — | PASS |

退出码 1。

## 4. 根因（实测证据）
符号块只覆盖函数/类/方法体，**丢失模块级区域**（imports / module docstring / 常量 / 顶层语句）：

| 文件 | 总行 | 定长块 | 符号块 | 未覆盖行 |
|---|---|---|---|---|
| proj-auth/auth.py | 63 | 5 | 6 | **33** |
| proj-auth/errors.py | 19 | 1 | 3 | 9 |
| proj-auth/models.py | 43 | 2 | 8 | 15 |
| proj-sched/errors.py | 17 | 1 | 3 | 10 |
| proj-sched/queue.py | 35 | 2 | 6 | 13 |
| proj-sched/scheduler.py | 52 | 5 | 7 | 13 |

落在这些行的 `gold_evidence` 无法被检索到 ⇒ 覆盖式 `recall@5` 大幅下滑。

## 5. 待办修法（下次实现）
**为代码文件补"模块剩余块"**：把"不属于任何符号、且连续"的区段各发一块（`meta.kind="module"`，`chunk_id={doc_id}:M{seq:03d}`）。
预期恢复覆盖（`recall@5` 回到定长水平）并保留符号结构化。备选：定长 ∪ 符号 并集。

## 6. 契约影响（留痕）
本次给 `EngineConfig` 新增 `chunking` 语义参数 ⇒ **所有配置的 `config_hash` 变化**（含 E00/E01/E02）。
历史报告的 `config_hash` 由旧口径产生，**不可与新值直接比较**（沿用 `docs/reports/R0/round-0.md` 的便携口径说明；
如需可再向 E01/E02 报告追加"后续变更"）。指标口径未变（`EVAL_VERSION` 仍为 `v2`）。

## 7. 边界
- 符号切块仅作用于 `.py`；Markdown/纯文本仍定长。
- 本阶段不达标，**不进入下一阶段**，等修复方案确认。
