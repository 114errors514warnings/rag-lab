# E06 架构说明 · Rerank + 拒答

> 报告：[`stage-E06-report.md`](stage-E06-report.md)

## 1. 链路（E06）

```
query
  │  Dense（bge-m3）召回 top-20 候选
  ▼
SiliconFlow Rerank（BAAI/bge-reranker-v2-m3, api.siliconflow.cn/v1/rerank）
  │  逐候选给 relevance_score
  ▼
RerankedRetriever → 取 top-5（按 relevance_score 降序）
  │
  ├─ 拒答：top_score < min_relevance(0.05) → refused=True，清空 answer/citations（检索保留）
  ▼
抽取式生成 + 引用
```

## 2. 组件
| 组件 | 文件 | 说明 |
|---|---|---|
| `SiliconFlowReranker` | `retrieve/rerank.py` | OpenAI 无关的 HTTP 调用；密钥 `$SILICONFLOW_API_KEY`；返回 relevance_score |
| `RerankedRetriever` | `retrieve/rerank.py` | 先召回 `candidates`，再重排到 `k` |
| 拒答 | `pipeline.py::answer` | `min_relevance` 作用于 top_score（rerank=rerank 分数） |

## 3. 契约与边界
- `rerank` / `rerank_candidates` 进 `config_hash`；`rerank=none` 时不引入额外开销。
- 只用免费 Rerank 模型，未调用其它模型；密钥不入库。
- rerank 的 relevance_score 既排序、又作拒答信号（一物两用）。
