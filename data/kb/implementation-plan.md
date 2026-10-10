# 分阶段实现与统一硬性测试方案 · Project Knowledge Engine

> 本文回答两件事：
> 1. **分阶段实现**——把《RAG 阶段性实践清单》的七个阶段翻译成一条**持续迭代的工程主线**：每阶段写哪些模块、按什么顺序、交付什么、怎么算完成。
> 2. **统一硬性测试**——一套**跨阶段不动**的测试方法：同一个套件、同一条命令、同一张门禁表、同一份报告格式，自动判定 + 退出码。
>
> 配套文档：`docs/stage-gates.md` 是测试协议的**详细设计**（为什么这样判、口径与纪律）；本文是**落地总纲**（怎么建、先建哪块、测试怎么挂上去）。二者不重复：一个讲实现路径，一个讲判据来源。

---

## 0. 一句话原则

**一个工程、一条流水线、七道门禁、单一基线。**

- 不做七个孤立 Demo：阶段 N 的产物直接叠在阶段 N-1 的工程上。
- 前三阶段**亲手实现核心检索链路**（清单 L105），不引入框架遮蔽错误来源。
- 每个阶段都用**同一批冻结问题**验证改动效果（清单 L105），并且**冻结数值基线**，否则无法计算 Δ。
- 系统本体（`rag_engine/`）与评测协议（`rag_eval/`）**解耦**，唯一连接点是 `Sut.answer(case, k)`。

---

## 1. 三层测试模型（"统一硬性"的完整定义）

"硬性" = 可自动判定、有退出码、有冻结基准、**不可事后放宽**。单靠检索指标测不出"增量索引是否真的只重建受影响切片"这类机制正确性，所以分三层：

| 层 | 名称 | 位置 | 回答的问题 | 判据 | 外部依赖 |
|---|---|---|---|---|---|
| **L1** | 功能 / 单元测试 | `tests/`（pytest，待建） | **机制对不对**（增量、过滤、去重、压缩、符号、隔离） | 二值 PASS/FAIL 断言 | 无（离线、确定性） |
| **L2** | 阶段门禁 | `rag_eval/runner.py` | **相对上一阶段有没有变好 / 有没有退化** | `gates.json`：主指标 + 护栏 + Δ | 无（可离线，零成本） |
| **L3** | 部署冒烟 | 走 HTTP / MCP 客户端 | **服务是不是真的跑得起来、可复现** | 成功率不下降 | 需服务在跑 |

三者的关系：

- **L1 保证"机制对"**：一个把整库推倒重建的增量索引，也能在 L2 上拿到一样的召回——只有 L1 能揭穿它。
- **L2 保证"效果可比较"**：把 L1 通过的系统放进冻结套件，算出相对基线的 Δ，产出一份能直接贴进报告的对比报告。
- **L3 保证"能交付"**：评测框架直接调用进程内的系统，绕过了网络/协议层；S7 必须真实走客户端。

**门禁总入口（任一层失败即中断）**：L1 → L2(S1..S6) → L3(S7)。退出码非 0 即视为阶段未通过。

---

## 2. 目标仓库结构（最终形态）

