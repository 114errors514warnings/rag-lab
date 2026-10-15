# RAG 工程骨架 · Project Knowledge Engine

> 学习实践项目关联集：`实践项目合集/rag-lab` + `实践项目合集/agent-runtime`（后续同类项目并入）。
> **进度评估只看关联集**；实现过程可借鉴其它无关项目（不计入进度）。

两条线合流：**系统本体（`rag_engine`，旧七阶段计划）** + **实验平台（`rag_lab`，新实验手册 E00–E12）**。前者是"被测系统"，后者做"单变量对照 + 归因 + 显著性"。

## 当前状态

| 部分 | 状态 |
|---|---|
| 方法论归档 | ✅ `RAG阶段性实践清单.md`（旧计划原文） |
| 分阶段实现总纲 | ✅ `docs/guide/implementation-plan.md`（旧计划 S1–S7） |
| 固定测试方法（评测协议） | ✅ `docs/guide/stage-gates.md` |
| **RAG 系统本体 · 阶段一** | ✅ `rag_engine/`（离线 hashing-tfidf + numpy 向量库 + dense 检索 + 带引用生成；多项目隔离；PDF/OpenAI 可选） |
| **实验平台 · M0** | ✅ `rag_lab/` + `scripts/`（快照 / Golden v2 / Trace / 配置驱动运行器 / 配对 bootstrap） |
| 评测协议 v2 | ✅ 证据制（`gold_evidence` 行区间/symbol），新增 nDCG、证据覆盖、拒答、宏微平均 |
| **E00 基线** | ✅ `recall@5=0.8148`、`trace=100%`（详见 `docs/reports/E/E00/` 与 `docs/reports/S/R0/round-0.md`） |
| L1 功能测试 | ✅ `tests/`（116 项，`python -m pytest`） |
| **系统本体 · 阶段二~七（S2–S7）** | ✅ 已全部达标（S3 经"查询改写+IDF 重排"达标；详见 `docs/reports/S/`） |
| 实验线 E00–E12 | ✅ **全部执行完成**（9 通过 / 4 未通过 / 1 部分；指标口径见 `docs/reports/E/metrics-glossary.md`；总结见 `docs/reports/E/summary.md`） |
| **Agent Runtime 线 A01–A10** | ⬜ 规划已归档（`docs/guide/agent-runtime-plan-A01-A10.md`）；综合路线图见 `docs/guide/roadmap-merged.md` |

## 目录结构

```
docs/
  guide/                      # 教学与规范（跨轮次长期有效）
    implementation-plan.md    #   系统侧总纲（旧计划 S1–S7）
    experiment-plan-E01-E12.md#   RAG 实验线 E01–E12 计划与测试标准
    stage-gates.md            #   固定测试方法说明
    records-convention.md     #   记录约定与索引
    roadmap-merged.md         #   综合路线图（S/E/T/A 合流）
    agent-runtime-plan-A01-A10.md  # Agent Runtime 线计划
    统一开发准则.md            #   关联集统一约束（汇报 / 只增不改 / 文档边界）
  reports/                    # 文档报告：S / E 两棵树（总索引 reports/README.md）
    README.md                 #   报告总索引
    S/                        #   S 计划：按 R 轮次（R0–R3）
      R0/ … R1/ … R2/ … R3/   #     每轮：round-N.md + <S阶段>/stage-S*-{report,architecture}.md
    E/                        #   E 计划：按 E 阶段（E00–E12）
      E00/ E01/ E02/ E03/     #     每阶段：stage-E*-{report,architecture}.md
rag_engine/                   # 被测系统（Indexing / Retrieval / Answering）
rag_eval/                     # 固定评测内核（schema / metrics / evidence / sut）
rag_lab/                      # 实验平台（config / golden / scoring / trace）
scripts/
  snapshot.py                 #   数据快照（文件 sha256 + 排除规则）
  run_eval.py                 #   实验运行器（E00–E12，配对对照）
configs/E00.yaml              #   固定基线配置
data/kb/                      #   知识库：proj-auth / proj-sched + 文档集（多项目隔离）
data/golden/cases.jsonl       #   Golden Dataset v2（证据制）
snapshots/  traces/           #   快照与逐阶段 trace
reports/{run_id}/             #   metrics.json / cases.jsonl / errors.csv / comparison.md
tests/                        # L1 功能测试（pytest）
baselines/*.json              # 早期冻结基线（只写不改）
```

## 跑一次实验

```powershell
# L1：机制正确性
python -m pytest -q

# 数据快照
python scripts/snapshot.py --root data/kb --name kb

# E00 基线
python scripts/run_eval.py --config configs/E00.yaml

# 与基线做 A/B 配对（bootstrap 95% CI）
python scripts/run_eval.py --config configs/E0x.yaml --baseline <E00_run_id>
```

产物：`reports/{run_id}/`（含 `comparison.md` 可直接贴报告）与 `traces/{run_id}.jsonl`。门槛 `FAIL` 时退出码为 `1`。

## 三条线与当前进度

```
RAG 系统线 S1–S7（✅ 已达标） ┐
RAG 实验线 E00–E12（✅ 已执行完成）┴─▶ Project Knowledge Engine（✅ 含 MCP 工具面）
                                              │
                                              ▼
                       Tool Calling / Tool Executor（agent-runtime，关联集内，已检出）
                                              │
                                              ▼
                       Agent Runtime A01–A10（⬜ 0/10）
```

- 新计划（A01–A10）：`docs/guide/agent-runtime-plan-A01-A10.md`（原文 `docs/guide/assets/…docx`）
- 综合路线图（S/E/T/A 合流、现状盘点、里程碑、复用映射、下一步）：`docs/guide/roadmap-merged.md`
- **E 线总结**（结论 / 负面结果 / 开放项）：`docs/reports/E/summary.md`

## 下一步（启动 A 线）

> E 线已收官（`docs/reports/E/summary.md`）；综合路线图见 `docs/guide/roadmap-merged.md`。

1. 在 `agent-runtime`（关联集内独立仓库，已本地检出）按手册推进 **A01–A10**：M1（A01–A03）→ M2（A04–A06）→ M3（A07–A09）→ M4（A10）；其前置 Tool Calling / Executor 见该仓库自身文档。
2. 复用本仓库的评测纪律（固定套件 / 预声明门禁 / run_id 报告）与 RAG Tool 接口（`search_project`/`get_symbol`/`read_context`）。
3. E 线遗留开放项见 `docs/reports/E/summary.md` §4（口径复核、两套代码语料统一、Docker、LLM 注入防护）。
