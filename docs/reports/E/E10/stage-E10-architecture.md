# E10 架构说明 · 增量索引

> 报告：[`stage-E10-report.md`](stage-E10-report.md)

## 1. 机制（复用 S2 `rag_engine/index/indexer.py`）

```
IncrementalIndexer(store, embedder, size, overlap)
  update(docs) -> IndexUpdate{added, changed, removed, reused, chunks_rebuilt}
    指纹   = sha256(f"{size}:{overlap}:{doc.text}")
    1) 按 doc_id 做 diff：added / changed / removed / reused
    2) store.remove_doc_ids(removed ∪ changed)      # 删旧切片
    3) 只对 (added ∪ changed) 重切块 + 嵌入 -> store.add
    4) 其余文档：chunk_id 与向量**逐字节不变**
  save/load(dir) -> indexer.json（持久化 doc_id 指纹）
```

## 2. 基准 harness
`scripts/exp_e10_incremental.py`：在 `data/kb` 上全量建索引，再改 1 个文档做增量；
输出"重建块数 / 耗时 / 未改动向量是否逐字节不变"，并据此返回退出码。

## 3. 不变量与边界
- **不变量**：只重建受影响切片；其余向量逐字节不变（L1 硬断言）。
- **边界**：全量 diff（doc_id 指纹），非文件系统事件监听；增量不改检索指标。
