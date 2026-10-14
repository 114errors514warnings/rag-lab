# E04b 架构说明 · Embedding 模型可替换

> 报告：[`stage-E04b-report.md`](stage-E04b-report.md)

## 1. 接线（与 E04 相同，仅换 `embed_model`）

```
EngineConfig.embed_provider = "siliconflow"
EngineConfig.embed_model    = <模型名>        # bge-m3 | bge-large-zh-v1.5 | bge-large-en-v1.5 | Qwen/Qwen3-Embedding-0.6B
        │
        ▼
build_embedder("siliconflow", dim, model, corpus_texts) → SiliconFlowEmbedder(model, dim)
        │  api.siliconflow.cn/v1/embeddings，密钥 $SILICONFLOW_API_KEY（不入库）
        ▼
L2 归一化 → numpy 向量库 → Dense Top-5 → 抽取式生成
```

## 2. 契约与注意
- 换 `embed_model` ⇒ `config_hash` 变 ⇒ 索引重建（不同模型的向量空间不可混用）。
- 维度随模型：`embed_dim` 应与模型维度一致（zh/en/m3/Qwen3-0.6B = 1024）。
- 语言路由（中/英分流）需**同名模型分别建索引**，且查询语言与文档语言一致时才有效——本场景（中文查询×中英混合库）不适用。
