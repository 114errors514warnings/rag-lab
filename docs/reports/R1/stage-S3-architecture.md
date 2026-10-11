# rag-lab · S3 架构说明 · 检索质量优化

> 配套报告：[`stage-S3-report.md`](stage-S3-report.md)
> 架构图（Archify，全部闸门通过）：`../../.archify/architecture-s3-retrieval-20261011-043000/s3-retrieval-architecture.html`

## 1. 组件与职责

| 组件 | 职责 | 文件 |
|---|---|---|
| BM25 索引 | 中英分词 + BM25 打分 + 先过滤后排序 | `rag_engine/index/bm25_store.py` |
| Sparse 检索 | BM25 检索适配 | `rag_engine/retrieve/sparse.py` |
| Hybrid 检索 | Dense + Sparse 的 RRF 融合 | `rag_engine/retrieve/hybrid.py` |
| Rerank | 候选 top-N 上的词面重排（Cross-Encoder 替身） | `rag_engine/retrieve/rerank.py` |
| Rewrite | 中→英术语扩展、多查询 | `rag_engine/retrieve/rewrite.py` |

## 2. 数据流

```
query ─▶ rewrite ─┬─▶ Dense(top-N) ─┐
                  └─▶ BM25(top-N)  ─┴─▶ RRF 融合 ─▶ Rerank(top-N) ─▶ top-K ─▶ 生成
```

## 3. 关键契约
- `tokenize(text) -> list[str]`：ASCII 词 + 中文 2-gram（单字也保留）。
- `BM25Store.search(query, k, flt) -> list[Retrieved]`。
- `rrf_fuse(rank_lists, k=60) -> [(chunk_id, score)]`：确定性，同分按 id 升序。
- `HybridRetriever(dense, sparse, rrf_k=60, candidates=50)`。
- `LexicalReranker.rerank(question, hits, top_k) -> list[Retrieved]`（接口同 Cross-Encoder）。

## 4. 系统注册（对齐 retrieval_v1 语料）
`retrieval_v1` 的 `relevant_chunk_ids` 对齐 `data/corpus/demo.jsonl`（c01…），故新增真实引擎系统：
- `demo_dense`：真实 hashing-tfidf Dense（基线）；
- `demo_hybrid`：Dense + BM25 RRF；
- `demo_rerank`：Hybrid + 词面重排；
- `demo_multi`：多查询融合 + 重排。

## 5. 边界与演进
- `my_pipeline`（项目 kb 语料）与 `retrieval_v1` 不对齐，直接评估 `mrr=0`；真实 corpus 的套件重标定留待 S6。
- RRF 的 `k` 与 `candidates` 为固定常量；若接入真实 Cross-Encoder，只需替换 `LexicalReranker`。

---

## 6. 后续变更（S3 已达标）

> 追加记录，不改写上文。

- 新增 `retrieve/rerank.py::IdfReranker`：在候选集内按 **IDF 加权命中** 重排（稀有词权重高，常见词权重低）。
- `retrieve/rewrite.py` 同义词表扩展，`multi_query` 扩展上限 4→8。
- `demo_multi` 现为：**Query Rewrite 多查询 → Dense+BM25 RRF → IDF 重排**，重排使用扩展后的查询词项。
- 结果：`mrr` +0.2250、`recall@3` +0.1250，护栏全 PASS（详见 `stage-S3-report.md` §8）。
