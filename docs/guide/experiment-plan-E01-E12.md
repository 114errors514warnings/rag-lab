# RAG 实验线 · E01–E12 计划与测试标准

> 依据：`RAG阶段性实践清单.md`、`docs/guide/implementation-plan.md`（S1–S7）、`docs/reports/S/R0/round-0.md`（E 线映射）、
> `docs/guide/records-convention.md`。**E 线映射来自仓库既有线索；若与《RAG 架构验证与性能优化实验手册》原文有出入，以手册为准并在此追加修订。**
>
> 固定不变（跨阶段）：运行器 `scripts/run_eval.py`、数据集 `data/golden/cases.jsonl`（sha 冻结）、指标口径 `rag_eval/metrics.py`（改口径须 bump `EVAL_VERSION`）、报告格式。
> 变的只有 `configs/E0x.yaml` 的 `system`。

## 0. 统一的测试标准（每阶段都适用）

- **L1（机制正确性，pytest，离线确定性）**：二值断言；`python -m pytest -q` 必须全过。
- **L2（阶段门禁，`scripts/run_eval.py`）**：
  - 命令：`python scripts/run_eval.py --config configs/E0x.yaml --baseline <上一轮 run_id>`
  - 判定：`PASS / FAIL / BASELINE / NO_GATE`；**任一 FAIL ⇒ 退出码 1**。
  - 每阶段在 `configs/E0x.yaml` 里**预声明 gates**（`max` 绝对上限 / `min_delta` 提升 / `max_delta` 容忍回退）。
- **A/B 配对**：自动输出逐题配对 + bootstrap 95% CI（跨 0 记"证据不足"）。
- **产物**：`reports/{run_id}/{metrics.json,cases.jsonl,errors.csv,comparison.md}`、`traces/{run_id}.jsonl`；
  阶段文档 `docs/reports/E/<阶段>/stage-<阶段>-{report,architecture}.md`；重要阶段配 Archify 架构图。
- **记录**：E 阶段文档在 `docs/reports/E/<阶段>/`；S 计划轮次快照在 `docs/reports/S/R{n}/round-{n}.md`；历史只追加不改写（见统一开发准则）。

## 1. R1（E01–E05 · 解析 / 切块 / 召回）

### E01 · 解析器扩展（文档/代码解析与 doc_id 稳定）
- **对照**：E00（loader 现状）。
- **实施**：确保 `.md/.txt/.py` 解析正确、`doc_id` 由来源相对路径稳定派生、`load_tree` 多项目（`proj-*`）隔离正确；补 L1。
- **指标**：`trace_completeness`、`recall@5`、`error_rate`。
- **L1 断言**：同文件 ⇒ 同 `doc_id`；不同项目 ⇒ 不同 `project_id`；解析内容含预期片段。
- **L2 门禁**：`recall@5 max_delta -0.01`；`context_evidence_coverage max_delta -0.01`；`p95_latency_ms max 500`。
- **产物**：`configs/E01.yaml`（可复用 E00 系统参数，用于回归）、L1 测试、阶段两份文档。

### E02 · 切块参数（size / overlap 网格）
- **对照**：E00（400/80）。
- **实施**：`chunk_size ∈ {256,400,512}`、`overlap ∈ {0,80,128}` 各跑一次（同一其它参数）。
- **指标**：`recall@5`、`precision@5`、`ndcg@5`、`p95_latency_ms`。
- **L1**：切块边界/overlap/`chunk_id` 稳定性（已有）+ 新增参数化断言。
- **L2 门禁**：最优配置相对 E00 `recall@5 min_delta 0`（不得回退）；`p95_latency_ms max 500`。
- **产物**：`configs/E02a/E02b/E02c.yaml`、对比报告。

### E03 · 符号级切块（函数/类级结构化）
- **对照**：E00 定长块。
- **实施**：以 AST 函数/类/方法为单位切块（`meta.symbol/kind/file/span`），仅对代码语料生效。
- **指标**：代码子集 `recall@5`、`context_evidence_coverage`。
- **L1**：AST 提取的符号名/种类与预期一致；`chunk_id` 稳定。
- **L2 门禁**：代码子集 `recall@5 min_delta 0`；整体 `recall@5 max_delta -0.01`。
- **产物**：`configs/E03.yaml`、L1 测试、阶段文档。

### E04 · Embedding（真实语义 vs hashing-tfidf）
- **对照**：E00（hashing-tfidf）。
- **实施**：`embed_provider=openai`（需 API Key）或本地模型；离线环境跑 hashing 作为对照，真实模型标 `BASELINE`。
- **指标**：`recall@5`、`mrr@5`、`cost_per_query`（新增）、`p95_latency_ms`。
- **L1**：`Embedder` 协议与 L2 归一化不变量。
- **L2 门禁**：`recall@5 min_delta 0`；`p95_latency_ms max 500`；缺 Key ⇒ `BASELINE`（不算通过）。
- **产物**：`configs/E04.yaml`、阶段文档。

