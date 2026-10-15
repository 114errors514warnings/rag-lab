# E06b 阶段报告 · Rerank 模型对照（bge-reranker-v2-m3 / Qwen3-Reranker）

- 实验：E06b（E 计划；E06 的延伸 —— 更换 Rerank 模型）
- 状态：⚠️ **未通过**（`mrr@5` 达标；**`no_answer_accuracy` 未过** —— 拒答阈值不可跨模型迁移）
- 日期：2026-10-14
- 配置：`configs/E06b_{qwen06,qwen4}.yaml`（基座同为 Dense + `bge-m3`，候选 20，拒答阈值 0.05）
- 基线：**E06 = `BAAI/bge-reranker-v2-m3`**（`mrr@5=0.8728`、`no_answer=1.0`）
- run_id：qwen06 `…221156…`、qwen4 `…221223…`
- 架构说明：[`stage-E06b-architecture.md`](stage-E06b-architecture.md)

## 1. 目标
比较 Rerank 模型：`bge-reranker-v2-m3`（现用）vs `Qwen3-Reranker-0.6B` / `4B`。

## 2. 结果（对照 bge-reranker；逐指标：含义 / 标准 / 实测 / 结论）

**判定标准**：替代模型相对 `bge-reranker-v2-m3`：`mrr@5` 回退 ≤ 0.01、`no_answer_accuracy` 不得下降。

| 指标 | 它衡量什么 | 标准 |
|---|---|---|
| `mrr@5` | 首个命中证据的平均倒数排名 | 回退 ≤ 0.01 |
| `no_answer_accuracy` | 无答案题**正确拒答**的题数 ÷ 无答案题数 | 不得下降（基线 1.0） |
| `p95_latency_ms` | 端到端第 95 百分位耗时 | ≤ 4000 ms |

| Rerank 模型 | `recall@5` | `mrr@5` | `no_answer_accuracy` | `p95(ms)` | 结论 |
|---|---|---|---|---|---|
| `bge-reranker-v2-m3`（基线） | 0.963 | 0.8728 | 1.0 | 1122 | — |
| `Qwen3-Reranker-0.6B` | 0.963 | 0.8642 ✅ | 0.6 ❌ | 765 | ❌ **FAIL**（`no_answer` 0.6 < 1.0） |
| `Qwen3-Reranker-4B` | 0.963 | 0.9259 ✅ | 0.6 ❌ | 1068 | ❌ **FAIL**（`no_answer` 0.6 < 1.0） |

## 3. 结论
1. **排序：`Qwen3-Reranker-4B` 最好**（`mrr@5=0.9259`，比 bge-reranker 高 **+0.0531**；`ndcg` 也最高）。
2. **但拒答未过**：`no_answer_accuracy` 从 1.0 掉到 **0.6** —— 因为**拒答阈值 0.05 是按 bge-reranker 的分数标定的**，
   **Qwen3-Reranker 的分数尺度不同**，0.05 对它不成立（部分无答案题未被拒）。→ **换 rerank 模型必须重新标定拒答阈值**。

## 4. 边界与后续
- 只测"排序"与"沿用旧阈值"的拒答；**未对 Qwen 模型重标阈值**（属"阈值需模型专属"的结论，不是实现 bug）。
- 仅使用该 Key 的免费 Rerank 模型；未调用其它模型；密钥不入库。
- API 存在运行间方差（E06b_qwen06 `mrr` 两次 0.8827/0.8642）。

---

## 5. 决策（2026-10-14）

**当前默认 Rerank 采用多语言 `BAAI/bge-reranker-v2-m3`**（拒答阈值 0.05 已按它标定，`no_answer=1.0`）。
`Qwen/Qwen3-Reranker-4B` 排序更强（`mrr` 0.9259）但需按其分数重标拒答阈值，**暂不采用**（留作后续可选项）。
