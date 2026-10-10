# RAG 工程骨架 · Project Knowledge Engine

基于《RAG阶段性实践清单》的落地工程：**一条固定流水线 + 七道验收门禁 + 单一 Baseline 对照**（不是七个孤立 Demo）。

## 当前状态

| 部分 | 状态 |
|---|---|
| 方法论归档 | ✅ `RAG阶段性实践清单.md`（文档原文，含 4 条实践原则与七阶段验收项） |
| **分阶段实现与统一硬性测试总纲** | ✅ 已落档 → 见 `docs/implementation-plan.md`（每阶段交付物 + L1/L2/L3 三层测试 + 阶段×测试矩阵） |
| **固定测试方法（评测协议）** | ✅ 已落地并可运行 → 见 `docs/stage-gates.md` |
| RAG 系统本体（解析/切块/索引/检索/生成） | ⬜ 待落地（阶段一） |
| 门禁表接入真实系统 | ⬜ 系统落地后按同一命令跑 |

## 目录结构

```
docs/implementation-plan.md   # 分阶段实现 + 统一硬性测试总纲（本工程的主计划）
docs/stage-gates.md          # 固定测试方法：每阶段跑什么、怎么判、报告长什么样
rag_engine/                   # RAG 系统本体（待落地，与 rag_eval 解耦）
tests/                        # L1 功能测试（待落地，pytest）
scripts/run_gates.ps1         # L1+L2 一条命令跑完并聚合退出码（待落地）
rag_eval/                     # 固定评测协议（与 RAG 实现解耦）
  schema.py                  # 用例/答案/报告的字段契约
  metrics.py                 # 指标口径（改口径必须 bump EVAL_VERSION）
  gates.json                 # 判定规则（主指标 + 护栏），数据驱动
  runner.py                  # 运行器：一条命令 → 报告 + 退出码
  sut/                       # 被测系统接入层（stub_* 仅用于协议自检）
data/eval_suites/*.jsonl      # 冻结的测试套件（带 sha256 校验）
data/corpus/demo.jsonl        # 演示语料（含干扰项）
baselines/*.json              # 冻结的基线数值（只写不改）
reports/*.json|*.md           # 每次运行的报告
```

## 跑一次评测

```powershell
python -m rag_eval.runner --stage S1 --system stub_dense --freeze
python -m rag_eval.runner --stage S3 --system stub_hybrid --baseline S3__stub_dense
```

有任一 `FAIL` 时退出码为 `1`，可直接作为 CI 门禁。报告写入 `reports/`（`.md` 可直接贴进阶段报告）。

## 下一步

> 完整路线见 `docs/implementation-plan.md`（按阶段给交付物、L1/L2/L3 测试与 DoD）。

1. 落地阶段一：实现 `Chunker / Embedder / Retriever / Generator`，在 `rag_eval/sut/__init__.py` 的 `REGISTRY` 注册为真实系统。
2. 用真实语料替换 `data/corpus/demo.jsonl`，编写你自己项目的 `smoke_v1` 套件（阶段一可先无标注，阶段三之前必须补 `relevant_chunk_ids`）。
3. 跑 `--stage S1 --freeze` 产出第一个基线数值，之后每完成一个阶段跑同一条命令对比。
