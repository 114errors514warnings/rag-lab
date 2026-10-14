# E07 阶段报告 · Query Rewrite / Multi-query

- 实验：E07（E 计划）
- 状态：⚠️ **门禁未通过**（`mrr@5` −0.0166；`recall`/`no_answer`/`p95` 达标）
- 日期：2026-10-14
- 配置：`configs/E07_multi.yaml`（基座同 E06：Dense + `bge-m3` + `bge-reranker-v2-m3`，加 `rewrite: multi`）
- 基线：**E06**（`recall@5=0.963`、`mrr@5=0.8728`、`no_answer=1.0`）
- run_id：`20261014T221621_E07_multi_4096dcbafed6_4b74acf_df5eb069a83579d2_626aa1732b4f8e12`
- 架构说明：[`stage-E07-architecture.md`](stage-E07-architecture.md)

## 1. 目标与主变量
**主变量**：查询改写/多查询（none → `multi`）。做法：把中文查询经术语表扩出英文标识符，形成"原查询 + 扩展查询"两路，
各召回候选后用 **RRF 融合**，再交 rerank。

## 2. 测试方法
- **L1**：`python -m pytest -q` → **108 passed**（新增多查询融合确定性 / 选型 2 项）。
- **L2**：`python scripts/run_eval.py --config configs/E07_multi.yaml --baseline <E06 run>`
  - 门禁：`recall@5 min_delta 0`、`mrr@5 max_delta -0.01`、`no_answer_accuracy min_delta 0`、`p95 max 4000`。

## 3. 结果

| 门禁 / 指标 | 基线 E06 | 本次 E07 | Δ | 判定 |
|---|---|---|---|---|
| `recall@5`（主） | 0.9630 | 0.9630 | +0.0000 | PASS |
| `mrr@5`（护栏） | 0.8728 | 0.8562 | **−0.0166** | **FAIL** |
| `no_answer_accuracy`（护栏） | 1.0 | 1.0 | +0.0 | PASS |
| `p95_latency_ms`（护栏） | 1122 | 1478 | — | PASS |

其它：`ndcg@5` 0.9484→0.9497、`precision@5` 0.3259、`answer_accuracy` 0.875。配对：`coverage Δ=0.0`、`ndcg +0.0013`、`answer_accuracy Δ=0.0`。

## 4. 结论
**多查询在本套件上无增益**：召回已饱和（E06 已 26/27=0.963），术语扩展**未带来任何新命中**；
RRF 融合反而使 `mrr` 略降（−0.0166）→ 触发护栏 FAIL。
> 注：E06 自身 `mrr` 有运行间方差（两次 0.8543 / 0.8728），E07 的 0.8562 **落在该方差范围内**，
> 故更严谨的表述是"**未见提升**"，而非"确定性下降"。

## 5. 边界与不做
- 术语表很小（`rewrite.SYNONYMS`）；未调 `limit` / `rrf_k` / 候选数（预声明值）。
- 仅多语言模型（`bge-m3` + `bge-reranker-v2-m3`）；未调用其它模型；密钥不入库。
- 语义类题（`semantic`）此前召回 0.8889，本次未单独提升——改写词表未覆盖其缺口。

## 6. 演进映射
- 若要真正验证改写的价值：需更大/更难、含**英文查询**的套件（S 侧扩集），届时改写/多查询才有发挥空间。
- E08（Parent-Child）、E09（Context Budget）继续。