```
rag_engine/                     # ★ RAG 系统本体（被测对象），与 rag_eval 完全解耦
  config.py                     # Pydantic 配置；配置摘要 -> config_hash（进报告）
  ingest/
    loader.py                   # S1  TXT / Markdown / PDF -> Document
    clean.py                    # S2  清洗、去重、格式统一
    metadata.py                 # S2  Chunk Metadata 构造（来源/章节/位置/更新时间）
    chunker.py                  # S1/S2 固定长度 / 语义 / 层级切块（参数化对比）
  embed/
    embedder.py                 # S1  Embedder 协议 + 本地(sentence-transformers)/API 实现
  index/
    vector_store.py             # S1  FAISS / Chroma 封装
    bm25_store.py               # S3  BM25 关键词索引
    indexer.py                  # S2  增量索引：新增/更新/删除
    store.py                    # S7  索引持久化 + 后台更新
  retrieve/
    dense.py                    # S1  Top-K 语义检索
    filters.py                  # S2  Metadata Filtering
    parent_child.py             # S2  Parent-Child Retrieval
    sparse.py                   # S3  BM25 检索
    hybrid.py                   # S3  Dense+Sparse 融合（RRF）
    rerank.py                   # S3  Cross-Encoder / Rerank API
    rewrite.py                  # S3  Query Rewrite / Multi-query
  context/
    builder.py                  # S4  去重/相关性过滤/压缩/Token Budget/来源追踪
  code_rag/
    scanner.py                  # S5  扫描 Python 等语言仓库
    ast_indexer.py              # S5  AST / tree-sitter -> Symbol 索引 + 结构化切块
    deps.py                     # S5  调用与跨文件依赖关系
  generate/
    llm.py                      # LLM 客户端（超时/重试/用量统计）
    generator.py                # S1  带来源引用的回答
  service/
    api.py                      # S7  FastAPI：索引 / 检索 / 多项目知识库管理
    mcp_server.py               # S7  MCP：search_project / get_symbol / read_context
  pipeline.py                   # 组装成一条流水线，暴露 answer(case, k)
  eval_adapter.py               # 实现 rag_eval.sut.Sut 协议，注册进 REGISTRY

tests/                          # ★ L1 功能测试（待建）
  test_chunking.py              #   切块边界 / overlap / 稳定 chunk_id
  test_incremental_index.py     #   只重建受影响切片（S2 的核心验收）
  test_metadata_filter.py       #   过滤后结果全部满足条件
  test_hybrid_rrf.py            #   RRF 融合的确定性
  test_context_budget.py        #   超预算裁剪后来源仍可追溯
  test_code_symbols.py          #   AST 符号提取（S5）
  test_isolation.py             #   跨项目隔离（S5）
  test_eval_protocol.py         #   评测协议自检（指标口径、gates 与套件一致性）

scripts/
  run_gates.ps1                 # ★ 一条命令跑完 L1+L2(+L3)，聚合退出码（待建）
```

> `rag_engine/` 与 `tests/`、`scripts/` 为**目标产物**，随阶段落地；`rag_eval/`、`data/`、`baselines/`、`reports/` 已就绪。

---

## 3. 分阶段实现（S1–S7）

每阶段固定四问：**做什么（清单项）→ 写哪些文件（交付物）→ 门禁是什么 → 怎样算完成（DoD）**。

### 阶段一 · 基础 RAG Pipeline

| 项 | 内容 |
|---|---|
| 清单项 | 解析 TXT/MD/PDF；固定长度 Chunking + Overlap；Embedding；FAISS/Chroma；Top-K 语义检索；LLM 带引用回答 |
| 交付物 | `ingest/loader.py`、`ingest/chunker.py`、`embed/embedder.py`、`index/vector_store.py`、`retrieve/dense.py`、`generate/generator.py`、`pipeline.py`、`eval_adapter.py` |

**关键契约（后续阶段都依赖，先定死）**

```python
# 稳定 chunk_id 是增量索引与评测对齐的前提，阶段一就要保证
Document = { doc_id, source, doc_type, text, updated_at }
Chunk    = { chunk_id: f"{doc_id}:{seq:04d}", doc_id, text, meta }
Embedder.embed(texts) -> list[list[float]]          # 归一化后内积=余弦
VectorStore.add(chunks, vectors) / .search(vector, k, flt=None)
```

**实现步骤**

1. loader 统一输出 `Document`，PDF 用 PyMuPDF，MD/TXT 直读。
2. chunker 参数化 `size/overlap`；`chunk_id` **确定性**（同文档同参数 ⇒ 同 id）。
3. embedder 先接 `sentence-transformers` 本地模型；接口预留 API 实现（成本字段来源）。
4. vector_store 先 FAISS `IndexFlatIP` + L2 归一化；同时持久化 `chunk_id -> meta` 映射。
5. generator prompt 明确要求"仅依据给定段落回答，并用 `[chunk_id]` 标注来源"。
6. `eval_adapter` 实现 `Sut`，把 `retrieved / citations / prompt_tokens / cost_usd / latency_ms` 填全，注册进 `REGISTRY`。

**门禁（L2）**

```powershell
python -m rag_eval.runner --stage S1 --system my_pipeline --freeze
```

- 套件 `smoke_v1`（10 题，无标注），k=3。
- 主指标 `citation_missing_rate ≤ 0.2`；护栏 `error_rate = 0`。
- `--freeze` 产出**第一个数值基线**（清单只要求保留问题，这里补上保留数值）。

**DoD**：文档导入 → 索引构建 → 检索 → 带引用问答全通；`reports/*_S1_*.md` 落盘；基线冻结为 `baselines/S1__my_pipeline.json`。

**常见坑**：`chunk_id` 不稳定 ⇒ 增量索引与评测全部对不上；`latency_ms` 不自报 ⇒ 报告把评测框架开销算进延迟。

