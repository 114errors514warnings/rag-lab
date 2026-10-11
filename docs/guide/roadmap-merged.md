# 综合路线图 · RAG（S/E）→ Tool Calling（T）→ Agent Runtime（A）

> 目的：把三条线合成**一条依赖链**，给出**当前进度定位**与**可直接落地的下一步**。
> 依据：`RAG阶段性实践清单.md`（阶段1–7）、`docs/guide/implementation-plan.md`（S1–S7）、
> `docs/guide/stage-gates.md`、`rag_lab/`（E00–E12 实验线）、`docs/guide/agent-runtime-plan-A01-A10.md`（A01–A10）。

## 评估口径（先明确）

- 本路线服务于**学习实践项目关联集**：`rag-lab` + `agent-runtime`（后续同类项目并入同一关联集）。
- **进度评估只看关联集**：判断"前置是否具备、计划完成到哪一步"时，仅计入 `rag-lab` 与本项目。
- **实现可跨项目借鉴**：实验实现时可以复用无关项目（ContextOptimizer / AI Drama / HIL 等）的资产，
  但**不计入关联集进度**（§5 的"复用映射"因此标注为"可借鉴、非本关联集进度"）。

## 0. 结论摘要

1. **新计划不含旧计划内容 → 需要综合计划（即本文件）。**
   A 手册原文："实验编号 A01–A10 为新增编号，**不覆盖原有 E00–E12**"，且明确**前置条件**为"已完成的 RAG 项目知识库与 Tool Calling/Tool Executor"。
   即 A 线依赖 S/E/T 线，三者是**串联**关系，不是一个可以互相替代的集合。
2. **当前进度定位**：
   - RAG 系统线（S1–S7）：**已全部达标**（本仓库，L1 77 项 + 各阶段门禁 exit 0）。
   - RAG 实验线（E00–E12）：**仅 E00 基线**；E01–E12 未做。
   - **Tool Calling / Tool Executor：在本工作区未找到**（HIL 只"暴露" MCP 工具、ContextOptimizer 只统计工具数并接收工具结果反馈，都不是 Executor）。
   - Agent Runtime 线（A01–A10）：**0/10 未开始**；但有可复用资产（见 §5）。

## 1. 三条线的依赖链

```
[RAG]  S1–S7 系统线  ─┐
       E00–E12 实验线 ─┴─▶ Project Knowledge Engine（已交付，含 MCP 工具面）
                                   │
                                   ▼
[Tool Calling]  T01–T03  Tool Schema / Executor   ← A 线的前置条件（当前缺口）
                                   │
                                   ▼
[Agent Runtime] A01 → A02 → A03 → A04 → A05 → A06 → A07 → A08 → A09 → A10
```

## 2. 按 A 手册框架的现状盘点

| 阶段 | 手册要求 | 现状 | 可复用资产 | 缺口 |
|---|---|---|---|---|
| 前置 | Tool Schema / Executor | ❌ 未见 | HIL：MCP 四工具（工具**面**而非执行器）；ContextOptimizer：工具结果反馈端点 | 真正的工具**执行器**与调用循环 |
| A01 | Agent Loop / ReAct | ❌ 未开始 | ContextOptimizer 的 provider/计量层可作模型调用底座 | 决策→工具→观察→停止循环、步数/预算护栏 |
| A02 | Workflow / 状态机 | 🟡 概念近似 | AI Drama 导演流程（固定阶段）；rag-lab pipeline | 显式状态转移表 / 守卫 / DAG / 审批节点 |
| A03 | State / Checkpoint | 🟡 局部 | AI Drama `session.json`/`turns.jsonl`/`side_chats` 持久化；ContextOptimizer SQLite | 关键节点 checkpoint、断点恢复、幂等性 |
| A04 | Runtime / 调度 | 🟡 局部 | AI Drama `RuntimeManager`（create/pause/resume/destroy） | 任务队列、并发限制、取消/超时、饥饿与资源指标 |
| A05 | Agent Registry / 生命周期 | 🟡 **强近似** | AI Drama `AgentRegistry` + `RuntimeManager` + `to_dict()` 状态；HIL 注册表 | `AgentSpec(id/version/role/model/tools/**permissions**)`、热更新、权限隔离 |
| A06 | Skill / Tool Registry | 🟡 局部 | HIL `@mcp.tool()` 注册与 schema；ContextOptimizer `providers.py` 抽象 | SkillSpec/ToolSpec、版本、**权限拦截**、调用审计 |
| A07 | Memory + RAG 集成 | 🟡 局部 | AI Drama 记忆管理器/长期记忆/隔离；rag-lab RAG + `context/builder.py` 预算 | 三层 Memory（session/project/agent）与 RAG 打通、串库率评测 |
| A08 | Retry / Rollback | 🟡 局部 | ContextOptimizer 重试升级 + 预算 + 反馈闭环；rag-lab 索引自愈；AI Drama 世界校验修正 | 错误分类、退避、幂等键、**补偿/回滚** |
| A09 | Multi-Agent 协作 | 🟡 **强近似** | AI Drama 多 Agent（导演/世界/记忆/梗概/角色）+ 每轮调用图 | Director/**Worker**/**Verifier** 角色分工、消息总线、冲突仲裁 |
| A10 | 综合 Runtime 集成 | ❌ 未开始 | rag-lab 评测协议（固定套件/门禁/报告）；ContextOptimizer 观测字段 | 30–50 Golden Tasks、消融矩阵、部署演示 |

