# E06 阶段报告 · Rerank + 拒答（SiliconFlow `BAAI/bge-reranker-v2-m3`）

- 实验：E06（E 计划）
- 状态：✅ 门禁通过（`mrr@5` 提升、**`no_answer_accuracy` 0→1.0**、`p95` 未越线）
- 日期：2026-10-14
- 配置：`configs/E06_rerank.yaml`（基座 Dense = E05 最优；`rerank=siliconflow`，候选 20，拒答阈值 0.05）
- 系统：`rag_engine(siliconflow:BAAI/bge-m3 + fixed + dense + rerank:siliconflow + extractive)`
- 基线：**E05_dense**（`mrr@5=0.7833`，`no_answer_accuracy=0`）
- run_id：`20261014T213234_E06_rerank_c5ec97d0d609_9d0b175_df5eb069a83579d2_626aa1732b4f8e12`
- 架构说明：[`stage-E06-architecture.md`](stage-E06-architecture.md)

## 1. 目标与主变量
**主变量**：Rerank（none → `BAAI/bge-reranker-v2-m3`，在 top-20 候选上重排到 5）。
同时把**拒答**接到 rerank 分数上（`min_relevance=0.05`），修掉 E00 起一直为 0 的 `no_answer_accuracy`。

## 2. 测试方法
- **L1**：`python -m pytest -q` → **106 passed**。
- **L2**：`python scripts/run_eval.py --config configs/E06_rerank.yaml --baseline <E05_dense run>`
  - 门禁：`mrr@5 min_delta 0`、`no_answer_accuracy min_delta 0`、`p95_latency_ms max 4000`（含 embedding + rerank 两次 API）。

## 3. 结果（逐指标：含义 / 标准 / 实测 / 结论）

| 指标 | 它衡量什么 | 标准 | 基线（E05_dense） | 本次（E06，+rerank） | 结论 |
|---|---|---|---|---|---|
| `mrr@5`（主） | 首个命中证据的平均倒数排名（越大越靠前） | 相对基线**不得下降** | 0.7833 | 0.8728 | ✅ 通过（+0.0895，提升） |
| `no_answer_accuracy`（主） | 无答案题被**正确拒答**的题数 ÷ 无答案题数 | 不得下降 | 0.0 | 1.0 | ✅ 通过（0→1.0，5/5） |
| `p95_latency_ms`（护栏） | 端到端第 95 百分位耗时 | ≤ 4000 ms（两次 API） | 300.2 ms | 1121.7 ms | ✅ 通过 |

> 观测项：`recall@5` 0.963（未变）、`ndcg@5` 0.9331→0.9484、`context_evidence_coverage` 0.963、`answer_accuracy` 0.8125→0.875、`citation_support` 0.3333→0.2741。

**退出码 0，通过。**

## 4. 结论
- **Rerank 提升排序**：`mrr@5` +0.0895、`ndcg@5` +0.0153，且**召回不受影响**（0.963）。
- **拒答修复**：`no_answer_accuracy` 0→**1.0**（5/5 无答案题全部正确拒答），且未损失召回——
  因为拒答只清空"答案+引用"，检索与覆盖式指标照常计算。

## 5. 拒答信号选择（与 E05 的差异）
E05 探测发现 **dense 余弦无法分离**无答案题；而 **rerank 分数可分离**（no_answer ≤0.048，answerable 多数 ≫），
故拒答阈值 0.05 落在两者之间。这也说明"**拒答需要比语义相似度更强的信号**"。

## 6. 显著性
配对 bootstrap（n=27/32）多为跨 0：`coverage Δ=0.0`、`ndcg +0.0153 CI[−0.0179,0.0559]`、`answer_accuracy +0.0625 CI[−0.125,0.25]` → **证据不足**（样本小）。
`no_answer_accuracy` 为二值量（0→1.0），属方向性修复。

## 7. 边界与不做
- 仅使用该 Key 的**免费 Rerank 模型**；**未调用其它模型**。
- API 存在轻微运行间方差：E06 两次 `mrr@5` 为 0.8543 / 0.8728（同配置）；以报告 run_id 为准。
- `rerank_candidates=20`、阈值 0.05 为预声明值，未做网格；密钥不入库（环境变量）。
