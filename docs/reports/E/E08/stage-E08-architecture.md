# E08 架构说明 · 检索单元与生成上下文的分离

> 报告：[`stage-E08-report.md`](stage-E08-report.md)

## 1. 链路（E08）

```
query
  │  rewrite(none) → retrieval(dense) → rerank(bge-reranker-v2-m3)
  ▼
检索 top-N (N=context_max_chunks=10)
  ├─ retrieved = hits[:k]           # k=5，供 recall@k / mrr / precision
  └─ context   = hits[:N]           # 供生成 + Context Evidence Coverage
  │
  ▼ 生成（抽取式，用 context）→ 引用
```

## 2. 上下文策略（`EngineConfig.context`）

| 取值 | 行为 |
|---|---|
| `none`（默认） | `context = retrieved`（= top-k），历史行为 |
| `top_n` | 检索 top-N，`retrieved=top-k`，`context=top-N` |
| `adjacent` | `retrieved=top-k`，`context=top-k + 邻近块（order±window）` |

相关字段：`context_max_chunks`（N）、`context_window`（邻近半径）。

## 3. 契约与注意
- `context` 进 `config_hash`；`MyPipeline.name` 含 `context:<mode>`。
- `SystemAnswer` 新增 `context`（`RetrievedChunk[]`）；`rag_lab` 的 `context_evidence_coverage` 优先用它映射。
- **`retrieved` 与 `context` 分离**：扩展只影响上下文，不改变 recall@k 的检索结果。
