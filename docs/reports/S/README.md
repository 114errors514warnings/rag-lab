# S 计划（系统建造）· 索引

S 计划 = 把 RAG 系统（Project Knowledge Engine）逐阶段造出来。
来源：《RAG 阶段性实践清单》→ [`../../guide/implementation-plan.md`](../../guide/implementation-plan.md)。

**记录机制：按 R 轮次（R0–R3）分批推进**——每个轮次一次性实现多个 S 阶段。

| 轮次 | 覆盖的 S 阶段 | 轮次记录 | 阶段文档 |
|---|---|---|---|
| R0 | S1 · 基础 Pipeline | [`R0/round-0.md`](R0/round-0.md) | [`R0/architecture.md`](R0/architecture.md) · `R0/diagrams/` |
| R1 | S2 · 文档与索引 ＋ S3 · 检索质量 | [`R1/round-1.md`](R1/round-1.md) | [`R1/S2/`](R1/S2/) · [`R1/S3/`](R1/S3/) |
| R2 | S4 · Context Engineering | `R2/round-2.md`（待补） | [`R2/S4/`](R2/S4/) |
| R3 | S5 · Code RAG ＋ S6 · 回归 ＋ S7 · 服务化 | `R3/round-3.md`（待补） | [`R3/S5/`](R3/S5/) · [`R3/S6/`](R3/S6/) · [`R3/S7/`](R3/S7/) |

- 轮次记录：`R{n}/round-{n}.md`（不可变快照，只追加、不改写）。
- 阶段文档：`R{n}/<S阶段>/stage-<S阶段>-{report,architecture}.md`。
- **E 计划（实验验证）在另一棵树**：[`../E/`](../E/)。
- 约定见 [`../../guide/records-convention.md`](../../guide/records-convention.md)。
