# Agent 工程与运行时系统实验手册 · A01–A10

> **来源**：外部计划文档，原文 `assets/Agent工程与运行时系统实验手册_A01-A10.docx`（v1.0 · 2026-10-10）。
> 本文为**逐字转换的 Markdown 版**，便于检索与引用；内容以原文为准。
>
> **定位**：新增实验阶段 **A01–A10**，承接 **RAG / Code RAG 与 Tool Calling**。**A 编号为新增，不覆盖原有 E00–E12**。
> 提示（原文第 124 行）：*"本文件是一份新增实验计划，而非已执行的实验记录。所有指标需要在真实运行后填写结果与证据。"*

---

## 一、阶段定位与实验原则

本阶段在已完成的 **RAG 项目知识库**与 **Tool Calling / Tool Executor** 基础上，逐步实现：单 Agent 循环 → 工作流 → 持久状态 → 任务调度 → Registry → 记忆 → 恢复 → 多 Agent 协作，最终形成**可复现、可评测的 AI Engineering Runtime**。实验编号 A01–A10 为新增编号，不覆盖原有 E00–E12。

统一原则：先实现最小可运行基线，再增加框架实现或优化；所有实验保留固定输入、执行轨迹、结构化日志、自动化断言、可复现结果；对照实验控制模型、提示词、工具集合、知识库快照与预算。

## 二、前置条件与统一技术栈

- **已有**：Python 工程基础、模型 API、**结构化 Tool Schema / Executor**、可调用的 RAG 检索接口。
- **推荐**：Python 3.11+、Pydantic、asyncio、pytest、FastAPI、SQLite（本地状态）、可选 PostgreSQL/Redis；LangGraph 作为对照实现而不是唯一依赖。
- **统一工具样例**：`search_project`、`get_symbol`、`read_context`、`run_test`；写入类工具先限制为沙箱目录并提供 dry-run。
- **统一观测字段**：`run_id、task_id、agent_id、step_id、tool_name、input_hash、latency_ms、tokens_in/out、cost_estimate、status、error_type、trace_id`。

## 三、实验路线与依赖关系

| 序号 | 主题 | 依赖 |
|---|---|---|
| A01 | Agent Loop 与 ReAct | Tool Calling |
| A02 | Agent Workflow 与状态机 | A01 |
| A03 | Agent State 与 Checkpoint | A02 |
| A04 | Agent Runtime 与任务调度 | A01–A03 |
| A05 | Agent Registry 与动态生命周期 | A04 |
| A06 | Skill Registry 与 Tool Registry | A05 |
| A07 | Agent Memory 与 RAG 集成 | A03/A05/A06 |
| A08 | Retry / Rollback 与故障恢复 | A03–A07 |
| A09 | Multi-Agent 通信与协作 | A04–A08 |
| A10 | 综合 Runtime 集成与性能评测 | A01–A09 |

### A01 · Agent Loop 与 ReAct
- 依赖：Tool Calling
- 目标与对照：构建"模型决策→工具调用→观察→继续/停止"闭环；同题对比单轮直答与 Agent Loop，观察决策质量、无效循环与预算耗尽。
- 实施：`max_steps`、`token_budget`、工具白名单、结束判定、轨迹记录；准备需多步检索与单步直答两类任务。
- 指标：任务成功率、平均步数、无效调用率、token/任务、超时率。
- 验收：运行 20 个固定任务；无无限循环；预算超限可确定终止；每步可回放。
- 产物：`experiments/a01/`（README.md、config.yaml、tests/、results.json、trace.jsonl、结论摘要）。

### A02 · Agent Workflow 与状态机
- 依赖：A01
- 目标与对照：实现顺序/条件分支/循环与人工审批节点；对比自由循环与确定性工作流。
- 实施：定义状态转移表及条件守卫；构建"检索→分析→验证→输出" DAG，并注入分支错误。
- 指标：状态转移正确率、路径覆盖率、完成率、步骤数。
- 验收：正常/失败/取消三类路径均有自动测试；非法转换被拒绝。
- 产物：`experiments/a02/`。

### A03 · Agent State 与 Checkpoint
- 依赖：A02
- 目标与对照：持久化任务上下文、消息摘要、当前节点与工具结果；验证断点恢复与幂等性。
- 实施：状态 Schema/version；SQLite 持久化；每个关键节点 checkpoint；模拟进程异常与重启。
- 指标：恢复成功率、重复副作用次数、状态一致性、恢复耗时。
- 验收：同一 checkpoint 恢复结果一致；有副作用步骤不能重复执行。
- 产物：`experiments/a03/`。

### A04 · Agent Runtime 与任务调度
- 依赖：A01–A03
- 目标与对照：任务队列、并发限制、取消、超时、生命周期及隔离。
- 实施：asyncio 调度器；状态 `queued/running/paused/completed/failed/cancelled`；执行 1/5/20 并发压力。
- 指标：吞吐、p50/p95 延迟、任务饥饿、取消响应时间、资源用量。
- 验收：并发限制有效；任务取消会释放资源；异常不阻塞其他任务。
- 产物：`experiments/a04/`。

