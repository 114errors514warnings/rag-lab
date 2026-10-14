# R0 · 架构说明（完整版 · 更新于 2026-10-11）

> 说明：R0 原先只有记录（`round-0.md`）与 Archify 架构图，**没有独立的架构说明文档**。
> 按《实践项目合集·统一开发准则》第 3 条，本文件提供**修改后的完整架构说明**，并标注修改时间。
> 触发变更：`config_hash` 改为便携口径（见 `round-0.md` 的「后续变更 · 2026-10-11」）。

## 1. 分层视图

```
data/kb/**（文档集 + proj-auth + proj-sched）
   │  ingest/loader.py        解析 → Document(doc_id, source, doc_type, text, project_id)
   ▼
   │  ingest/chunker.py       滑窗 + overlap → Chunk(chunk_id, start/end_line, meta)
   ▼
   │  embed/embedder.py       HashingTfidf（默认）/ OpenAI（可选） → L2 归一化向量
   ▼
   │  index/vector_store.py   内积索引（=余弦），支持 project_id 过滤与持久化
   ▼
   │  retrieve/dense.py       question → 向量 → Top-K
   ▼
   │  generate/generator.py   抽取式回答 + [chunk_id] 引用 + refused 标记
   ▼
Answer → eval_adapter.MyPipeline.answer(case,k) → SystemAnswer（评测协议）
```

## 2. 组件与职责

| 组件 | 职责 | 文件 |
|---|---|---|
| 配置 | `EngineConfig` + `fingerprint()`（**便携指纹**） | `rag_engine/config.py` |
| 加载 | TXT/MD/PY/PDF → `Document`；多项目 `load_tree` | `rag_engine/ingest/loader.py` |
| 切块 | 固定长度 + overlap（附行号） | `rag_engine/ingest/chunker.py` |
| 嵌入 | `Embedder` 协议 + hashing/OpenAI 实现 | `rag_engine/embed/embedder.py` |
| 向量库 | `VectorStore` 协议 + numpy 后端 | `rag_engine/index/vector_store.py` |
| 检索 | Top-K 语义检索（可过滤） | `rag_engine/retrieve/dense.py` |
| 生成 | 带引用抽取式回答（+ 可选 OpenAI） | `rag_engine/generate/generator.py` |
| 组装 | 建索引/查询/manifest | `rag_engine/pipeline.py` |
| 评测适配 | `MyPipeline`（系统↔协议唯一连接点） | `rag_engine/eval_adapter.py` |
| 实验平台 | config/golden/scoring/trace | `rag_lab/` |
| 评测内核 | schema/metrics/evidence/runner | `rag_eval/` |

## 3. 关键契约（更新点标注）

| 契约 | 内容 |
|---|---|
| 稳定 `chunk_id` | `f"{doc_id}:{seq:04d}"`，同文档同参数恒定 |
| 向量归一化 | Embedder 输出 L2 归一化 ⇒ 内积 = 余弦 |
| **`config_hash`（2026-10-11 更新）** | `fingerprint()` 只哈希**语义参数**（切块/嵌入/检索/生成）；**排除路径字段** `index_dir`/`raw_dir` ⇒ 跨机器/目录可复现；历史值由旧口径产生，不可直接比较 |
| 引用可回溯 | `citations` ⊆ 实际使用片段 |
| 系统与评测解耦 | 唯一连接点 `eval_adapter.MyPipeline.answer` |
| manifest 决定重建 | 源文件 sha256 + config 指纹 |

## 4. 数据流（run_eval）

```
configs/E0x.yaml ──▶ ExperimentConfig ──▶ EngineConfig(**system)
        │                                         │
        │                              MyPipeline._ensure() → RAGPipeline
        ▼                                         │
data/golden/cases.jsonl ──▶ 逐题 answer() ──▶ score_case → aggregate → metrics
        │                                         │
        └─▶ trace.jsonl / reports/{run_id}/{metrics.json,cases.jsonl,errors.csv,comparison.md}
```

## 5. 不变量与边界

- 不变量：`chunk_id` 稳定；向量归一化；`config_hash` 随语义参数变、不随路径变；引用可回溯；系统与评测解耦。
- 边界（本阶段不做）：清洗/去重、语义/层级切块、Parent-Child、Metadata Filtering、增量索引、
  BM25/Hybrid/Rerank/Rewrite、Context 压缩与预算、AST/符号索引、忠实度评测、FastAPI/MCP/Docker；
  默认不调用真实神经网络 Embedding/LLM（离线可复现）。
- 架构图：`docs/reports/S/R0/diagrams/round-0.architecture.html`（Archify，全闸门通过）。
