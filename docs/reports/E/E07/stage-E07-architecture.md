# E07 架构说明 · Query Rewrite / Multi-query

> 报告：[`stage-E07-report.md`](stage-E07-report.md)

## 1. 链路（E07）

```
query
  │  rewrite()/multi_query()   → [原查询, 原查询+英文术语扩展]
  ▼
MultiQueryRetriever
  ├─ 对每条查询各跑 base（Dense，bge-m3）召回候选
  ├─ rrf_fuse(多路排名)                    # RRF，确定
  ▼
候选（<=rerank_candidates）
  │  SiliconFlowReranker（bge-reranker-v2-m3）
  ▼
top-5 →（拒答 top<0.05）→ 抽取式生成
```

## 2. 组装顺序（`pipeline._make_retriever`）
`base(dense|bm25|hybrid)` → **`rewrite: multi` 时包 `MultiQueryRetriever`** → `rerank` 时再包 `RerankedRetriever`。

## 3. 组件与契约
| 组件 | 文件 | 说明 |
|---|---|---|
| `rewrite` / `multi_query` | `retrieve/rewrite.py` | 中文→英文术语扩展（确定性） |
| `MultiQueryRetriever` | `retrieve/rewrite.py` | 多路召回 + `rrf_fuse` 融合 |
| `EngineConfig.rewrite` | `config.py` | `none` \| `multi`，进 `config_hash` |

## 4. 边界
- 融合只做 RRF，无加权；术语表小。
- 本场景召回已饱和，故多查询收益有限（见报告 §4）。
