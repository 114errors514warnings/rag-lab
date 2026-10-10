# RAG 工程骨架 · Project Knowledge Engine

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
| L1 功能测试 | ✅ `tests/`（45 项，`python -m pytest`） |
| M1–M8 / 阶段二~七 | ⬜ 按 `docs/guide/implementation-plan.md` 与实验手册推进 |

## 目录结构

```
docs/
  guide/                      # 教学与规范（跨轮次长期有效）
    implementation-plan.md    #   系统侧总纲（旧计划 S1–S7）
    stage-gates.md            #   固定测试方法说明
    records-convention.md     #   记录约定与索引
  reports/                    # 逐轮次报告（按实验轮次分阶段）
    R0/round-0.md             #   R0 · 平台化基线（已冻结）
    R0/diagrams/              #     round-0 架构图（Archify 生成）
    R1/  R2/  R3/             #   后续轮次
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

## 下一步（M1）

> 路线见 `docs/guide/implementation-plan.md`；实验记录见 `docs/reports/R0/round-0.md`。

1. **M1 解析与切块**：`ingest/clean.py`、切块模式（token/层级）、代码 AST 符号索引（为 E01–E03）；`configs/E01–E03.yaml`。
2. **M3 之前**：确定真实 Embedding（本地/API）与 tokenizer，否则 E04 无法真跑 A/B。
3. **M5 之前**：补拒答与 LLM 裁判（当前 `no_answer_accuracy=0`、`answer_accuracy` 为代理口径）。
4. 每个实验：改一个主变量 → 跑 L1 → 跑运行器 → 看配对 CI（跨 0 记"证据不足"）→ 写 `round-N.md`。
