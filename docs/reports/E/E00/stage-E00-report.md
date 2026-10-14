# E00 阶段报告 · 基线（固定块 + Dense Top-5）

- 实验：E00（E 计划第一个阶段）
- 状态：✅ 基线建立（Trace 完整率 1.0）
- 日期：2026-10-09（首跑）/ 2026-10-14（复核）
- 配置：`configs/E00.yaml`
- 系统：`my_pipeline`（离线 hashing-tfidf + numpy 向量库 + dense 检索 + 抽取式带引用生成）
- 数据集：`data/golden/cases.jsonl`（32 题，证据制）
- run_id：`20261009T155134_E00_e821df85555c_nogit_df5eb069a83579d2_626aa1732b4f8e12`

## 1. 目标
建立"可重放、可核对"的基线：固定块 + 单路 Dense Top-5、无重排；完成 100% Trace。

## 2. 指标（基线数值）
| 指标 | 值 | 说明 |
|---|---|---|
| `recall@5` | 0.8148 | 覆盖式：至少一组充分证据被前 5 覆盖 |
| `precision@5` | 0.3475 | 前 5 中命中证据的比例 |
| `mrr@5` | 0.7840 | 首个命中名次倒数 |
| `ndcg@5` | 0.8965 | 0/1/2 等级 |
| `context_evidence_coverage` | 0.8148 | 最终上下文覆盖 |
| `answer_accuracy` | 0.6875 | rubric 代理（召回覆盖 且 有引用） |
| `no_answer_accuracy` | 0.0 | **拒答机制缺失（已知缺口）** |
| `citation_support` | 0.3475 | 引用命中证据比例 |
| `p95_latency_ms` | 0.379 | 离线，无网络/LLM |
| `trace_completeness` | 1.0 | 全部 case 有召回记录 |

## 3. 复现
```powershell
python scripts/snapshot.py --root data/kb --name kb
python scripts/run_eval.py --config configs/E00.yaml
```

## 4. 归属说明
E00 的"轮次级背景"（实验平台 / Golden v2 / Trace 的建设）记录在 **S 计划**的轮次记录
[`../../S/R0/round-0.md`](../../S/R0/round-0.md) 中；**本文件是 E 计划下 E00 的独立阶段记录。**
架构说明见 [`stage-E00-architecture.md`](stage-E00-architecture.md)。
