# E06b 架构说明 · Rerank 模型可替换

> 报告：[`stage-E06b-report.md`](stage-E06b-report.md)

## 1. 接线（与 E06 相同，仅换 `rerank_model`）

```
EngineConfig.rerank       = "siliconflow"
EngineConfig.rerank_model = <模型名>     # BAAI/bge-reranker-v2-m3 | Qwen/Qwen3-Reranker-0.6B | Qwen/Qwen3-Reranker-4B
EngineConfig.rerank_candidates = 20
        │
        ▼
_make_retriever → RerankedRetriever(DenseRetriever, SiliconFlowReranker(model=rerank_model, top_n=candidates))
        │  api.siliconflow.cn/v1/rerank，密钥 $SILICONFLOW_API_KEY
        ▼
top-5 重排结果 → （拒答：top_score < min_relevance）→ 生成
```

## 2. 契约与注意
- 换 `rerank_model` ⇒ `config_hash` 变；`MyPipeline.name` 现包含 rerank 模型名。
- **拒答阈值 `min_relevance` 与 rerank 模型的分数尺度强耦合**：不同模型需各自标定（E06b 用旧阈值 → `no_answer` 掉到 0.6）。
- rerank 的 `relevance_score` 一名两用：既排序、又作拒答信号。
