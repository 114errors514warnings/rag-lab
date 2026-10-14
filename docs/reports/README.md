# 报告索引（docs/reports）

按**实验轮次** R0–R3 分阶段；每轮含一份不可变快照 `round-{n}.md`，以及**每阶段一个子文件夹**
（`<阶段>/stage-<阶段>-report.md` + `stage-<阶段>-architecture.md`）。

| 轮次 | 快照 | 阶段子文件夹 | 状态 |
|---|---|---|---|
| R0 · 平台化基线 | [`R0/round-0.md`](R0/round-0.md) | [`R0/architecture.md`](R0/architecture.md) + [`R0/diagrams/`](R0/diagrams/) | ✅ 已冻结 |
| R1 · 解析/切块/召回 | [`R1/round-1.md`](R1/round-1.md) | `R1/E01` `R1/E02` `R1/E03` `R1/S2` `R1/S3` | 🟡 进行中（E03 ❌） |
| R2 · 排序/上下文/成本 | `R2/round-2.md`（待补） | `R2/S4` | 🟡 进行中 |
| R3 · 增量/隔离/服务化 | `R3/round-3.md`（待补） | `R3/S5` `R3/S6` `R3/S7` | 🟡 进行中 |

## 命名与放置约定

- 快照：`R{n}/round-{n}.md`（不可变，只追加）。
- 阶段报告 / 架构说明：`R{n}/<阶段>/stage-<阶段>-report.md` 、`stage-<阶段>-architecture.md`
  （阶段 = `E01`…`E12`、`S1`…`S7`）。
- 架构图：`R{n}/diagrams/` 或项目根 `.archify/<type>-<slug>-<时间戳>/`。

> 约定与模板见 [`../guide/records-convention.md`](../guide/records-convention.md)；
> 开发纪律见 [`../guide/统一开发准则.md`](../guide/统一开发准则.md)。