---

### 阶段二 · 文档处理与索引优化

| 项 | 内容 |
|---|---|
| 清单项 | 清洗/去重/格式统一；固定长度 vs 语义 vs 层级切块对比；Chunk Metadata；Metadata Filtering；Parent-Child；更新/删除/增量索引 |
| 交付物 | `ingest/clean.py`、`ingest/metadata.py`、`chunker.py`（增语义/层级）、`retrieve/filters.py`、`retrieve/parent_child.py`、`index/indexer.py`、`tests/test_incremental_index.py`、`tests/test_metadata_filter.py` |

**关键机制**

- **去重**：内容 `content_hash`；同一来源重复文档只留最新。
- **增量**：以 `doc_id` 为单位 diff（对比 `{mtime, content_hash}` 索引清单）→ 只对 `added/changed` 文档重算切片与向量，按 `doc_id` 删除旧切片。**只重建受影响的索引**（清单 L38）。
- **Metadata**：`source / section / position / updated_at / project_id / trust`，供过滤与来源回溯。
- **过滤**：metadata filtering 在检索入口前置，避免"先取 top-k 再过滤"导致候选不足（需要时加大候选再过滤）。
- **Parent-Child**：小块检索、返回所属父块作为生成上下文。

**L1 功能测试（硬性）**

- `test_incremental_index`：改动 1 个文档后，断言**重建的 chunk 集合 = 期望集合**，且**其余 chunk_id 与向量逐字节不变**。
- `test_metadata_filter`：断言过滤后命中结果 100% 满足过滤条件。

**门禁（L2）**：`python -m rag_eval.runner --stage S2 --system my_pipeline --baseline S1__my_pipeline`

- `smoke_v1` 回归：主 `error_rate = 0`，护栏 `citation_missing_rate` 不退化（`max_delta 0`）。
- 机制正确性由 L1 承担，**不塞进检索指标**。

**DoD**：更新文档后仅重建受影响索引（L1 绿）；可按来源过滤；任意答案能回溯到原文（source + position）。

---

### 阶段三 · 检索质量优化

| 项 | 内容 |
|---|---|
| 清单项 | BM25；Dense+Sparse Hybrid；RRF 融合；Cross-Encoder / API Reranker；Query Rewrite；Multi-query；准确率与延迟对比 |
| 交付物 | `index/bm25_store.py`、`retrieve/sparse.py`、`hybrid.py`、`rerank.py`、`rewrite.py`、`tests/test_hybrid_rrf.py` |

**实现步骤**

1. sparse：BM25（中文先分词/字粒度），与 dense 各出候选。
2. hybrid：**RRF 融合**（`score = Σ 1/(k + rank)`，无需量纲归一化）。
3. rerank：仅在候选集（如 top-50）上跑 Cross-Encoder，控制成本。
4. rewrite/multi-query：生成改写与多路子查询，扩大召回。
5. 每个方案的 `config_hash` 必须变化，保证报告可追溯到具体配置。

**门禁（L2）**：`--stage S3 --system <方案> --baseline S3__<上一方案>`

- 套件 `retrieval_v1`（20 题，含 `relevant_chunk_ids` + dev/holdout），k=3。
- 主指标 `mrr Δ ≥ +0.10`、`recall@3 Δ ≥ +0.05`。
- 护栏 `p95_latency_ms ≤ 500`、`cost_per_query_usd ≤ 0.005`。
- **清单 L48 要求**：对 Dense / BM25 / Hybrid / Rerank **各跑一次**，报告横向对比。

**DoD**：`reports/*_S3_*.md` 给出四方案对比；主指标达标且护栏不越线（仓库内已有一次真实示例：主指标 PASS 但 p95 越线 → 整阶段 FAIL）。

---

### 阶段四 · Context Engineering

| 项 | 内容 |
|---|---|
| 清单项 | 去重与相关性过滤；Context Compression；Token Budget；冲突/过期/低可信度处理；来源追踪；长度/成本/质量对比 |
| 交付物 | `context/builder.py`、`tests/test_context_budget.py` |

**Context Builder 职责（按序）**

1. 去重（chunk_id / 文本近似）。
2. 相关性阈值过滤。
3. 压缩（抽取式/摘要式，压缩后必须仍带来源）。
4. **Token Budget 分配**：按文档分组，保证每文档至少 1 块，剩余预算按分排序填充，超预算截断。
5. 冲突/过期/低可信度标注（`updated_at`、`source` 可信度），生成器据此降权。
6. 输出 `Context{ segments:[{chunk_id, source, text}], tokens }`。

