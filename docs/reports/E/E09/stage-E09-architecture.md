# E09 架构说明 · Context Budget 接入

> 报告：[`stage-E09-report.md`](stage-E09-report.md)

## 1. 链路（E09，`context: builder`）

```
query → dense(bge-m3) → rerank(bge-reranker-v2-m3)
  ▼
候选 (top-N, N=context_max_chunks)
  │  ContextBuilder(max_tokens=context_budget_tokens)   # 复用 S4 rag_engine/context/builder.py
  │    1) 去重（chunk_id + 文本近似）
  │    2) 相关性阈值过滤
  │    3) 分组（source）→ 每文档至少 1 块
  │    4) 预算填充（按分数）→ 超预算截断（保留来源/定位）
  │    5) stale / low_trust 标注
  ▼
context = segments（截断后的文本）→ 抽取式生成 + 引用
```

## 2. 上下文策略（`EngineConfig.context`）

| 取值 | 行为 |
|---|---|
| `none`（默认） | `context = retrieved`（top-k） |
| `top_n` | `context = top-N`（E08） |
| `adjacent` | `context = top-k + 邻近块` |
| `builder` | `context = ContextBuilder(top-N).build(...)`（E09；预算/去重） |

相关字段：`context_budget_tokens`（预算，0=不限）、`context_max_chunks`（N）。

## 3. 契约与注意
- **复用 S4 既有实现**：`ContextBuilder` / `Context` / `ContextSegment`（未新造）。
- 截断只改块文本，**不改 `chunk.meta`（来源/行号/symbol）**，故证据映射与引用不受影响。
- `context`/`context_budget_tokens` 进 `config_hash`；`MyPipeline.name` 含 `context:builder`。
