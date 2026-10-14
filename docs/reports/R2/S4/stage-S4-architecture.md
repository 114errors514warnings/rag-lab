# rag-lab · S4 架构说明 · Context Engineering

> 报告：[`stage-S4-report.md`](stage-S4-report.md)

## 1. 组件与职责
| 组件 | 职责 | 文件 |
|---|---|---|
| ContextBuilder | 去重 → 阈值过滤 → 分组下限 → 预算填充 → 截断 → 标注 | `rag_engine/context/builder.py` |
| Context/ContextSegment | 可追溯的上下文结构（chunk_id/source/text/tokens/notes） | 同文件 |
| ContextExtractiveGenerator | 用上下文组装回答并标注来源 | `rag_engine/generate/context_generator.py` |

## 2. 预算分配算法（按序）
```
hits ──去重(chunk_id + 文本近似)──▶ 阈值过滤 ──▶ 按 source 分组
     ──每组至少 per_doc_min 块──▶ 剩余按 score 降序填充
     ──累计 tokens ≤ max_tokens；超则 _fit 截断（保留 chunk_id/source）──▶ Context
```

## 3. 关键契约
- `ContextBuilder.build(hits) -> Context{segments, tokens, dropped}`。
- `ContextSegment{chunk_id, source, text, tokens, score, notes}`；`notes ∈ {truncated, stale, low_trust}`。
- `ContextExtractiveGenerator.generate(question, retrieved) -> Generation`（`citations = [seg.chunk_id]`）。

## 4. 不变量（L1）
- `tokens ≤ max_tokens` 恒成立；
- 截断只截文本前缀，**chunk_id 与 source 保留**；
- 每个有命中的 source 至少 1 段（预算允许时）；
- `dropped` 记录被预算淘汰的 chunk_id。

## 5. 边界
- 标注为启发式（`updated_at` 比较、`trust<1`）；语义冲突留给 LLM 级处理（观察项）。
