# E04 阶段报告 · Embedding（SiliconFlow `BAAI/bge-m3` vs hashing-tfidf）

- 实验：E04（E 计划）
- 状态：✅ 门禁通过；**显著性存疑**（见 §5）
- 日期：2026-10-14
- 配置：`configs/E04.yaml`（chunk 512/80 + `embed_provider=siliconflow`）
- 系统：`rag_engine(siliconflow:BAAI/bge-m3 + fixed + dense + extractive)`
- 数据集：`data/golden/cases.jsonl`（32 题，证据制）
- 基线：**E02**（hashing-tfidf，512/80，`recall@5=0.8519`）
- run_id：`20261014T212627_E04_3fedce19e4e8_c8de897_df5eb069a83579d2_626aa1732b4f8e12`
- 架构说明：[`stage-E04-architecture.md`](stage-E04-architecture.md)

## 1. 目标与主变量
**主变量**：Embedding 提供者（离线 `hashing-tfidf` → 真实语义向量）；其余全部冻结（512/80 定长、Dense Top-5、抽取式生成）。
真实语义向量用 **SiliconFlow 免费模型 `BAAI/bge-m3`（dim=1024）**，密钥经环境变量 `SILICONFLOW_API_KEY` 注入，**不入库**。

## 2. 测试方法
- **L1**：`python -m pytest -q` → **100 passed**（新增 API Embedder 的构造 / 回落 / 缺钥报错 4 项）。
- **L2**：`python scripts/run_eval.py --config configs/E04.yaml --baseline <E02 run>`
  - 门禁：`recall@5 min_delta 0`；`mrr@5 max_delta -0.01`；`p95_latency_ms max 2000`（API 含网络延迟，绝对上限预声明）。

## 3. 结果（逐指标：含义 / 标准 / 实测 / 结论）

| 指标 | 它衡量什么 | 标准 | 基线（E02，hashing） | 本次（E04，bge-m3） | 结论 |
|---|---|---|---|---|---|
| `recall@5` | 覆盖式召回：充分证据落入检索 top-5 的题数 ÷ 可答题数 | 相对 E02 **不得回退** | 0.8519 | 0.9630 | ✅ 通过（+0.1111，提升） |
| `mrr@5` | 首个命中证据的平均倒数排名（越大越靠前） | 回退 ≤ 0.01 | 0.7914 | 0.7833 | ✅ 通过（−0.0081） |
| `p95_latency_ms` | 端到端第 95 百分位耗时 | ≤ 2000 ms（API 含网络，预声明放宽） | — | 301.1 ms | ✅ 通过 |

> 观测项（未设门禁）：`ndcg@5` 0.8921→0.9331、`context_evidence_coverage` 0.9630、`answer_accuracy` 0.6875→0.8125、`no_answer_accuracy` 仍 0.0；分组召回 symbol / dependency / literal 均 1.0、semantic 0.8889。

**退出码 0，通过。**

## 4. 结论
真实语义向量（`BAAI/bge-m3`）使**覆盖式召回 0.8519→0.963**，`ndcg`/`answer_accuracy` 同步上升，护栏（`mrr`/`p95`）未破线。

## 5. 显著性（配对 bootstrap，n=27 可答题）
| 指标 | 均值 Δ | 95% CI | 结论 |
|---|---|---|---|
| coverage | +0.1111 | [0.0, 0.2593] | 跨 0 → **证据不足** |
| context_coverage | +0.1111 | [0.0, 0.2593] | 跨 0 → 证据不足 |
| answer_accuracy | +0.0938 | [0.0, 0.2188] | 跨 0 → 证据不足 |

即：改善在**点估计**上明显、门禁（按点估计）PASS，但**统计上不充分**（样本小，CI 下界正好落在 0）。要更强结论需扩大测试集（属 S 计划侧的套件工作）。

## 6. 边界与不做
- `no_answer_accuracy` 仍为 0（拒答机制在 **E05** 处理）。
- 只使用了该 Key 的**免费 Embedding 模型**；**Rerank 模型**（`BAAI/bge-reranker-v2-m3`）留待 **E06**。未调用其它模型。
- API 延迟含网络（avg 108ms / p95 301ms）；本地 hashing 无此开销。
- 密钥不入库：仅环境变量 `SILICONFLOW_API_KEY`；`.gitignore` 忽略 `.env` / `*APIKey*`。
