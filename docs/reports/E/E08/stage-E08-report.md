# E08 阶段报告 · 上下文扩展（Context Expansion）

- 实验：E08（E 计划）
- 状态：✅ **通过**（`context_evidence_coverage` 0.9630 → **1.0**；token / 延迟护栏达标）
- 日期：2026-10-15
- 配置：`configs/E08_context.yaml`（基座同 E06：Dense + `bge-m3` + `bge-reranker-v2-m3` + 拒答；加 `context: top_n`）
- 系统：`rag_engine(siliconflow:BAAI/bge-m3 + fixed + dense + rerank:siliconflow:BAAI/bge-reranker-v2-m3 + context:top_n + extractive)`
- 判定方式：**无基线（选项 B）**，按**绝对门禁**判定；`context_evidence_coverage` 以 E06/E07 的 0.9630 作参考
- run_id：`20261015T122744_E08_context_fad2b0f8dd68_699e1af_df5eb069a83579d2_aab322a14cf9b90e`
- 架构说明：[`stage-E08-architecture.md`](stage-E08-architecture.md)

## 1. 目标与主变量
**主变量**：上下文扩展。做法：检索 **top-N（N=10）候选**，其中 **前 k=5 作为 `retrieved`（供 recall@k 判定）**，
**全部 N 作为 `context`（送进生成）**——即"检索单元 ≠ 生成上下文"，用于多证据题。

## 2. 测试方法
- **L1**：`python -m pytest -q` → **110 passed**（新增上下文扩展 / 恒定 2 项）。
- **L2**：`python scripts/run_eval.py --config configs/E08_context.yaml`（无 `--baseline`）
  - 门禁（绝对）：`avg_prompt_tokens max 2000`、`p95_latency_ms max 4000`。

## 3. 结果（逐指标：含义 / 标准 / 实测 / 结论）

| 指标 | 它衡量什么 | 标准 | 参考（E06/E07） | 本次（E08，context=top_n） | 结论 |
|---|---|---|---|---|---|
| `context_evidence_coverage` | 送进生成的**上下文**覆盖全部必要证据的题数 ÷ 可答题数 | 观察项（无基线） | 0.9630 | 1.0000 | ⬆ 提升（覆盖全部 27 题，含多证据题） |
| `avg_prompt_tokens`（护栏） | 送进生成的上下文平均 token 数 | ≤ 2000 | — | 621.75 | ✅ 通过 |
| `p95_latency_ms`（护栏） | 端到端第 95 百分位耗时 | ≤ 4000 ms | — | 2872.7 ms | ✅ 通过 |
| `recall@5` | 覆盖式召回（检索 top-5） | 观察项 | 0.9630 | 0.9630 | 不变 |
| `mrr@5` | 首个命中证据的平均倒数排名 | 观察项 | 0.8728 | 0.8728 | 不变 |
| `no_answer_accuracy` | 无答案题正确拒答比例 | 观察项 | 1.0 | 1.0 | 不变 |

分组 `context_evidence_coverage`：symbol / dependency / literal / semantic **全 1.0**。**退出码 0，通过。**

## 4. 结论
把 **top-10 候选全部作为上下文**，使 `context_evidence_coverage` **0.9630 → 1.0**——**补齐了此前唯一未覆盖的多证据题 `QA18`**
（它的第 3 段证据在 top-5 之外、但在 top-10 之内）。代价是上下文 token 增至 621.75、延迟略升，均在护栏内。

> 说明：先试过 **邻近块扩展（`context: adjacent`）**——`context_evidence_coverage` 仍是 0.963（未提升），
> 因为缺的那段证据不在 top-5 命中的邻位。故采用 `top_n`。两种模式都保留在引擎里。

## 5. 边界与不做
- **无基线（选项 B）**：与旧 run 无配对（用例编号已改 QA/QB/QD）；`context_evidence_coverage` 的提升以数值对比 E06/E07 说明。
- **未实现真·Parent-Child（层级块）**：本集是定长块；如需，用 `chunker.chunk_hierarchical` + `ParentChildRetriever`（S2 已备）另做。
- `citation_support` 0.3333 → 0.2121（上下文变大，引用里掺入更多非目标块）——属观察项，未设门禁。
- 仅用多语言免费模型；密钥不入库。

## 6. 演进映射
- E09（Context Budget / 压缩）：在 E08 的"更大上下文"上做 token 预算与去重/压缩的取舍。