### A05 · Agent Registry 与动态生命周期
- 依赖：A04
- 目标与对照：按任务选用不同 Agent 配置、实例化并释放；配置隔离与注册发现。
- 实施：`AgentSpec(id/version/role/model/tools/permissions)`；注册、查找、创建、销毁；测试热更新与非法配置。
- 指标：创建耗时、销毁后资源残留、配置误用率、路由正确率。
- 验收：不同 Agent 的权限互不串用；释放后无悬挂任务。
- 产物：`experiments/a05/`。

### A06 · Skill Registry 与 Tool Registry
- 依赖：A05
- 目标与对照：区分 **Skill**（可复用执行策略）与 **Tool**（实际操作接口）；支持声明、版本、权限、调用审计。
- 实施：`SkillSpec/ToolSpec`、Schema 校验、能力发现、启停与版本兼容；模拟危险工具越权调用。
- 指标：发现正确率、Schema 校验覆盖、权限拦截率、调用成功率。
- 验收：非法参数与越权请求均被拒绝并记录；版本冲突有清晰错误。
- 产物：`experiments/a06/`。

### A07 · Agent Memory 与 RAG 集成
- 依赖：A03/A05/A06
- 目标与对照：短期状态、长期检索记忆与项目级 Code RAG 分层协作，控制跨项目串扰。
- 实施：`session/project/agent` 三层 Memory；对照"无记忆/全文历史/RAG 检索记忆"；写入去重与过期策略。
- 指标：检索命中率、回答/修改成功率、串库率、token 成本。
- 验收：多项目隔离测试通过；记忆来源可追溯；陈旧信息可更新。
- 产物：`experiments/a07/`。

### A08 · Retry / Rollback 与故障恢复
- 依赖：A03–A07
- 目标与对照：可重试错误分类、退避重试、幂等键、补偿动作与人工干预。
- 实施：注入 LLM 超时、429、工具异常、状态存储失败；对照"无恢复/有限重试/回滚补偿"。
- 指标：恢复率、重复写入率、重试次数、额外成本、故障定位时间。
- 验收：超出重试上限明确失败；写操作具备回滚或补偿记录；无静默数据污染。
- 产物：`experiments/a08/`。

### A09 · Multi-Agent 通信与协作
- 依赖：A04–A08
- 目标与对照：**Director / Worker / Verifier** 与消息总线；考察协作收益与开销。
- 实施：任务拆分（检索/执行/验证）；测试串行/并行/单 Agent 基线；注入冲突指令与消息丢失。
- 指标：任务完成率、协作开销、消息丢失率、总 token、p95 延迟。
- 验收：消息含关联 ID 与版本；冲突有仲裁规则；失败节点可重试。
- 产物：`experiments/a09/`。

### A10 · 综合 Runtime 集成与性能评测
- 依赖：A01–A09
- 目标与对照：整合 Project Knowledge、Registry、Workflow、Memory、Evaluator；输出可部署的最小工程成果。
- 实施：建立 30–50 个 Golden Tasks；分别测"单 Agent / 多 Agent / 带与不带 RAG / 带与不带恢复"；生成报告。
- 指标：Task Completion、Tool Success、Recall、p95 延迟、token/任务、成本、恢复率。
- 验收：固定数据集可复测；出具原始 trace、测试报告、架构图、README 与演示脚本。
- 产物：`experiments/a10/`。

## 四、统一测试设计与统计方法

- **测试集**：覆盖简单、多跳、需要工具、工具不可用、检索误导、权限越界、并发冲突、可恢复失败等任务类型；固定 random seed、语料版本与模型参数。
- **统计**：每个对照组尽量运行 3 次以上；记录均值与 p95；对概率性任务同时报告成功次数/总次数，不能仅展示最好的一次。
- **消融**：依次关闭 RAG、Memory、Retry、Multi-Agent，对比完成率、成本及延迟；避免多变量同时变化得出因果结论。
- **安全**：文件写入、命令执行与外部网络调用必须具备沙箱、权限确认、路径约束；对工具结果与 RAG 文本按非可信输入处理。

## 五、里程碑与交付目录

- **M1（A01–A03）**：可运行单 Agent + Workflow + 断点恢复。
- **M2（A04–A06）**：可配置 Runtime + Agent/Skill/Tool Registry。
- **M3（A07–A09）**：RAG Memory + 故障恢复 + 多 Agent。
- **M4（A10）**：完整基准与部署演示，连接后续 MCP、Evaluation 和成本优化阶段。

建议仓库目录：`src/runtime/`、`src/agents/`、`src/registry/`、`src/memory/`、`src/tools/`、`src/evaluation/`、`experiments/a01…a10/`、`datasets/`、`reports/`。

## 六、与原学习路线的衔接

RAG 阶段交付 **Project Knowledge Engine**；Tool Calling 阶段交付 **Tool Executor**；本手册交付 **Agent Runtime**。下一阶段通过 MCP Server 向 Cline/Codex/OpenClaw 暴露 `search_project`、`get_symbol`、`read_context`、`run_test` 等能力；Evaluation 与成本优化贯穿各阶段。