**L1**：`test_context_budget` 断言超预算被裁剪，且**裁剪后引用来源与定位不丢失**。

**门禁（L2）**：`--stage S4 --system my_pipeline --baseline S1__my_pipeline`

- `retrieval_v1` k=5；主 `citation_precision` 不下降（`min_delta 0`）；护栏 `avg_prompt_tokens ≤ 2000`。
- 记录压缩前后：**质量不降 且 token 下降**（清单 L57）。

**DoD**：固定预算下输出可追溯上下文；报告含成本与质量变化。

---

### 阶段五 · Code RAG 专项

| 项 | 内容 |
|---|---|
| 清单项 | 扫描代码；AST/tree-sitter；Symbol 索引；函数/类级结构化切块；引用与依赖关系；符号+关键词+语义融合；Git 变更增量；多项目隔离 |
| 交付物 | `code_rag/scanner.py`、`ast_indexer.py`、`deps.py`、**新建套件 `data/eval_suites/code_v1.jsonl`**、`tests/test_code_symbols.py`、`tests/test_isolation.py` |

**先建套件再写检索**（当前 `gates.json` 的 S5 套件为空，runner 会直接跳过）：

```jsonl
{"id":"kc01","question":"分页参数是在哪个函数校验的？","expected_symbols":["validate_page","PageQuery.validate"],
 "relevant_chunk_ids":["<symbol chunk>"],"project_id":"proj-a","split":"holdout"}
```

- 套件必须包含**至少两个项目**的用例，才能测出泄漏。
- 结构化切块：以函数/类/方法为单位，块头写 `symbol / kind / file / span / deps`。

**L1**：`test_code_symbols`（AST 提取的函数/类/方法名与预期一致）、`test_isolation`（检索结果全部属于目标项目）。

**门禁（L2）**：`--stage S5 --system my_pipeline --baseline <冻结基线>`

- `code_v1` k=10；主 `recall@10` 不下降；**护栏 `leakage_rate = 0`**（跨项目混入率必须为 0，清单 L68）。

**DoD**：自然语言可定位函数、相关调用点与跨文件依赖；任意用例不混入其它项目。

---

### 阶段六 · Evaluation 与性能优化

| 项 | 内容 |
|---|---|
| 清单项 | Golden Dataset；Recall@K/Precision@K/MRR；Rerank 前后排序；忠实度与引用正确性；延迟/Token/成本；配置对比；自动化回归 |
| 交付物 | 扩充 `retrieval_v1`/`code_v1`；`ragas`/`deepeval` 忠实度**观察项**；`scripts/run_gates.ps1`、`.github/` 或等价 CI |

**门禁（L2）**：`--stage S6 --system my_pipeline --baseline <最新冻结>`

- 套件 `smoke_v1` + `retrieval_v1`；主指标空；护栏 `recall@3 max_delta -0.01`、`error_rate = 0` —— 即**回归门禁**（清单 L78）。

**自动化回归（L1+L2 合流）**：`scripts/run_gates.ps1`

```powershell
pytest -q                                   # L1：机制正确性
python -m rag_eval.runner --stage S6 --system my_pipeline --baseline latest   # L2：全量回归
exit $LASTEXITCODE                          # 非 0 即 CI 失败
```

**忠实度处理**：LLM 裁判本身有方差，**只作观察项、不做门禁**；如需门禁，固定裁判模型 + 多采样取均值。

**DoD**：每次改配置自动产出质量/延迟/成本对比报告；CI 红绿分明。

---

### 阶段七 · 工程集成与扩展

| 项 | 内容 |
|---|---|
| 清单项 | FastAPI 封装；多项目知识库管理；持久化 + 后台更新；Docker；MCP（`search_project`/`get_symbol`/`read_context`）；接 Cline/Codex；选做 Graph RAG |
| 交付物 | `service/api.py`、`service/mcp_server.py`、`Dockerfile`、`compose.yaml`、`eval_adapter.py` 增加"走 HTTP"的实现（如 `http_pipeline`） |

**MCP 工具签名（建议冻结）**

```
search_project(project_id, query, k=5, filters?) -> [{chunk_id, source, score, snippet}]
get_symbol(project_id, symbol, kind?)            -> {def, file, span, callers[], callees[]}
read_context(project_id, query, token_budget)    -> {segments:[{chunk_id,source,text}], citations[]}
```

**门禁（L3+L2）**：`--stage S7 --system http_pipeline --baseline latest`

