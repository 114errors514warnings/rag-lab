# E 计划（实验验证）· 索引

E 计划 = 在系统上做**单变量实验**，量化归因、优化质量/成本/延迟。
来源：《RAG 架构验证与性能优化实验手册》→ [`../../guide/experiment-plan-E01-E12.md`](../../guide/experiment-plan-E01-E12.md)。

**记录机制：按 E 阶段（E00–E12）独立存放**——每个阶段一份报告 + 一份架构说明。

| 阶段 | 主题 | 状态 | 报告 / 架构说明 |
|---|---|---|---|
| E00 | 基线（固定块 + Dense Top-5） | ✅ 基线建立 | [`E00/`](E00/) |
| E01 | 解析器契约 | ✅ 通过 | [`E01/`](E01/) |
| E02 | 切块参数（512/80 最优） | ✅ 通过 | [`E02/`](E02/) |
| E03 | 符号级切块 | ❌ **未通过**（3 次尝试） | [`E03/`](E03/) |
| E04 | Embedding（SiliconFlow `BAAI/bge-m3`） | ✅ 通过（显著性存疑） | [`E04/`](E04/) |
| E05 | Dense / BM25 / Hybrid + 拒答 | ⬜ 未做 | — |
| E06–E12 | Rerank / Rewrite / Parent-Child / Context / 增量 / 隔离 / Tool | ⬜ 未做 | — |

- 命名：`E{nn}/stage-E{nn}-report.md` 与 `stage-E{nn}-architecture.md`。
- **S 计划（系统建造）在另一棵树**：[`../S/`](../S/)。
- 约定见 [`../../guide/records-convention.md`](../../guide/records-convention.md)。
