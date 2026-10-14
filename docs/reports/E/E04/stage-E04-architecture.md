# E04 架构说明 · Embedding 提供者（API）

> 报告：[`stage-E04-report.md`](stage-E04-report.md)

## 1. Embedding 提供者（树）

```
rag_engine/config.py  EngineConfig.embed_provider ∈ {hashing, siliconflow, openai}
        │
        ▼
rag_engine/embed/embedder.py::build_embedder(provider, dim, model, corpus_texts)
├── "hashing"     → HashingTfidfEmbedder(dim).fit(corpus)        # 离线、零依赖（默认）
├── "siliconflow" → SiliconFlowEmbedder(model="BAAI/bge-m3", dim=1024)
│                    base_url = https://api.siliconflow.cn/v1
│                    api_key  = $SILICONFLOW_API_KEY（仅环境变量）
└── "openai"      → OpenAIEmbedder(model, dim)                    # api_key = $OPENAI_API_KEY
        │
        ▼  输出 L2 归一化 ⇒ 内积 = 余弦
NumpyVectorStore（向量持久化；Embedder 本身无状态）
```

`SiliconFlowEmbedder` / `OpenAIEmbedder` 共用 `OpenAIEmbedder` 基类（OpenAI 兼容 API，`batch=32`）；
`pipeline.load()` 按 `config.embed_provider` 重建实现（向量从向量库读）。

## 2. 运行时链路（E04）

```
data/kb/** → chunk(512/80, fixed) → SiliconFlow BAAI/bge-m3 → numpy 向量库 → Dense Top-5 → 抽取式生成 + 引用
```

## 3. 密钥处理（硬约束）
- 密钥**只从环境变量读取**（`SILICONFLOW_API_KEY`），**不写入代码 / 配置 / 报告**；`.gitignore` 忽略 `.env`、`*APIKey*`。
- `build`/`load` 均按 `config.embed_provider` 选择实现；配置指纹含 `embed_provider/model/dim`，变更即重建索引。

## 4. 契约
- `Embedder` 协议不变（`name` / `dim` / `fit` / `embed`）；输出 L2 归一化。
- API Embedder 无状态；`save()` 只写标记文件（`model`/`dim`），不存向量。
- `MyPipeline.name` 随配置动态反映真实模型/切块/检索（避免报告误标为 hashing）。

## 5. 边界
- 仅使用 SiliconFlow 的**免费 Embedding 模型**；**未调用其它模型**（拒答/E05、Rerank/E06 另作）。
- `bge-m3` 维度 1024，与离线默认一致，向量库无需改结构。
