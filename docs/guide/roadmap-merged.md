# 综合路线图 · RAG（S/E）→ Tool Calling（T）→ Agent Runtime（A）

> 目的：把三条线合成**一条依赖链**，给出**当前进度定位**与**可直接落地的下一步**。
> 依据：`RAG阶段性实践清单.md`（阶段1–7）、`docs/guide/implementation-plan.md`（S1–S7）、
> `docs/guide/stage-gates.md`、`rag_lab/`（E00–E12 实验线）、`docs/guide/agent-runtime-plan-A01-A10.md`（A01–A10）。

## 评估口径（先明确）

- 本路线服务于**学习实践项目关联集**：`rag-lab` + `agent-runtime`（后续同类项目并入同一关联集）。
- **进度评估只看关联集**：判断"前置是否具备、计划完成到哪一步"时，仅计入关联集内项目。
- **关联集之外的项目与本项目无任何关联**：实现过程中**允许借鉴**其思路或代码，但这只是过程行为，
  **不产生关联，也不在文档中提及**（不出现其名称/路径/链接）。见《统一开发准则》§四。

## 0. 结论摘要

1. **新计划不含旧计划内容 → 需要综合计划（即本文件）。**
   A 手册原文："实验编号 A01–A10 为新增编号，**不覆盖原有 E00–E12**"，且明确**前置条件**为"已完成的 RAG 项目知识库与 Tool Calling/Tool Executor"。
   即 A 线依赖 S/E/T 线，三者是**串联**关系，不是一个可以互相替代的集合。
2. **当前进度定位**（关联集口径）：
   - RAG 系统线（S1–S7）：**已全部达标**（本仓库，L1 87 项 + 各阶段门禁 exit 0）。
   - RAG 实验线（E00–E12）：**E00/E01/E02 完成**；E03 未通过（记录在案）；E04–E12 未做。
   - **Tool Calling / Tool Executor：由 agent-runtime 的 M0（T01–T03）补齐**。
   - Agent Runtime 线（A01–A10）：**0/10 未开始**。

## 0.1 前置条件核对（**关联集口径**）

| 前置条件 | 关联集内来源 | 状态 |
|---|---|---|
| Python 工程基础 | rag-lab / agent-runtime | ✅ 两个 pytest 工程 |
| 模型 API | 关联集内**默认离线** | 🟡 接口已留、未启用 |
| 结构化 Tool Schema / Executor | agent-runtime · M0 | ✅ `src/tools/{spec,registry,executor}.py` |
| 可调用的 RAG 检索接口 | rag-lab · S7 | ✅ `service/api.py` + MCP 三工具 |

> 结论：四项前置中 3 项已具备、1 项（真实模型 API）为"可选项待启用"。A01 可先用**可插拔 LLM + 离线 FakeLLM**
> 验证 Loop 机制，再按需接入真实模型 API。

## 0.2 计划完成情况（**关联集口径**）

| 线 | 范围 | 完成度 |
|---|---|---|
| RAG 系统线 | S1–S7 | ✅ **7 / 7** |
| RAG 实验线 | E00–E12 | 🟡 **3 / 13**（E00/E01/E02；E03 未通过） |
| Tool Calling | T01–T03 | ✅ **3 / 3**（M0） |
| Agent Runtime | A01–A10 | ⬜ **0 / 10** |

里程碑：**M0 ✅**；**M1(A01–A03) / M2(A04–A06) / M3(A07–A09) / M4(A10) ⬜**。

## 1. 三条线的依赖链

```
[RAG]  S1–S7 系统线  ─┐
       E00–E12 实验线 ─┴─▶ Project Knowledge Engine（含 RAG 检索工具面）
                                   │
                                   ▼
[Tool Calling]  T01–T03  Tool Schema / Executor   （agent-runtime · M0）
                                   │
                                   ▼
[Agent Runtime] A01 → A02 → A03 → A04 → A05 → A06 → A07 → A08 → A09 → A10
```

## 2. 按 A 手册框架的现状盘点（仅关联集）