- `smoke_v1` 经真实客户端调用；主 `success_rate` 不下降。
- 验证"可复现"：`docker compose up` → 跑评测 → 结果与本地一致（清单 L88）。

**DoD**：外部客户端经标准接口检索项目知识；部署与测试步骤文档化、可复现。

---

## 4. 统一硬性测试方案（汇总）

### 4.1 五个"固定"（不改协议就不可比）

1. **数据集固定**：套件是文件，运行时记录 `sha256`；与基线的哈希不一致 → 直接 FAIL（防"看结果改题目"）。
2. **指标实现固定**：口径写在 `rag_eval/metrics.py`；改口径必须 bump `EVAL_VERSION`。
3. **运行方式固定**：一条命令，跨阶段仅 `--stage` 与 `--system` 变。
4. **基准固定**：baseline 是**冻结的报告文件**（`baselines/*.json`），不是"重跑一遍"。
5. **判定规则固定**：门禁写在 `rag_eval/gates.json`，是数据不是代码；阶段中途不得放宽。

> 完整论证见 `docs/stage-gates.md`。

### 4.2 测试资产与变更纪律

| 路径 | 作用 | 变更纪律 |
|---|---|---|
| `data/eval_suites/smoke_v1.jsonl` | 阶段一冒烟（10 题，无标注） | 阶段二后不得修改 |
| `data/eval_suites/retrieval_v1.jsonl` | 检索套件（20 题，含标注 + dev/holdout） | 冻结使用；新增用例标 `added_in_stage` 并单独统计 |
| `data/eval_suites/code_v1.jsonl` | Code RAG 套件（**待建**，含 `expected_symbols` + `project_id`） | 阶段五冻结 |
| `rag_eval/metrics.py` | 指标口径 | 改动必须 bump `EVAL_VERSION` |
| `rag_eval/gates.json` | 判定规则 | 阶段开始时定，中途不得放宽 |
| `baselines/*.json` | 冻结基线数值 | 只增不改；新基线 = 新文件名 |
| `reports/*.json` / `*.md` | 每次运行产物 | 追加式，不覆盖 |

### 4.3 阶段 × 门禁总表

| 阶段 | 套件 | k | 主指标（判据） | 护栏 | 特殊动作 |
|---|---|---|---|---|---|
| S1 | `smoke_v1` | 3 | `citation_missing_rate ≤ 0.2` | `error_rate = 0` | `--freeze` 产出首个数值基线 |
| S2 | `smoke_v1` | 3 | `error_rate = 0` | `citation_missing_rate` 不退化 | 机制正确性由 `tests/` 承担 |
| S3 | `retrieval_v1` | 3 | `mrr Δ≥+0.10`、`recall@3 Δ≥+0.05` | `p95≤500ms`、`cost≤$0.005` | Dense/BM25/Hybrid/Rerank 各跑一次 |
| S4 | `retrieval_v1` | 5 | `citation_precision` 不下降 | `avg_prompt_tokens ≤ 2000` | 对比压缩前后（质量不降、token 降） |
| S5 | `code_v1`（待建） | 10 | `recall@10` 不下降 | `leakage_rate = 0` | 先编写套件 |
| S6 | `smoke_v1` + `retrieval_v1` | 3 | —（全护栏） | 任一指标回退 ≤ 0.01 | CI 回归门禁 |
| S7 | `smoke_v1`（走客户端） | 3 | `success_rate` 不下降 | — | 真实 HTTP/MCP 调用 |

判定取值：`PASS` / `FAIL` / `BASELINE`（缺基线）/ `NO_GATE`（仅观察项）。

### 4.4 命令手册（跨阶段写法完全一致）

```powershell
# 阶段一起步：跑通并冻结首个基线
python -m rag_eval.runner --stage S1 --system my_pipeline --freeze

# 后续每阶段：与冻结基线对比
python -m rag_eval.runner --stage S3 --system my_pipeline --baseline S1__my_pipeline

# 只跑某套件 / 临时改 k（排查用，不作正式结论）
python -m rag_eval.runner --stage S3 --system my_pipeline --suite retrieval_v1 --k 5

# 协议自检（仓库现有占位系统，证明"跑→报告→对比→判定→退出码"链路是通的）
python -m rag_eval.runner --stage S3 --system stub_dense --freeze
python -m rag_eval.runner --stage S3 --system stub_hybrid --baseline S3__stub_dense
```

