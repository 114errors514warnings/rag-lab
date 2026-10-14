# R1 · E01–E05（解析 / 切块 / 召回）

状态：🟡 进行中（S2 / S3 ✅；E01 / E02 ✅；**E03 ❌ 未通过**）。

- **轮次记录（滚动快照）**：[`round-1.md`](round-1.md)
- 阶段文档（每阶段两份，按阶段分子文件夹）：

| 阶段 | 报告 | 架构说明 |
|---|---|---|
| S2 · 文档与索引优化 | [`S2/stage-S2-report.md`](S2/stage-S2-report.md) | [`S2/stage-S2-architecture.md`](S2/stage-S2-architecture.md) |
| S3 · 检索质量优化 | [`S3/stage-S3-report.md`](S3/stage-S3-report.md) | [`S3/stage-S3-architecture.md`](S3/stage-S3-architecture.md) |
| E01 · 解析器契约 | [`E01/stage-E01-report.md`](E01/stage-E01-report.md) | [`E01/stage-E01-architecture.md`](E01/stage-E01-architecture.md) |
| E02 · 切块参数 | [`E02/stage-E02-report.md`](E02/stage-E02-report.md) | [`E02/stage-E02-architecture.md`](E02/stage-E02-architecture.md) |
| E03 · 符号级切块（未通过） | [`E03/stage-E03-report.md`](E03/stage-E03-report.md) | [`E03/stage-E03-architecture.md`](E03/stage-E03-architecture.md) |

- 阶段架构图（项目根 `.archify/`）：
  - S2：`../../../.archify/architecture-s2-index-20261011-040000/s2-index-architecture.html`
  - S3：`../../../.archify/architecture-s3-retrieval-20261011-043000/s3-retrieval-architecture.html`
- 覆盖实验：E01 解析器、E02 切块参数、E03 Symbol 切块、E04 Embedding、E05 Dense/BM25/Hybrid。
- 对应旧计划：阶段二 + 阶段三前半。
- 约定与模板见 [`../../guide/records-convention.md`](../../guide/records-convention.md)。