> 图例：❌ 未开始 ｜ 🟡 有可复用基础但未按 A 要求实现 ｜ ✅ 已达标。

## 3. 前置缺口：补一条 Tool Calling（T）线

A 手册把"Tool Schema / Executor"当作**已存在**的前置；但本工作区里它并不存在，必须补齐，否则 A01 无从落地。

| 编号 | 主题 | 交付 | 验收 |
|---|---|---|---|
| **T01** | ToolSpec / Schema 与注册 | `src/tools/`：`ToolSpec(name, schema, side_effect, sandbox, timeout, version)`；注册与发现 | Schema 校验覆盖；非法参数被拒 |
| **T02** | Tool Executor | 统一执行器：沙箱目录、`dry-run`、超时、重试、**调用审计**（统一观测字段） | 越权/危险调用被拦截并记录；trace 可回放 |
| **T03** | 与 RAG 工具对接 | 把 rag-lab 的 `search_project/get_symbol/read_context` + `run_test` 包装成 Tool 并接入执行器 | 端到端：模型发起工具调用→执行→观察→记录 |

统一观测字段（沿用 A 手册）：`run_id, task_id, agent_id, step_id, tool_name, input_hash, latency_ms, tokens_in/out, cost_estimate, status, error_type, trace_id`。
> 注：ContextOptimizer 已实现其中的 `request_id/provider/model/effort/tokens/cost/latency/success/error_type/routed_reason` 等，可直接复用其 SQLite 计量与 `/metrics` 观测面。

## 4. 综合里程碑（可落地执行顺序）

| 里程碑 | 覆盖 | 依赖 | 出口判据 |
|---|---|---|---|
| **M0 前置** | T01–T03 | RAG 工具已就绪（✅） | 工具执行器可用、审计可回放、RAG 工具被真实调用 |
| **M1** | A01–A03 | M0 | 单 Agent Loop 无死循环、预算可终止；工作流三类路径自动测试通过；checkpoint 恢复一致、无重复副作用 |
| **M2** | A04–A06 | M1 | 并发限制有效、取消释放资源；Agent 权限互不串用；非法/越权调用被拒并记录 |
| **M3** | A07–A09 | M2 | 三层 Memory 与 RAG 打通、串库率 = 0；重试/回滚无静默污染；多 Agent 消息含关联 ID、冲突有仲裁 |
| **M4** | A10 | M3 | 30–50 Golden Tasks 可复测；单/多 Agent、带/不带 RAG、带/不带恢复的消融矩阵与报告 |

每一阶段沿用本仓库已固化的**三层测试纪律**（机制单测 → 阶段门禁 → 真实客户端冒烟）与**记录约定**（每阶段 `report.md` + `architecture.md`，重要阶段配 Archify 架构图）。

## 5. 已有资产复用映射（避免重复造轮子 · **可借鉴，非本关联集进度**）

> 下表项目**不属于**学习实践关联集；仅为**实现时参考/借鉴**，不构成 `rag-lab`+`agent-runtime` 的完成度。

| 现有项目 | 直接可复用到 | 说明 |
|---|---|---|
| **rag-lab** | A 线的 Project Knowledge Engine、T03 的 RAG 工具、A10 的评测协议 | 已有 `search_project/get_symbol/read_context`（MCP+FastAPI）、固定套件/门禁/报告格式、`context/builder.py` 预算 |
| **ContextOptimizer** | A01 的模型调用层、A08 的重试/升级、统一观测字段 | provider 抽象、多信号路由、预算、`/v1/feedback` 闭环、SQLite 计量与 `/metrics`、`X-Gateway-*` 头 |
| **模拟群聊对话（AI Drama）** | A04/A05/A09/A07 的概念与部分代码 | `AgentRegistry`+`RuntimeManager` 生命周期、多 Agent 编排与调用图、记忆管理器与世界观隔离 |
| **HIL** | A06 的 Tool 注册范式、A07 的检索记忆 | `FastMCP` `@mcp.tool()` 注册与 schema、stdio 端到端测试、项目索引与记忆 |

## 6. 现在应做的下一步（M0）

1. **确定承载仓库**（见 §7 决策点）。
2. 落地 `src/tools/`：`ToolSpec` + `Executor`（沙箱/dry-run/超时/审计），并写 L1 测试。
3. 把 rag-lab 的三个检索工具 + `run_test` 包成 Tool，跑一次"模型→工具→观察"端到端（可先用确定性 FakeLLM，沿用 rag-lab/AI Drama 的离线回放做法）。
4. 产出 M0 的 `report.md` + `architecture.md`（Archify 架构图）。

## 7. 决策点（需你确认）

A 手册建议目录是 `src/runtime/ src/agents/ src/registry/ src/memory/ src/tools/ src/evaluation/ experiments/a01…a10/ datasets/ reports/`，与 rag-lab 现有布局（`rag_engine/ rag_eval/ rag_lab/ service/`）**不同**。两种承载方式：

- **方案 1（推荐）**：新建独立仓库 `agent-runtime`（Agent Runtime 是与 RAG 并列的下一条学习线），rag-lab 仅作为它的"知识库/工具"依赖。
- **方案 2**：作为 rag-lab 的子包（如 `runtime/` + `experiments/a01…a10/`），复用其评测与记录纪律。

> 在确认前，本文件与 A 手册副本已加入 rag-lab `docs/guide/`，作为**规划文档**归档；不改变 rag-lab 现有 S/E 线的基线。