- `--baseline` 接受：报告 json 路径 / 冻结名（`baselines/<名>.json`）/ `latest`。
- **退出码**：任一 `FAIL` → `1`（可直接作 CI 门禁）；否则 `0`。
- 每次同时落盘 `.json`（机器可读、含逐条 `per_case`）与 `.md`（可直接贴进阶段报告）。

### 4.5 阈值策略（文档没给阈值，必须"先测后定"）

1. S1 先跑出基线数值（`--freeze`）。
2. 目标幅度按"值得做一次改造"定，经验区间：排序 Δ≥0.10、召回 Δ≥0.05、成本 ≤+20%、p95 ≤+30% 或绝对上限。
3. 护栏用"绝不能破线"的值：跨项目混入率 = 0、错误率 = 0、token 预算上限。
4. 阈值写进 `gates.json` 后不再改；必须改时在报告里注明原因（否则等于事后放宽标准）。

---

## 5. 阶段 × 测试总矩阵

| 阶段 | 交付模块 | L1 功能测试 | L2 门禁 | L3 冒烟 | 清单验收对应 |
|---|---|---|---|---|---|
| S1 | loader/chunker/embedder/vector_store/dense/generator | 切块稳定 id | S1 `smoke_v1` | — | 可运行的文档问答 + 初始基线 |
| S2 | clean/metadata/filters/parent_child/indexer | 增量索引、metadata 过滤 | S2 回归 | — | 仅重建受影响索引、可过滤可回溯 |
| S3 | bm25/sparse/hybrid/rerank/rewrite | RRF 融合确定性 | S3 四方案对比 | — | Dense/BM25/Hybrid/Rerank 指标对比 |
| S4 | context/builder | 预算裁剪不丢来源 | S4 引用精度 + token 预算 | — | 固定预算可追溯上下文 + 成本记录 |
| S5 | scanner/ast_indexer/deps + `code_v1` | 符号提取、隔离 | S5 召回 + 零泄漏 | — | 定位函数/调用点/依赖，不串项目 |
| S6 | 套件扩充 + CI | 协议自检 | S6 全量回归 | — | 自动产出质量/延迟/成本报告 |
| S7 | FastAPI/MCP/Docker | — | S7 成功率 | S7 客户端调用 | 外部客户端可检索、部署可复现 |

**里程碑映射（压缩版，把 S1–S7 合并执行，不另写评测）**

| 里程碑 | 覆盖 | 套件 | 主指标 |
|---|---|---|---|
| M1 | 阶段一 + 二 | `smoke_v1` | `citation_missing_rate ≤ 0.2` |
| M2 | 阶段三 + 四 | `retrieval_v1` | `mrr Δ≥+0.10`、`recall@3 Δ≥+0.05` |
| M3 | 阶段五 + 六 + 七 | `code_v1` + 回归 | `recall@10` 不下降、零泄漏 |

---

## 6. 执行顺序（现在从哪开始）

1. **落地阶段一**：按第 3 节写 `rag_engine/` 最小链路，在 `rag_eval/sut/__init__.py` 的 `REGISTRY` 注册为 `my_pipeline`。
2. **换真实语料**：用项目文档替换 `data/corpus/demo.jsonl`；写自己的 `smoke_v1`（阶段一可无标注，**阶段三之前必须补 `relevant_chunk_ids`**）。
3. **冻结首个基线**：`--stage S1 --system my_pipeline --freeze`。
4. **每完成一个阶段**：先跑 `tests/`（L1），再跑同一条 L2 命令对比冻结基线，报告落 `reports/`。
5. **建 `code_v1` 后再做阶段五**；**接 CI 在阶段六**；**服务化在阶段七**。

---

## 7. 反模式（禁止）

- ❌ 重跑基线再比 Δ（把噪声当提升）——基线只读，要换就 `--freeze` 新基线。
- ❌ 改套件题目后仍与旧报告对比——运行时 `sha256` 会直接判 FAIL。
- ❌ 改 `metrics.py` 公式不 bump `EVAL_VERSION`——历史报告与新报告不可比。
- ❌ 把"机制正确性"塞进检索指标——增量/过滤/隔离的正确性交给 `tests/`。
- ❌ 阶段中途放宽 `gates.json`——等于事后调标准。
- ❌ 用 LLM 裁判做硬门禁且不控方差——忠实度先作观察项。
- ❌ 七个孤立 Demo——所有阶段叠在同一条流水线上。

---

> 一句话收尾：**实现按阶段迭代，测试跨阶段不变。** 变的只有 `--system`，不变的是套件、指标、基线、门禁与报告格式。
