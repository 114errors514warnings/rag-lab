# 记录约定与索引

本项目按《RAG 阶段性实践清单》（系统侧）与《RAG 架构验证与性能优化实验手册》（实验侧）
在**同一条流水线**上持续迭代。迭代的代价是：早期形态会被后续覆盖（文件被扩展、配置被改、
指纹变化）。若不显式记录，"当时到底做了什么、边界在哪"就会丢失。

因此约定：

1. **每完成一个轮次，写一份记录**（`docs/reports/R{n}/round-{n}.md`），冻结：
   目标、交付物与逐文件职责、对外契约、已验证行为、门禁/指标结果、**不做什么**、
   以及**后续会改动哪些文件**（演进映射）。
2. **记录是快照，只追加、不改写历史**。行为若被后续改变，在文末"后续变更"追加，而非抹掉原文。
3. **数值基线不复制进记录**：记录只引用 `reports/{run_id}/` 与 `baselines/` 里的冻结文件。
4. 系统能力（旧计划阶段）与实验结论（新手册轮次）**合并到同一份 `round-{n}.md`**，不再分两份。

## 文档布局（教学 / 报告分离）

```
docs/
  guide/                     # 教学与规范文档（跨轮次长期有效）
    implementation-plan.md   #   系统侧总纲（旧计划 S1–S7）
    stage-gates.md           #   固定测试方法说明
    records-convention.md    #   本文件：记录约定与索引
  reports/                   # 逐轮次报告（按实验轮次 R0–R3 分阶段）
    R0/                      #   R0 · 平台化基线
      round-0.md
      diagrams/round-0.architecture.{json,html}
    R1/  R2/  R3/            #   后续轮次，待补
```

> 代码（`rag_engine/` `rag_eval/` `rag_lab/` `scripts/` `tests/` `configs/` `data/`）
> 与运行产物（`reports/{run_id}/` `traces/` `snapshots/`）路径保持不变，仅文档分离。

## 索引

| 轮次 / 里程碑 | 系统侧对应 | 记录 | 状态 |
|---|---|---|---|
| R0 · 平台化基线（E00 + Golden + Trace） | 阶段一 · 基础 RAG Pipeline | [`../reports/R0/round-0.md`](../reports/R0/round-0.md) | ✅ 已冻结 |
| R1 · E01–E05（解析/切块/召回） | 阶段二 + 阶段三前半 | `../reports/R1/round-1.md` | ⬜ 待补 |
| R2 · E06–E09（排序/上下文/成本） | 阶段三后半 + 阶段四 | `../reports/R2/round-2.md` | ⬜ 待补 |
| R3 · E10–E12 + 盲测 | 阶段五 + 六 + 七 | `../reports/R3/round-3.md` | ⬜ 待补 |

> 总纲见 [`implementation-plan.md`](implementation-plan.md)；判据来源见 [`stage-gates.md`](stage-gates.md)。