| 阶段 | 手册要求 | 现状 | 关联集内可复用 | 缺口 |
|---|---|---|---|---|
| 前置 | Tool Schema / Executor | ✅ M0 已补齐 | agent-runtime `src/tools/`（ToolSpec/Registry/Executor） | 与模型循环对接 |
| A01 | Agent Loop / ReAct | ❌ 未开始 | agent-runtime 工具执行器；rag-lab 检索工具 | 决策→工具→观察→停止循环、步数/预算护栏 |
| A02 | Workflow / 状态机 | ❌ 未开始 | rag-lab pipeline（线性流程） | 显式状态转移表 / 守卫 / DAG / 审批节点 |
| A03 | State / Checkpoint | ❌ 未开始 | agent-runtime 审计 trace；rag-lab 快照 | 关键节点 checkpoint、断点恢复、幂等性 |
| A04 | Runtime / 调度 | ❌ 未开始 | — | 任务队列、并发限制、取消/超时、饥饿与资源指标 |
| A05 | Agent Registry / 生命周期 | ❌ 未开始 | agent-runtime Tool Registry（注册/版本/权限范式） | `AgentSpec(id/version/role/model/tools/permissions)`、热更新、权限隔离 |
| A06 | Skill / Tool Registry | 🟡 局部 | agent-runtime Tool Registry（Schema/权限/审计） | SkillSpec、版本兼容、能力发现 |
| A07 | Memory + RAG 集成 | 🟡 局部 | rag-lab RAG + `context/builder.py` 预算 | session/project/agent 三层 Memory、串库率评测 |
| A08 | Retry / Rollback | 🟡 局部 | agent-runtime Executor（错误分类 `retryable`）；rag-lab 索引自愈 | 退避重试、幂等键、**补偿/回滚** |
| A09 | Multi-Agent 协作 | ❌ 未开始 | — | Director/Worker/Verifier、消息总线、冲突仲裁 |
| A10 | 综合 Runtime 集成 | ❌ 未开始 | rag-lab 评测协议（固定套件/门禁/报告） | 30–50 Golden Tasks、消融矩阵、部署演示 |

> 图例：❌ 未开始 ｜ 🟡 有可复用基础但未按 A 要求实现 ｜ ✅ 已达标。

## 3. 前置缺口：补一条 Tool Calling（T）线

A 手册把"Tool Schema / Executor"当作**已存在**的前置；关联集内由 **agent-runtime · M0（T01–T03）** 补齐。

| 编号 | 主题 | 交付 | 验收 |
|---|---|---|---|
| **T01** | ToolSpec / Schema 与注册 | `src/tools/`：`ToolSpec(schema, side_effect, sandbox, timeout, version)`；注册与发现 | Schema 校验覆盖；非法参数被拒 |
| **T02** | Tool Executor | 统一执行器：沙箱、`dry-run`、超时、**调用审计** | 越权/危险调用被拦截并记录；trace 可回放 |
| **T03** | 与 RAG 工具对接 | `search_project/get_symbol/read_context` + `run_test` 接入执行器 | 端到端：模型→工具→观察→记录 |

统一观测字段：`run_id, task_id, agent_id, step_id, tool_name, input_hash, latency_ms, tokens_in/out, cost_estimate, status, error_type, trace_id`。

## 4. 综合里程碑（可落地执行顺序）

| 里程碑 | 覆盖 | 依赖 | 出口判据 |
|---|---|---|---|
| **M0 前置** | T01–T03 | RAG 工具已就绪（✅） | 工具执行器可用、审计可回放、RAG 工具被真实调用 |
| **M1** | A01–A03 | M0 | 单 Agent Loop 无死循环、预算可终止；工作流三类路径自动测试通过；checkpoint 恢复一致、无重复副作用 |
| **M2** | A04–A06 | M1 | 并发限制有效、取消释放资源；Agent 权限互不串用；非法/越权调用被拒并记录 |
| **M3** | A07–A09 | M2 | 三层 Memory 与 RAG 打通、串库率 = 0；重试/回滚无静默污染；多 Agent 消息含关联 ID、冲突有仲裁 |
| **M4** | A10 | M3 | 30–50 Golden Tasks 可复测；单/多 Agent、带/不带 RAG、带/不带恢复的消融矩阵与报告 |

## 5. 现在应做的下一步

1. **先完成 RAG 实验线**（E03 修复 → E04…E12），它是 A 线 A07（Memory+RAG）的前置。
2. 随后按 A 线 M1（A01–A03）→ M2（A04–A06）→ M3（A07–A09）→ M4（A10）推进。
3. 每阶段：**写模块 → L1 → L2 门禁 → 两份文档（报告 + 架构说明）→ 重要阶段 Archify 图**；
   测试未通过先停下汇报（见《统一开发准则》）。

## 6. 决策点

A 手册建议目录（`src/runtime/ src/agents/ src/registry/ src/memory/ src/tools/ src/evaluation/ experiments/a01…a10/`）
已在 `agent-runtime` 落地为独立仓库（与 `rag-lab` 同级，位于 `实践项目合集/`）。后续实验在该仓库内推进。
