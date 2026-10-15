# E 线总结 · RAG 实验（E00–E12）

> 依据《RAG 架构验证与性能优化实验手册》；系统本体为 S1–S7。**指标口径以 [`metrics-glossary.md`](metrics-glossary.md) 为准。**
> 一句话：**E00–E12 全部执行完毕；主要收益来自"更强的模型"（Embedding / Rerank），检索链路的花样（切块 / 稀疏 / 改写）在本套件上多为负结论。**

## 1. 总览

| 阶段 | 主变量 | 结果 | 状态 |
|---|---|---|---|
| E00 | 基线（固定块 + Dense Top-5） | `recall@5=0.8148`、trace 100% | ✅ 基线 |
| E01 | 解析器契约 | 召回持平 0.8148 | ✅ 通过 |
| E02 | 切块 512/80 | `recall@5` 0.8148→**0.8519** | ✅ 通过 |
| E03 | 符号级切块 | 0.5926→0.8148（3 次尝试），仍 < 0.8519 | ❌ 未通过 |
| E04 | Embedding `bge-m3` | `recall@5` 0.8519→**0.963** | ✅ 通过 |
| E04b | Embedding 模型对照 | Qwen3-0.6B ✅；`bge-large-zh/en` ❌ | ⚠️ 部分 |
| E05 | 检索模式（Dense/BM25/Hybrid） | **Dense 最优**；BM25/Hybrid 召回未过门禁 | ❌ 未通过 |
| E06 | Rerank + 拒答 | `mrr@5` **+0.0895**；`no_answer` **0→1.0** | ✅ 通过 |
| E06b | Rerank 模型对照 | Qwen3-Reranker-4B `mrr` 更高，但拒答未过 | ❌ 未通过 |
| E07 | Query Rewrite / Multi-query | 无增益（召回已饱和） | ❌ 未通过 |
| E08 | 上下文扩展（top-10） | `context_coverage` 0.963→**1.0** | ✅ 通过 |
| E09 | Context Budget | token 621→211；覆盖 1.0→0.889（权衡） | ✅ 通过 |
| E10 | 增量索引 | 改 1 文档仅重建 **7/111** 块 | ✅ 机制验证 |
| E11 | 多项目隔离 / 注入 | `leakage_rate=0`（负对照 FAIL） | ✅ 通过 |
| E12 | 服务化（HTTP） | 与进程内质量一致、隔离不破 | ✅ 通过 |

合计：**9 通过 · 4 未通过（E03/E05/E06b/E07）· 1 部分（E04b）**。

## 2. 关键结论（跨阶段）

1. **模型 > 链路**：最大收益来自换 Embedding（E04，`recall +0.111`）与加 Rerank（E06，`mrr +0.089`）；
   而"改切块 / 改稀疏融合 / 改多查询"（E03/E05/E07）**均无增益**。
2. **覆盖式 `recall@5` 偏好粗块**：一块越大越容易"包住"多段证据 → 天然不利于符号块、不利于稀疏候选竞争。
   这是 E03/E05 负结论的**结构性原因**（非实现 bug）。
3. **拒答需要比语义相似度更强的信号**：dense 余弦**无法分离**无答案题（E05 探测），**rerank 分数可分离**（E06）。
   且**阈值随 rerank 模型而变**（E06b：换 Qwen3-Reranker 后 0.05 失效）。
4. **"检索"与"上下文"要分开**：`recall@k`（检索 top-k）与 `context_evidence_coverage`（送进 LLM 的上下文）分离，
   因此 E08 能"召回不变、覆盖 0.963→1.0"，E09 能"牺牲覆盖换 token"。
5. **工程侧全线达标**：增量索引（E10）、多项目隔离（E11）、HTTP 服务化（E12）均通过，且**隔离经 HTTP 仍然成立**。

## 3. 负面结果清单（如实保留）

| 阶段 | 事实 | 归因（一句话） |
|---|---|---|
| E03 | 符号切块 3 次尝试（symbol / +模块 / ∪定长）均 < 定长 512 | 符号块更细，覆盖式召回吃亏 |
| E05 | BM25、Hybrid 召回不及 Dense | 强 Dense 下融合无增量；RRF 拉低覆盖 |
| E07 | 多查询无增益 | 召回已饱和（26/27），术语扩展无新命中 |
| E06b | Qwen3-Reranker 排序更强但拒答未过 | 拒答阈值不可跨模型迁移 |
| E04b | 单语言 embedding（zh/en）更差 | 查询全中文 + 中文问英文代码，跨语言吃亏 |

## 4. 开放项（未做 / 待立项）

1. **口径复核（S 侧）**：扩套件（更大、更难、含**英文查询**）后，重估 E03/E05/E07 的价值；当前结论受小套件限制。
2. **两套代码语料并存**：主库 `data/kb`（proj-auth/sched）与 `/symbol` 用的 `data/code_corpus`（proj-alpha/beta）未统一。
3. **Docker 未实跑**：本机无守护；`Dockerfile`/`compose.yaml` 已就绪，命令见 E12 测试方案。
4. **真实 LLM 注入防护**：当前无 LLM，注入无法接管；接 LLM 后需加"系统提示与用户内容隔离"。
5. **阈值/参数未网格**：`rrf_k`、`rerank_candidates`、拒答阈值、切块网格等按预声明值固定，未做调参。

## 5. 复现

```powershell
python -m pytest -q                                   # L1（116 项）
$env:SILICONFLOW_API_KEY = "<key>"                    # 密钥仅环境变量，不入库
python scripts/run_eval.py --config configs/E06_rerank.yaml --baseline <run_id>
python scripts/exp_e10_incremental.py                 # E10 机制基准（离线）
```
