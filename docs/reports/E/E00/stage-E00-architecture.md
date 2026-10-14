# E00 架构说明 · 基线链路

> 报告：[`stage-E00-report.md`](stage-E00-report.md)
> 轮次级架构图（含 E00 链路，属 S/R0）：`../../S/R0/diagrams/round-0.architecture.html`

## 1. 基线链路（E00）

```
data/kb/**（文档集 + proj-auth + proj-sched）
   │ loader / chunker            固定块 400 / overlap 80
   ▼
   │ HashingTFIDF                L2 归一化向量
   ▼
   │ numpy 向量库               内积 = 余弦
   ▼
   │ Dense Top-5                按 project_id 过滤；min_relevance = 0（不拒答）
   ▼
   │ 抽取式生成 + 引用           逐条 [chunk_id]
   ▼
SystemAnswer（评测协议）
```

## 2. 评测链路

```
run_eval.py --config configs/E00.yaml
  ├─ 加载 data/golden/cases.jsonl（证据制，32 题）
  ├─ MyPipeline.answer(case, k)              # 被测系统
  ├─ rag_eval 证据制指标（覆盖式 recall / nDCG / 证据覆盖 / 配对 CI）
  └─ reports/{run_id}/ + traces/{run_id}.jsonl
```

## 3. 关键契约
- 固定块 `size=400 / overlap=80`；单路 Dense；`top_k=5`；`min_relevance=0`。
- `chunk_id = {doc_id}:{seq:04d}` 稳定；证据按 `file + 行区间` 映射。
- Trace 完整率 1.0（每条 case 都有召回记录）。

## 4. 边界
- 这是**基线**，不追求高分：无重排、无 Query Rewrite、无上下文预算、无真实语义 embedding、无拒答。
- E00 的具体缺陷与后续在 E 计划的其它阶段处理；拒答在 E05 修。
