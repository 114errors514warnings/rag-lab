# rag-lab · S4 阶段报告 · Context Engineering

- 阶段：S4（系统侧阶段四）｜轮次：R2
- 状态：✅ 完成（L1 + L2 通过，1 次通过）
- 日期：2026-10-11
- 架构说明：[`stage-S4-architecture.md`](stage-S4-architecture.md)

## 1. 目标
去重/相关性过滤、Context 压缩、Token Budget 分配、冲突/过期/低可信度处理、来源追踪；
固定预算下产出可追溯上下文，且质量不降、token 受控。

## 2. 交付物
| 文件 | 职责 |
|---|---|
| `rag_engine/context/builder.py` | `ContextBuilder`：去重 → 阈值过滤 → 按 source 每组至少 1 块 → 剩余按分填充 → 超预算截断（保留来源/定位）→ 标注 stale/low_trust |
| `rag_engine/context/__init__.py` | 导出 `Context / ContextBuilder / ContextSegment` |
| `rag_engine/generate/context_generator.py` | `ContextExtractiveGenerator`：经 Builder 组装上下文并标注 `chunk_id` 来源 |
| `tests/test_context_budget.py` | L1：预算上限、每文档下限、截断可追溯、删除记录、来源不丢 |

## 3. 测试方法
- L1：`python -m pytest -q` → **62 passed**（新增 5 项）。
- L2：`python -m rag_eval.runner --stage S4 --system demo_context --baseline S4__demo_dense`（retrieval_v1, k=5）

## 4. 结果
| 门禁 | 基线 | 本次 | Δ | 判定 |
|---|---|---|---|---|
| `citation_precision`（主） | 0.19 | 0.19 | +0.0000 | **PASS** |
| `avg_prompt_tokens`（护栏 ≤2000） | 260.4 | 260.4 | +0.0000 | **PASS** |

退出码 0。**1 次通过**。

说明：demo 语料块较短、预算 600 未触顶，故 token 未下降（Δ=0）；"压缩/裁剪后来源不丢"由 L1 `test_context_budget` 断言（超预算截断仍保留 `chunk_id` 与 `source`）。

## 5. 边界与不做
- 语义压缩（摘要式）留待接入 LLM 后作为观察项；当前为"去重 + 预算裁剪 + 标注"。
- `my_pipeline`（项目 kb）在 retrieval_v1 上因语料/标注不对齐不做 S4 主判定，沿用 demo 对齐系统。

## 6. 演进映射
- `code_rag/*`（S5）、`service/*`（S7）。
