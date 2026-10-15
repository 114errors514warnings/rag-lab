# 记录约定与索引

本项目是**两套计划**在**同一条流水线**上持续迭代：

- **S 计划（系统建造）**——把 RAG 系统逐阶段造出来；来源《RAG 阶段性实践清单》→ `implementation-plan.md`。
- **E 计划（实验验证）**——在系统上做单变量实验、量化归因；来源《RAG 架构验证与性能优化实验手册》→ `experiment-plan-E01-E12.md`。

两者**有依赖**（E 跑在 S 造出的系统上），但是**不同的坐标、分别存放、分别追踪**。

## 记录约定

1. **S 计划按 R 轮次记录**：每个轮次一次性实现多个 S 阶段，写一份不可变快照
   `docs/reports/S/R{n}/round-{n}.md`；各阶段文档放
   `docs/reports/S/R{n}/<S阶段>/stage-<S阶段>-{report,architecture}.md`。
   **R 轮次只属于 S 计划**，不承载 E 的语义。
2. **E 计划按 E 阶段记录**：每个实验阶段一份报告 + 一份架构说明，放
   `docs/reports/E/<E阶段>/stage-<E阶段>-{report,architecture}.md`。
3. **只增不改**：记录是快照；行为若被后续改变，在文末「后续变更」追加，而非改写原文。
4. **数值不复制**：记录只引用 `reports/{run_id}/` 与 `baselines/` 里的冻结文件。

## 文档布局

```
docs/
  guide/                        # 教学与规范（跨计划长期有效）
    implementation-plan.md      #   S 计划总纲（S1–S7）
    experiment-plan-E01-E12.md  #   E 计划（E00–E12）
    stage-gates.md
    records-convention.md       #   本文件
    roadmap-merged.md
    agent-runtime-plan-A01-A10.md
    统一开发准则.md
  reports/
    README.md                   #   报告总索引（S / E 两棵树）
    S/                          #   S 计划：按 R 轮次
      README.md
      R0/ round-0.md · architecture.md · diagrams/
      R1/ round-1.md · S2/ · S3/
      R2/ S4/
      R3/ S5/ · S6/ · S7/
    E/                          #   E 计划：按 E 阶段
      README.md
      E00/ E01/ E02/ E03/ …
```

> 代码（`rag_engine/` `rag_eval/` `rag_lab/` `scripts/` `tests/` `configs/` `data/`）
> 与运行产物（`reports/{run_id}/` `traces/` `snapshots/`）路径保持不变，仅文档分离。

## 索引

### S 计划（按 R 轮次）

| 轮次 | 覆盖 S 阶段 | 记录 | 状态 |
|---|---|---|---|
| R0 | S1 · 基础 Pipeline | [`../reports/S/R0/round-0.md`](../reports/S/R0/round-0.md) | ✅ 已冻结 |
| R1 | S2 · 文档与索引 ＋ S3 · 检索质量 | [`../reports/S/R1/round-1.md`](../reports/S/R1/round-1.md) | 🟡 进行中 |
| R2 | S4 · Context Engineering | `../reports/S/R2/round-2.md` | ⬜ 待补 |
| R3 | S5 · Code RAG ＋ S6 · 回归 ＋ S7 · 服务化 | `../reports/S/R3/round-3.md` | ⬜ 待补 |

### E 计划（按 E 阶段）

| 阶段 | 状态 | 记录 |
|---|---|---|
| E00 · 基线 | ✅ | [`../reports/E/E00/`](../reports/E/E00/) |
| E01 · 解析器 | ✅ | [`../reports/E/E01/`](../reports/E/E01/) |
| E02 · 切块参数 | ✅ | [`../reports/E/E02/`](../reports/E/E02/) |
| E03 · 符号级切块 | ❌ 未通过（3 次尝试） | [`../reports/E/E03/`](../reports/E/E03/) |
| E04 · Embedding | ✅（显著性存疑） | [`../reports/E/E04/`](../reports/E/E04/) |
| E04b · Embedding 模型对照 | ⚠️ 部分未通过（Qwen3 PASS；zh/en FAIL） | [`../reports/E/E04b/`](../reports/E/E04b/) |
| E05 · 检索策略对照 | ⚠️ 门禁未通过（Dense 最优） | [`../reports/E/E05/`](../reports/E/E05/) |
| E06 · Rerank + 拒答 | ✅ 通过（no_answer 0→1.0） | [`../reports/E/E06/`](../reports/E/E06/) |
| E06b · Rerank 模型对照 | ⚠️ 未通过（拒答阈值不可迁移） | [`../reports/E/E06b/`](../reports/E/E06b/) |
| E07 · Query Rewrite / Multi-query | ⚠️ 未通过（无增益） | [`../reports/E/E07/`](../reports/E/E07/) |
| E08 · 上下文扩展 | ✅ 通过（context_coverage 0.963→1.0） | [`../reports/E/E08/`](../reports/E/E08/) |
| E09–E12 | ⬜ 未做 | — |

> 总纲见 [`implementation-plan.md`](implementation-plan.md)（S）与 [`experiment-plan-E01-E12.md`](experiment-plan-E01-E12.md)（E）。
