# E11 架构说明 · 多项目隔离与泄漏门禁

> 报告：[`stage-E11-report.md`](stage-E11-report.md)

## 1. 链路

```
EvalCase.project_id ──(isolation=true)──▶ pipeline.answer(project_id)
                                              │  检索 flt={"project_id": project_id}
                                              ▼
                                        只返回本项目块
   （isolation=false 时忽略 project_id → 跨项目检索 → leakage>0）
```

## 2. 组件与契约
| 组件 | 文件 | 说明 |
|---|---|---|
| `EngineConfig.isolation` | `config.py` | on=按 project 过滤（默认）；off=对照 |
| 适配层应用 | `eval_adapter.py` | `project_id = case.project_id if isolation else None` |
| 泄漏度量 | `rag_lab/scoring.py::_leakage` | 检索块中 `project_id != case.project_id` 的占比；聚合为 `leakage_rate` |

## 3. 安全回归（L1，`tests/test_security.py`）
- 泄漏度量：跨项目块 → 0.5；全同项目 → 0.0；无 project → None。
- 检索过滤：`store.search(flt={"project_id": ...})` 只返回该项目块。
- 注入：注入文本被当**数据**（行为确定、只引用证据），不改控制流。

## 4. 边界
- 无 LLM ⇒ 注入不能接管；接真实 LLM 后需另加提示隔离防护。
- `project_id` 是最粗隔离边界；细粒度权限未做。
