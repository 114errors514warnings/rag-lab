# E 计划（实验验证）· 索引

E 计划 = 在系统上做**单变量实验**，量化归因、优化质量/成本/延迟。
来源：《RAG 架构验证与性能优化实验手册》→ [`../../guide/experiment-plan-E01-E12.md`](../../guide/experiment-plan-E01-E12.md)。

**记录机制：按 E 阶段（E00–E12）独立存放**——每个阶段一份报告 + 一份架构说明。
**指标口径**：所有报告里的指标名以 [`metrics-glossary.md`](metrics-glossary.md) 为准（含义 / 计算口径 / 常见标准）。
**E 线总结**（结论 / 负面结果 / 开放项）：[`summary.md`](summary.md)。

| 阶段 | 主题 | 状态 | 报告 / 架构说明 |
|---|---|---|---|
| E00 | 基线（固定块 + Dense Top-5） | ✅ 基线建立 | [`E00/`](E00/) |
| E01 | 解析器契约 | ✅ 通过 | [`E01/`](E01/) |
| E02 | 切块参数（512/80 最优） | ✅ 通过 | [`E02/`](E02/) |
| E03 | 符号级切块 | ❌ **未通过**（3 次尝试） | [`E03/`](E03/) |
| E04 | Embedding（SiliconFlow `BAAI/bge-m3`） | ✅ 通过（显著性存疑） | [`E04/`](E04/) |
| E04b | Embedding 模型对照（多语言 / 中文 / 英文 / Qwen3） | ⚠️ 部分未通过（Qwen3-0.6B PASS；zh/en FAIL） | [`E04b/`](E04b/) |
| E05 | Dense / BM25 / Hybrid 对照 | ⚠️ **门禁未通过**（对照已完成；Dense 最优，BM25/Hybrid 的 recall FAIL） | [`E05/`](E05/) |
| E06 | Rerank + 拒答（`BAAI/bge-reranker-v2-m3`） | ✅ 通过（`no_answer` 0→1.0） | [`E06/`](E06/) |
| E06b | Rerank 模型对照（Qwen3-Reranker） | ⚠️ 未通过（mrr 达标；拒答阈值不可跨模型迁移） | [`E06b/`](E06b/) |
| E07 | Query Rewrite / Multi-query | ⚠️ 未通过（recall 持平；mrr 略降，落在方差内） | [`E07/`](E07/) |
| E08 | 上下文扩展（top-N 进上下文） | ✅ 通过（context_coverage 0.963→1.0） | [`E08/`](E08/) |
| E09 | Context Budget（去重 + 预算裁剪） | ✅ 门禁通过（有 token↔覆盖 权衡） | [`E09/`](E09/) |
| E10 | 增量索引（vs 全量重建） | ✅ 机制验证（改 1 文档仅重建 7/111 块） | [`E10/`](E10/) |
| E11 | 多项目隔离 / 注入防护 | ✅ 通过（`leakage_rate=0`；负对照 FAIL） | [`E11/`](E11/) |
| E12 | 服务化与 Tool 接口（HTTP 端到端） | ✅ 通过（HTTP 与进程内质量一致；隔离不破） | [`E12/`](E12/) |

- 命名：`E{nn}/stage-E{nn}-report.md` 与 `stage-E{nn}-architecture.md`。
- **S 计划（系统建造）在另一棵树**：[`../S/`](../S/)。
- 约定见 [`../../guide/records-convention.md`](../../guide/records-convention.md)。
