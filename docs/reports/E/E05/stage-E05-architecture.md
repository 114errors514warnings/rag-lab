# E05 架构说明 · 检索模式与重排接线

> 报告：[`stage-E05-report.md`](stage-E05-report.md)　· 后续 E06 同用此接线

## 1. 检索/重排组装（树）

```
rag_engine/config.py  EngineConfig.retrieval ∈ {dense, bm25, hybrid}
                      EngineConfig.rerank    ∈ {none, lexical, idf, siliconflow}
        │
        ▼
rag_engine/pipeline.py::_make_retriever(config, embedder, store)   # build 与 load 共用
├── dense  → DenseRetriever(embedder, store, min_relevance=0)          # 拒答在 pipeline 层统一处理
├── bm25   → SparseRetriever(BM25Store().add(store.chunks))
└── hybrid → HybridRetriever(dense, SparseRetriever(bm25), candidates=rerank_candidates)
        │  （若 rerank != none，再用 RerankedRetriever 包一层）
        ▼
RerankedRetriever(base, reranker, candidates)
   ├── lexical   → LexicalReranker（离线词面替身）
   ├── idf       → IdfReranker（候选集内 IDF 加权）
   └── siliconflow → SiliconFlowReranker（BAAI/bge-reranker-v2-m3，API）
```

## 2. 拒答（pipeline 层统一）
`RAGPipeline.answer`：`low = min_relevance>0 and top_score < min_relevance`；命中则 `refused=True`，
并清空 `answer`/`citations`（检索结果保留在 trace）。`min_relevance` 语义：dense=余弦；rerank=rerank 分数。

## 3. 契约
- `retrieval` / `rerank` / `rerank_candidates` 均进 `config_hash` ⇒ 配置变即重建索引。
- BM25 索引在 build/load 时由 `store.chunks` 重建（不单独持久化）。
- `MyPipeline.name` 动态反映 embedding/切块/检索/重排。

## 4. 边界
- bm25/hybrid 无重排时 `min_relevance` 不适用（分数非同一量纲）。
