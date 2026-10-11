# rag-lab · S2 架构说明 · 文档处理与增量索引

> 配套报告：[`stage-S2-report.md`](stage-S2-report.md)
> 架构图（Archify，全部闸门通过）：`../../.archify/architecture-s2-index-20261011-040000/s2-index-architecture.html`

## 1. 组件与职责

| 组件 | 职责 | 文件 |
|---|---|---|
| 文档加载 | 目录 → `Document`（doc_id 由相对路径派生） | `rag_engine/ingest/loader.py` |
| 清洗去重 | 归一化文本、`content_hash`、同源留最新、跨源内容去重 | `rag_engine/ingest/clean.py` |
| 元数据 | `source/section/position/updated_at/project_id/trust` + 行号定位 | `rag_engine/ingest/metadata.py` |
| 切块 | 定长（S1）与层级 Parent-Child（S2） | `rag_engine/ingest/chunker.py` |
| 增量索引 | 以 `doc_id` diff，只重建 added/changed | `rag_engine/index/indexer.py` |
| 向量库 | numpy 内积后端 + `flt` 前置过滤 + `remove_doc_ids` | `rag_engine/index/vector_store.py` |
| 过滤 | 过滤语义 + 候选放大 | `rag_engine/retrieve/filters.py` |
| Parent-Child 检索 | 子块召回 → 父块作上下文 | `rag_engine/retrieve/parent_child.py` |

## 2. 建索引数据流（S2）

```
目录 ─▶ load_tree ─▶ clean_documents ─▶ dedupe_documents
                                              │
                                              ▼
                     chunk_documents(定长)  ── 每块 meta ← build_chunk_meta
                                              │
                                              ▼
                              embed ─▶ NumpyVectorStore.add
```

增量更新（`IncrementalIndexer.update(docs)`）：

```
fingerprint(doc) = sha256(size:overlap:normalized_text)
added   = 当前有、指纹表无
changed = 指纹不同
removed = 指纹表有、当前无
reused  = 指纹相同
store.remove_doc_ids(removed ∪ changed)     # 只删这些 doc 的切片
embed(added ∪ changed) ─▶ store.add         # 只重算这些 doc
fingerprints = 当前
```

## 3. 不变量（L1 硬断言）
1. 只有 `added ∪ changed` 的文档会被重新切块与嵌入（用计数嵌入器断言被嵌入文本 = 该文档切片）。
2. `removed ∪ changed` 的旧切片被删除（按 `doc_id`）。
3. 其余文档的 `chunk_id` 与向量**逐字节不变**（`np.array_equal` 断言）。
4. 索引器状态（`indexer.json`）可持久化并恢复，恢复后同文档判为 `reused`。

## 4. 关键契约
- `Chunk.chunk_id = f"{doc_id}:{seq:04d}"`（S1 契约，S2 不破坏）；层级切块用 `{doc_id}:P{seq:04d}` / `:C{seq:03d}`。
- `VectorStore.search(query_vec, k, flt) -> list[Retrieved]`：**先过滤后排序**（避免候选不足）。
- `IncrementalIndexer.update(docs) -> IndexUpdate{added, changed, removed, reused, chunks_rebuilt}`。
- `build_chunk_meta(doc, text, start, end, order, kind, parent_id, trust) -> dict`。

## 5. 边界与演进
- 增量更新按**内容指纹**而非 mtime（更稳，避免"touch 未改内容"触发重建）。
- Parent-Child 的父块目前也进向量库（供 `build_parent_map` 解析）；S4 Context Builder 会用父块做预算分配。
- 语义切块（按嵌入断句）留待按证据引入；接口 `chunk_fn` 已参数化，替换不影响索引器与检索层。
