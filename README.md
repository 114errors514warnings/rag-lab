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
| **E00 基线** | ✅ `recall@5=0.8148`、`trace=100%`（详见 `docs/reports/R0/round-0.md`） |
| L1 功能测试 | ✅ `tests/`（92 项，`python -m pytest`） |
| **系统本体 · 阶段二~七（S2–S7）** | ✅ 已全部达标（S3 经"查询改写+IDF 重排"达标；详见 `docs/reports/R1..R3/`） |
| 实验线 E01–E12 | 🟡 E00/E01/E02 ✅；**E03 未通过（待修）**；E04–E12 ⬜（计划见 `docs/guide/experiment-plan-E01-E12.md`） |
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
  reports/                    # 逐轮次报告（按实验轮次分阶段）
    R0/round-0.md + architecture.md   # R0 · 平台化基线（已冻结）
    R0/diagrams/              #     round-0 架构图
    R1/round-1.md + stage-* 报告/架构 # R1 · 解析/切块/召回（进行中）
    R2/  R3/                  #   后续轮次
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
RAG 实验线 E00–E02 ✅ / E03 ❌ / E04–E12 ⬜ ┴─▶ Project Knowledge Engine（✅ 含 MCP 工具面）
                                              │
                                              ▼
                       Tool Calling / Tool Executor（❌ 本工作区未找到 → A 线前置缺口）
                                              │
                                              ▼
                       Agent Runtime A01–A10（⬜ 0/10，有新计划）
```

- 新计划（A01–A10）：`docs/guide/agent-runtime-plan-A01-A10.md`（原文 `docs/guide/assets/…docx`）
- 综合路线图（S/E/T/A 合流、现状盘点、里程碑、复用映射、下一步）：`docs/guide/roadmap-merged.md`

## 下一步（先闭环 RAG 实验线）

> 依据 `docs/guide/roadmap-merged.md` §5：E 线是 Agent 线 A07（Memory + RAG）的前置，**先完成 E 线**。
> 记录约定见 `docs/guide/records-convention.md`；本轮快照见 `docs/reports/R1/round-1.md`。

1. **修复 E03**（当前唯一未闭环实验）：为代码文件补"模块剩余块"（`kind="module"`）或采用定长∪符号并集，复测转绿（详见 `docs/reports/R1/stage-E03-report.md` §5）。
2. **E05 优先于 E04**：接入 `system.retrieval`（Dense / BM25 / Hybrid）+ `min_relevance` 拒答，不依赖外部模型，顺带修 `no_answer_accuracy=0`。
3. **E04**：待定"本地模型 / API / 暂保持离线（记 `BASELINE`）"后再做。
4. E 线收敛后启动 T/A 线；`agent-runtime`（关联集内独立仓库）**本工作区未检出**，需先确认其位置或决定承载方式。
