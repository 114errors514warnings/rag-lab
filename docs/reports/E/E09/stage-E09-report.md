# E09 阶段报告 · Context Budget（去重 + 预算裁剪）

- 实验：E09（E 计划）
- 状态：✅ **门禁通过**（`avg_prompt_tokens` / `p95` 达标）；`context_evidence_coverage` 随预算收紧而下降（观察项 / 权衡）
- 日期：2026-10-15
- 配置：`configs/E09_budget{200,400}.yaml`（基座同 E08；`context: builder`）
- 实现：**复用 S4 的 `rag_engine/context/builder.py::ContextBuilder`**（去重 → 相关性 → 每文档≥1 → 预算填充 → 超预算截断 → stale/trust 标注）
- 判定方式：**无基线（选项 B）**，按绝对门禁；`context_evidence_coverage` 以 E08 的 1.0 作参考
- run_id：`…145225_E09_budget200…`、`…145310_E09_budget400…`
- 架构说明：[`stage-E09-architecture.md`](stage-E09-architecture.md)

## 1. 目标与主变量
**主变量**：上下文 Token 预算（`context_budget_tokens`）。在 E08"大上下文"的基础上做去重 + 预算裁剪，
比较**上下文长度 / 成本 / 覆盖**三者的取舍。

## 2. 测试方法
- **L1**：`python -m pytest -q` → **108 passed**（S4 的 `tests/test_context_budget.py` 覆盖 builder 去重/预算/来源保留）。
- **L2**：`python scripts/run_eval.py --config configs/E09_budget{200,400}.yaml`（无 `--baseline`）
  - 门禁（绝对）：`avg_prompt_tokens max 2000`、`p95_latency_ms max 4000`。

## 3. 结果（权衡曲线）

| 预算 | `context_evidence_coverage` | `avg_prompt_tokens` | `mrr@5` | `citation_support` | `p95(ms)` |
|---|---|---|---|---|---|
| 无（E08 top_n，参考） | **1.0000** | 621.75 | 0.8728 | 0.2121 | 2872.7 |
| 400 | 0.9259 | 412.5 | 0.8562 | 0.2315 | 1431.9 |
| 200 | 0.8889 | 211.2 | 0.8747 | 0.3374 | 1346.4 |

`recall@5`=0.963、`no_answer_accuracy`=1.0、`answer_accuracy`=0.875 三档不变。**两档门禁均 PASS（退出码 0）。**

## 4. 结论
- 预算裁剪**按预期降低上下文成本**：`avg_prompt_tokens` 621.75 → 412.5 → 211.2（约 −34% / −66%）。
- 代价是**覆盖下降**：`context_evidence_coverage` 1.0 → 0.9259 → 0.8889（多证据题又被挤出）。
- **`retrieved`/`recall@5` 不受影响**（预算只作用于上下文）。
- 结论：存在清晰的 **"token ≈ 覆盖"** 权衡；`E08`（不裁剪）与 `E09`（裁剪）分别代表曲线两端，可按预算选点。

## 5. 边界与不做
- **无基线（选项 B）**：与旧 run 不配对；结论以上表数值说明。
- **未实现语义压缩（摘要式）**：当前 Builder 是"去重 + 截断"，非模型摘要；故覆盖随预算掉。
- 复用既有 S4 实现（未新造），并把 E 线 `context: builder` 接入其中。
- 仅用多语言免费模型；密钥不入库。

## 6. 演进映射
- E10（增量索引）、E11（隔离/安全）、E12（Tool 接口）继续。
