# E05 阶段报告 · 检索策略对照（Dense / BM25 / Hybrid）

- 实验：E05（E 计划）
- 状态：✅ 对照完成 —— **结论：Dense 最优**；BM25 / Hybrid 未过召回门禁
- 日期：2026-10-14
- 配置：`configs/E05_dense.yaml` · `configs/E05_bm25.yaml` · `configs/E05_hybrid.yaml`
- 基座：SiliconFlow `BAAI/bge-m3`（512/80，同 E04）；主变量 = `retrieval`
- 数据集：`data/golden/cases.jsonl`（32 题）
- 架构说明：[`stage-E05-architecture.md`](stage-E05-architecture.md)

## 1. 目标与主变量
对照三种检索模式：`dense`（向量）、`bm25`（稀疏）、`hybrid`（Dense+BM25 的 RRF 融合）；其余全部冻结。

## 2. 测试方法
- **L1**：`python -m pytest -q` → **106 passed**（新增检索选型 / 拒答阈值 / 重排 6 项）。
- **L2**：三方案各跑一次；`bm25`/`hybrid` 与 `dense` 配对（`--baseline <E05_dense run>`）。
  - 门禁：`recall@5 max_delta -0.02`、`mrr@5 max_delta -0.02`、`p95_latency_ms max 2500`。

## 3. 结果

| 模式 | `recall@5` | `precision@5` | `mrr@5` | `ndcg@5` | `context_cov` | `no_answer` | `p95(ms)` | 召回门禁 |
|---|---|---|---|---|---|---|---|---|
| **dense**（基线） | **0.9630** | 0.3333 | 0.7833 | 0.9331 | 0.9630 | 0.0 | 300.2 | — |
| bm25 | 0.7778 | 0.4414 | 0.7883 | 0.8818 | 0.7778 | 0.2 | 0.6 | **FAIL**（−0.1852） |
| hybrid | 0.9259 | 0.3111 | 0.7883 | 0.9467 | 0.9259 | 0.0 | 103.6 | **FAIL**（−0.0371） |

`mrr@5` / `p95` 护栏三方案均 PASS。run_id：dense `…213047…`、bm25 `…213109…`、hybrid `…213123…`。

## 4. 结论
在"强 Dense（bge-m3）+ 覆盖式召回"下：**Dense 最优**。
- **BM25**：`precision` 更高（0.4414）、`p95` 极快（无向量调用），但**召回显著下降**（配对 `coverage −0.1852`，95% CI `[−0.3333, −0.037]`，**显著**）。
- **Hybrid（RRF）**：`ndcg` 略升、`mrr` 略升，但**召回下降**（−0.0371）；配对 `coverage −0.037`，CI `[−0.1111, 0.0]` 跨 0 → **证据不足**。

即：**Hybrid 在此语料/套件上无实质增益**（呼应手册 E05 的提醒：若 Hybrid 无增益，应检查 tokenizer/字段/去重/RRF）。

## 5. 拒答（本阶段未启用）
探测显示 **dense 余弦无法分离无答案题**（answerable 0.49–0.71 vs no_answer 0.29–0.59，重叠严重），
故 E05 保持 `min_relevance=0`（不拒答）；**拒答改由 E06 的 rerank 分数实现**（可分离）。

## 6. 边界与不做
- 仅使用 SiliconFlow 免费模型（embedding）；BM25 为本地实现。
- 不调参 RRF（`rrf_k=60`、`candidates=50` 固定）；不改数据集。
