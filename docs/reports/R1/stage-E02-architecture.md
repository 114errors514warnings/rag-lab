# rag-lab · E02 架构说明 · 切块参数对照

> 报告：[`stage-E02-report.md`](stage-E02-report.md)
> **次要阶段**：架构以树形文档表示（未生成 Archify 图）。

## 1. 切块层结构（树）

```
ingest/chunker.py
├── chunk_document(doc, size, overlap) -> [Chunk]
│     ├── _pick_end(text,start,size)   # 在 [start+0.6*size, start+size] 内回退到换行/句读
│     ├── chunk_id = f"{doc_id}:{seq:04d}"       # 序号连续、稳定
│     └── meta = {source, doc_type, start, end, start_line, end_line, order, ...}
└── chunk_documents(docs, size, overlap)
```

## 2. 参数如何影响结果

```
size ↑  → 单块覆盖更长 → 覆盖式 recall@5 ↑（本实验 512 优于 400 优于 256）
overlap ↑ → 相邻块共享更多上下文（块数不减）
size ↓  → 块更碎 → 证据被拆散 → recall ↓
```

## 3. 关键契约（E02 断言）
- `chunk_id` 序号连续：`[f"{doc_id}:{i:04d}" for i in range(n)]`。
- 同文档同参数 ⇒ 同 `chunk_id` 列表（稳定）。
- `size>0` 且 `0<=overlap<size`，否则 `ValueError`。
- 改参数 ⇒ 块数变化（但首块序号仍为 `:0000`）。

## 4. 不变量与边界
- 不变量：切块确定性；`chunk_id` 与行号字段（供证据映射）稳定。
- 边界：本阶段只调 `size/overlap`，不改嵌入/检索/生成；`config_hash` 随 `chunk_size` 变化（语义参数），不随路径变化。