### E05 · 检索策略（Dense / BM25 / Hybrid）+ 拒答
- **对照**：E00（Dense）。
- **实施**：新增 `system.retrieval ∈ {dense, bm25, hybrid}` 与 `min_relevance`（拒答）；runner 支持系统变体选择。
- **指标**：`recall@5`、`mrr@5`、`no_answer_accuracy`、`p95_latency_ms`。
- **L1**：RRF 融合确定性；拒答阈值行为。
- **L2 门禁**：`recall@5 min_delta 0`、`mrr@5 min_delta 0`；`no_answer_accuracy min_delta 0`；`p95 max 500`。
- **产物**：`configs/E05_{dense,bm25,hybrid}.yaml`、对比报告。

## 2. R2（E06–E09 · 排序 / 上下文 / 成本）

### E06 · Rerank（重排前后）
- **对照**：E05 最优。
- **实施**：候选 top-N 上重排（词面替身 / Cross-Encoder）。
- **指标**：`mrr@5`、`ndcg@5`、`p95_latency_ms`。
- **L1**：重排确定性；候选数受控。
- **L2 门禁**：`mrr@5 min_delta 0`；`p95 max 500`。

### E07 · Query Rewrite / Multi-query
- **对照**：E06。
- **实施**：术语扩展与多查询融合。
- **指标**：`recall@5`、`mrr@5`。
- **L1**：改写确定性、扩展词命中。
- **L2 门禁**：`recall@5 min_delta 0`；`mrr@5 max_delta -0.01`。

### E08 · Parent-Child 检索与上下文扩展
- **对照**：平铺块。
- **实施**：小块召回、父块作上下文。
- **指标**：`context_evidence_coverage`、`avg_prompt_tokens`。
- **L1**：子→父映射正确；父块来源可追溯。
- **L2 门禁**：`context_evidence_coverage min_delta 0`；`avg_prompt_tokens max 2000`。

### E09 · Context Builder（去重 / 压缩 / Token 预算 / 来源追踪）
- **对照**：全量拼接。
- **实施**：`context/builder.py` 接入生成路径。
- **指标**：`context_evidence_coverage`、`answer_accuracy`、`avg_prompt_tokens`、`cost_per_query`。
- **L1**：预算裁剪后来源/定位不丢。
- **L2 门禁**：`context_evidence_coverage max_delta -0.01`；`avg_prompt_tokens max 2000`。

## 3. R3（E10–E12 · 阶段五+六+七 + 盲测）

### E10 · 增量索引
- **对照**：整库重建。
- **实施**：以 `doc_id` diff 只重建受影响切片。
- **指标**：`trace_completeness`、建索引耗时（新增）、`recall@5`。
- **L1**：仅重建受影响切片；其余向量逐字节不变。
- **L2 门禁**：`recall@5 max_delta -0.01`；`error_rate max 0`。

### E11 · 多项目隔离与回归门禁（CI）
- **对照**：无隔离。
- **实施**：`leakage_rate` 断言 + `scripts/run_gates.ps1` 聚合（pytest + run_eval）。
- **指标**：`leakage_rate`、全量回归。
- **L1**：跨项目检索结果全部属于目标项目。
- **L2 门禁**：`leakage_rate max 0`；全部指标 `max_delta -0.01`。

### E12 · 服务化（http_pipeline + 可复现部署）
- **对照**：进程内调用。
- **实施**：FastAPI/MCP 暴露检索；`http_pipeline` 经真实 HTTP 调用。
- **指标**：`answer_accuracy`、`error_rate`、`p95_latency_ms`。
- **L1**：服务端 schema/路由。
- **L2 门禁**：`answer_accuracy max_delta -0.02`；`error_rate max 0`。

## 4. 里程碑映射（E 线）

| 里程碑 | 覆盖 | 出口判据 |
|---|---|---|
| M0 | E00 + 平台 | ✅ 已交付（R0） |
| M1 | E01–E05 | 召回不回退；拒答可用；可复现 |
| M2 | E06–E09 | 排序/上下文指标提升或持平，成本受控 |
| M3 | E10–E12 | 增量/隔离/服务化全绿 |

## 5. 执行顺序
`E01 → E02 → E03 → E04 → E05`（R1）→ `E06 → E07 → E08 → E09`（R2）→ `E10 → E11 → E12`（R3）。
每阶段：写模块 → L1 → L2（对比冻结基线）→ 两份文档（+重要阶段 Archify 图）→ 提交；**测试不过先停下汇报**。
