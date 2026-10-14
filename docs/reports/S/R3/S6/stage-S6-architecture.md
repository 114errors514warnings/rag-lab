# rag-lab · S6 架构说明 · Evaluation 与自动化回归

> 报告：[`stage-S6-report.md`](stage-S6-report.md)

## 1. 组件与职责
| 组件 | 职责 | 文件 |
|---|---|---|
| runner | 加载套件/门禁 → 跑被测系统 → 算指标 → 对比冻结基线 → 出报告 + 退出码 | `rag_eval/runner.py` |
| gates | 判定规则（数据，非代码） | `rag_eval/gates.json` |
| run_gates.ps1 | L1 + L2 聚合门禁（CI 入口） | `scripts/run_gates.ps1` |
| baselines/ | 冻结基线（只增不改） | `baselines/*.json` |
| reports/ | 每次运行产物（json + md） | `reports/*` |

## 2. 回归流水线
```
run_gates.ps1
  ├─ pytest -q                          # L1 机制正确性
  └─ rag_eval.runner --stage S6 ...     # L2 全量回归（smoke_v1 + retrieval_v1）
        └─ 有任一 FAIL → 退出码 1（CI 红）
```

## 3. 关键契约
- 数据集冻结：运行时比对 `sha256`；与基线不一致直接 `FAIL (suite_sha256)`。
- 基线只读：`--freeze` 才写新基线文件。
- 判定取值：`PASS / FAIL / BASELINE / NO_GATE`。

## 4. 边界
- 延迟门限容忍 CI 抖动（10%~20% 容忍带 / 绝对上限）。
- 报告格式跨阶段一致：`.json`（含 per_case）+ `.md`（可贴）。
