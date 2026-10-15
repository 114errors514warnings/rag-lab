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
历史报告的 `config_hash` 由旧口径产生，**不可与新值直接比较**（沿用 `docs/reports/S/R0/round-0.md` 的便携口径说明；
如需可再向 E01/E02 报告追加"后续变更"）。指标口径未变（`EVAL_VERSION` 仍为 `v2`）。

## 7. 边界
- 符号切块仅作用于 `.py`；Markdown/纯文本仍定长。
- 本阶段不达标，**不进入下一阶段**，等修复方案确认。

---

## 8. 后续变更（2026-10-14）

> 按《实践项目合集·统一开发准则》第 2 条：历史报告**只追加、不改写**。以上正文保持原样。

**触发原因**：执行 §5 待办修法——为代码文件补"模块剩余块"。

**改动**：
- `rag_engine/ingest/symbol_chunker.py`：抽出 `_node_span`（含装饰器行）；新增 `_module_spans`，
  把"不属于任何符号、且连续"的行区段补为 `kind="module"` 块；符号块 + 模块块按起始行排序后统一编号，
  `chunk_id` 仍为 `{doc_id}:{seq:04d}` 连续稳定。
- `rag_engine/pipeline.py`：元数据 enrichment 改为跳过**自带 `kind`** 的块（原仅跳过 `symbol` 块）。
- `tests/test_symbol_chunking.py`：新增 2 项 L1 —— module 块覆盖模块级区域、**每个非空源行都被覆盖**。

**复测**（`--config configs/E03.yaml --baseline <E02 run>`，套件 32 题，k=5）：

| 门禁 | 基线(E02,512/80) | 本次(E03,symbol+module) | Δ | 判定 |
|---|---|---|---|---|
| `recall@5`（主） | 0.8519 | 0.8148 | −0.0371 | **FAIL** |
| `mrr@5`（护栏） | 0.7914 | 0.7698 | −0.0216 | **FAIL** |
| `p95_latency_ms` | — | 0.443 | — | PASS |

L1：`python -m pytest -q` → **94 passed**。较修复前 `recall@5 0.5926→0.8148`（已回到 E00 定长水平）。

**归因（逐题比对）**：整体覆盖 23/27(E02) vs 22/27(E03)，仅差 **1 题**。
- E02 覆盖而 E03 未覆盖：`QA13`（模块级常量 `_PBKDF2_ROUNDS`）、`QA18`（依赖题，需同时命中 `verify_login` + `verify_password` + `errors.py` 常量段）。
- E03 覆盖而 E02 未覆盖：`QB06`。
- 原因：**覆盖式 `recall@5` 对多证据题偏好更粗的块**；符号块把相邻函数拆开，top-5 难以同时集齐 `QA18` 的三段证据。

**结论**：模块剩余块修复了"覆盖缺口"，但符号切块粒度更细，在本套件上与定长 512 的覆盖式召回仍差 1 题，**门禁未通过**。

**待决策方案**（按纪律停下汇报）：
- (A) **符号 ∪ 定长并集**：在符号块基础上并回定长块（新 `chunking` 取值，保留符号结构）；
- (B) **符号块按 size 预算合并相邻块**（含模块块）：得到"符号对齐但更粗"的块；
- (C) 保持**未达标**记录，先推进 E04/E05，E03 待有更合适判定口径时复核。

---

## 9. 后续变更（2026-10-14 · 尝试 3：符号 ∪ 非冗余定长）

> 按《实践项目合集·统一开发准则》第 2 条：历史报告**只追加、不改写**。以上正文保持原样。

**触发原因**：执行 §8 待决策方案 (A)。

**改动**：
- `rag_engine/ingest/symbol_chunker.py`：新增 `chunk_documents_symbol_union`——符号（含模块）块 ∪ 非冗余定长块；
  定长块 id 加 `F` 前缀（`{doc_id}:F{seq:04d}`）避免与符号块冲突；被**任一**符号/模块块完整包含的定长块视为冗余丢弃。
- `rag_engine/pipeline.py`：新增 `chunking = symbol_union` 分支。
- `configs/E03_union.yaml`：尝试 3 配置（其余同 E02）。
- `tests/test_symbol_chunking.py`：新增 2 项 L1（并集 id 唯一且保留定长块；完全包含时丢弃冗余定长块）。

**复测**（`--config configs/E03_union.yaml --baseline <E02 run>`）：

| 门禁 | 基线(E02) | 本次(E03_union) | Δ | 判定 |
|---|---|---|---|---|
| `recall@5`（主） | 0.8519 | 0.7037 | **−0.1481** | **FAIL** |
| `mrr@5`（护栏） | 0.7914 | 0.7870 | −0.0044 | PASS |
| `p95_latency_ms` | — | 0.395 | — | PASS |

L1：`python -m pytest -q` → **96 passed**。

**归因**：并入较多粗粒度定长块后，候选竞争加剧，部分题的正确符号/模块块被挤出 top-5，
覆盖式 `recall@5` 反降；`mrr` 反而小幅回升（定长块把部分证据排到更前）。

**结论（3 次尝试后）**：`symbol`（0.5926）→ `symbol+module`（0.8148）→ `symbol_union`（0.7037），
**均未超过 E02 定长 512 的 0.8519**。按协议"3 次未通过则记录原因并进入下一阶段"，
E03 记为**未达标**；`symbol` 与 `symbol_union` 作为可选 `chunking` 模式保留（结构化价值），
R1 按计划推进 **E05**（BM25/Hybrid + 拒答）。


