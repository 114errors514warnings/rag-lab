# 实验轮次记录 · R0 / M0 平台化基线（冻结快照）

> 对应《RAG 架构验证与性能优化实验手册》第 1 轮（E00 + Golden + Trace）。
> 合并了原「阶段一记录」（基础 RAG Pipeline）的简要内容；记录约定见 [`../../guide/records-convention.md`](../../guide/records-convention.md)。
> 这是**平台 + 被其验证的系统**的联合快照，后续轮次会覆盖 `rag_engine/` 与 `rag_lab/` 里的文件。

## 0. 元信息

| 项 | 值 |
|---|---|
| 轮次 | R0（里程碑 M0）；系统侧对应旧计划阶段一 |
| 状态 | ✅ 系统最小链路 + 实验平台骨架已落地，E00 基线已产出 |
| 日期 | 2026-10-08（阶段一）/ 2026-10-09（平台化） |
| 评测协议版本 | `v2`（证据制；`rag_eval/__init__.py` 的 `EVAL_VERSION`） |
| 被测系统 | `my_pipeline` = `rag_engine(hashing-tfidf + dense + extractive)` |
| 配置指纹 `config_hash` | `e821df85555c`（E00）；阶段一旧指纹 `fc3a4c805df7`（v1 口径） |
| 数据快照 | `snapshots/kb.json`（digest `df5eb069a83579d2`，10 文件） |
| 数据集 | `data/golden/cases.jsonl`（32 题，sha `626aa1732b4f8e12`） |
| E00 run_id | `20261009T155134_E00_e821df85555c_nogit_df5eb069a83579d2_626aa1732b4f8e12` |
| 报告 / Trace | `reports/{run_id}/{metrics.json,cases.jsonl,errors.csv,comparison.md}` · `traces/{run_id}.jsonl` |
| 架构图 | `docs/reports/R0/diagrams/round-0.architecture.html`（源 `.../round-0.architecture.json`，由 Archify 生成，showcase 质量门禁全过） |

## 1. 系统本体（原阶段一，简要）

基础 RAG Pipeline：**解析 → 切块 → Embedding → 向量索引 → Top-K 检索 → 带引用生成**。

| 清单项（阶段一） | 落地 |
|---|---|
| 解析 TXT / Markdown / PDF | ✅ TXT/MD/PY 已实现；PDF 走可选依赖（PyMuPDF / pypdf） |
| 固定长度 Chunking + Overlap | ✅ `ingest/chunker.py`（末端优先断句；附 `start_line/end_line` 供证据映射） |
| 调用 Embedding 生成向量 | ✅ 默认离线 `HashingTfidfEmbedder`；可选 `OpenAIEmbedder` |
| FAISS / Chroma 向量索引 | ✅ numpy 内积后端（等价 `IndexFlatIP` 语义；接口可替换） |
| Top-K 语义检索 | ✅ `retrieve/dense.py`（支持 `project_id` 过滤） |
| 带来源引用的回答 | ✅ 抽取式 `ExtractiveGenerator`；可选 `OpenAIGenerator` |

### 1.1 `rag_engine/` 逐文件职责

| 文件 | 职责 | 关键符号 |
|---|---|---|
| `utils.py` | 确定性分词与 token 估算（CJK 单字/二元组 + 拉丁词） | `tokenize`、`estimate_tokens` |
| `schema.py` | 实现内部契约（与评测契约分开） | `Document`、`Chunk`、`Retrieved` |
| `config.py` | 引擎配置；`fingerprint()` 即 `config_hash` | `EngineConfig` |
| `ingest/loader.py` | 解析 → `Document`；`doc_id` 由来源派生；多项目 `load_tree` | `load_file`、`load_tree` |
| `ingest/chunker.py` | 固定长度切块 + overlap | `chunk_document(s)` |
| `embed/embedder.py` | Embedding 协议与实现 | `Embedder`、`HashingTfidfEmbedder`、`OpenAIEmbedder` |
| `index/vector_store.py` | 向量库协议与 numpy 后端（内积=余弦，可持久化/过滤） | `VectorStore`、`NumpyVectorStore` |
| `retrieve/dense.py` | Top-K 语义检索 | `DenseRetriever` |
| `generate/generator.py` | 带引用生成 + 拒答标记 | `Generator`、`ExtractiveGenerator`、`OpenAIGenerator` |
| `pipeline.py` | 组装 + manifest 持久化/重载 + 项目过滤 | `RAGPipeline`、`Answer`、`load_or_build` |
| `eval_adapter.py` | 接入评测协议的唯一连接点 | `MyPipeline` |

### 1.2 端到端数据流

```
data/kb/**（文档集 + proj-auth + proj-sched）
   │  ingest/loader.py      解析 -> Document(doc_id, source, doc_type, text, project_id)
   ▼
   │  ingest/chunker.py     滑窗 + overlap -> Chunk(chunk_id={doc_id}:{seq:04d}, start/end_line, symbol)
   ▼
   │  embed/embedder.py     HashingTfidf.embed -> L2 归一化向量
   ▼
   │  index/vector_store.py 内积索引（=余弦）
   ▼
   │  retrieve/dense.py     question -> 向量 -> top-k（按 project_id 过滤）
   ▼
   │  generate/generator.py 抽取式回答 + [chunk_id] 引用 + refused 标记
   ▼
Answer ──► eval_adapter.MyPipeline.answer(case, k) ──► SystemAnswer（评测协议）
```

### 1.3 已固化契约（后续不得破坏）

| 契约 | 内容 |
|---|---|
| 稳定 `chunk_id` | `f"{doc_id}:{seq:04d}"`，同文档同参数恒定 |
| 向量归一化 | Embedder 输出 L2 归一化 ⇒ 内积 = 余弦 |
| `config_hash` 随配置变 | `EngineConfig.fingerprint()` 进入报告 |
| 引用可回溯 | `citations` ⊆ 实际使用片段 |
| 系统与评测解耦 | 唯一连接点 `eval_adapter.MyPipeline.answer` |
| manifest 决定重建 | 源文件 sha256 + config 指纹 |

### 1.4 阶段一边界（本阶段不做）

清洗/去重、语义/层级切块、Parent-Child、Metadata Filtering、增量索引、BM25/Hybrid/RRF/Rerank/Rewrite、上下文压缩与 Token Budget、AST/符号索引、忠实度评测、FastAPI/MCP/Docker；默认不调用真实神经网络 Embedding/LLM（离线可复现）。

## 2. 实验平台（M0 本轮交付）

| 手册要求 | 落地 |
|---|---|
| 交付 B · Golden Dataset（答案+证据+难度；dev/val/blind） | ✅ `data/golden/cases.jsonl`，32 题，含 `gold_evidence(file/line/symbol)`、`query_type`、`difficulty`、`split`、`answer_rubric`、`adjudication` |
| 交付 C · 逐阶段 Trace / 配置快照 / 指标报告 | ✅ `rag_lab/trace.py`、`scripts/run_eval.py`、`snapshots/`、`reports/{run_id}/` |
| 2.1 数据分层（≥2 项目 + 文档集） | ✅ `data/kb/{proj-auth,proj-sched}` + 顶层文档，`project_id` 隔离 |
| 2.1 数据快照（文件 hash、排除规则） | ✅ `scripts/snapshot.py` |
| 3 指标（证据制） | ✅ 覆盖式 Recall/Precision/MRR/nDCG、Context Evidence Coverage、Answer Accuracy、No-answer Accuracy、Citation Support、宏/微平均 |
| 2.3/8 配对 bootstrap + 预声明门槛 | ✅ `scripts/run_eval.py --baseline` + `rag_eval/metrics.paired_bootstrap_ci` |
| 6 失败归因 | ✅ 每题 `first_failure_stage` 初判 + `errors.csv` |

### 2.1 新增基础设施

| 路径 | 作用 |
|---|---|
| `rag_lab/` | 实验平台包（config / golden / scoring / trace） |
| `scripts/snapshot.py` | 数据快照（sha256、排除 node_modules/.git/密钥） |
| `scripts/run_eval.py` | 配置驱动实验运行器（E00–E12 通用） |
| `configs/E00.yaml` | 固定基线配置 |
| `data/golden/cases.jsonl` | Golden Dataset v2 |
| `data/kb/` | 多项目知识库（2 个代码项目 + 文档集） |
| `rag_eval/evidence.py` | 证据映射与覆盖判定（v2 固定资产） |

### 2.2 R0 架构图

用 [Archify](https://github.com/tt-a1i/archify)（本地部署于 `<archify>`）从本仓库实际结构生成：

```powershell
node <archify>\bin\archify.mjs finalize architecture `
  docs\reports\R0\diagrams\round-0.architecture.json docs\reports\R0\diagrams\round-0.architecture.html `
  --quality showcase --json
```

- 源文件：`docs/reports/R0/diagrams/round-0.architecture.json`（Typed JSON IR，可继续迭代）
- 成品：`docs/reports/R0/diagrams/round-0.architecture.html`（自包含交互式 HTML，可直接浏览器打开）
- 门禁：`validate / deliver / check / browser-check` 全部 pass

## 3. E00 基线数值（冻结）

**E00 = 固定块(400 字符, overlap 80) + 单路 Dense Top-5，无重排。** 全部 32 题。

| 指标 | 值 | 说明 |
|---|---|---|
| `recall@5` | 0.8148 | 覆盖式：至少一组充分证据被前 5 覆盖 |
| `precision@5` | 0.3475 | 前 5 中命中证据的比例 |
| `mrr@5` | 0.7840 | 首个命中名次倒数 |
| `ndcg@5` | 0.8965 | 0/1/2 等级 |
| `context_evidence_coverage` | 0.8148 | 最终上下文覆盖 |
| `answer_accuracy` | 0.6875 | rubric 代理（召回覆盖 且 有引用） |
| `no_answer_accuracy` | 0.0 | **拒答机制缺失（见 §6）** |
| `citation_support` | 0.3475 | 引用命中证据比例 |
| `p95_latency_ms` | 0.379 | 离线，无网络/LLM |
| `trace_completeness` | 1.0 | 全部 case 有召回记录 |

> 分组指标（题型 × 指标）见 `reports/{run_id}/comparison.md`。

## 4. 已验证行为（证据）

- **L1**：`python -m pytest -q` → **45 passed**。
- **E00 可重放**：同配置 + 同数据快照 ⇒ 同 run_id 前缀、同指标。
- **A/B 配对**：临时用 `chunk_size=256` 对照验证了配对 bootstrap 与 CI 渲染（因样例小结论"证据不足"），产物 `comparison.md` 生成正常。
- **协议自检**：桩系统 `stub_dense`/`stub_hybrid` 仍可运行，`rag_eval` 不依赖 `rag_engine`。
- **修复记录（本轮）**：① loader 未含 `.py` 导致代码未入索引；② nDCG 因重复命中同一证据而 >1。均已修并加测试。

## 5. 与后续的区分（演进映射）

| 文件 / 资产 | 本轮（R0）形态 | 后续实验/阶段会怎么动 | 必须保留的不变量 |
|---|---|---|---|
| `config.py` | 切块/嵌入/检索/生成 + 路径 | E02 增切块参数；E04 换 embedding；E05 增 hybrid/rerank | `fingerprint()` 语义 |
| `ingest/loader.py` | TXT/MD/PY/PDF → Document；`load_tree` | E01 增 AST 解析器（新文件） | `doc_id` 稳定、来源相对路径 |
| `ingest/chunker.py` | 固定长度 + overlap（附行号） | E02/E03 增 token/Symbol/层级块 | `chunk_id` 规则、行号字段 |
| `embed/embedder.py` | 离线 hashing-tfidf + 可选 OpenAI | **E04** 默认切真实语义向量（换实现，不改接口） | `Embedder` 协议 + L2 归一化 |
| `index/vector_store.py` | numpy 内积 + `flt` | E05 增 `bm25_store.py`；E10 增量 | `VectorStore` 协议、`search` 语义 |
| `retrieve/dense.py` | 纯向量 Top-K | E05/E06/E07/E08 并列 hybrid/rerank/rewrite/parent-child | `retrieve(question, k, flt)` 形状 |
| `generate/generator.py` | 检索结果 → 引用回答 | E09 由 `context/builder.py` 组织上下文；E05 补拒答 | 引用可回溯 |
| `pipeline.py` | 建索引 + 查询 + manifest | E10 接增量；E12 增 http 适配 | `answer(question, k) -> Answer` 形状 |
| `eval_adapter.py` | `MyPipeline`（离线） | E11 补 project 隔离断言；E12 增 `http_pipeline` | `Sut` 契约不变 |
| `rag_lab/`、`rag_eval/evidence.py` | M0 平台 | 每轮扩展（新指标/新 trace 字段），口径变更须 bump `EVAL_VERSION` | 证据制口径、run_id 可复现 |
| `data/golden/cases.jsonl` | 32 题种子标注 | 每轮**只增不改**旧题 | sha256 冻结纪律 |
| `data/kb/` | 2 项目 + 文档集 | 可扩项目/更新文件（E10） | `project_id` 隔离 |
| `baselines/`、`reports/` | 追加式 | 追加式 | 不覆盖 |

## 6. 已知缺口（留给后续轮次）

1. **拒答机制缺失 → `no_answer_accuracy = 0`（E05/生成侧）**：`min_relevance=0` 使任何查询都返回结果。
2. **`answer_accuracy` / `citation_support` 是代理口径（E09/生成侧）**：未接 LLM 裁判。
3. **Embedding 仍是离线 hashing-tfidf（E04）**：A/B 需真实模型/API。
4. **切块按字符，手册 E00 为 512 tokens（E02）**：是否引入 tokenizer 待定。
5. **尚无重排/BM25/Rewrite/上下文扩展（E05–E09）**。
6. **`adjudication.reviewed=false`**：Golden 为种子标注，需人工复核后才可作最终盲测集。
7. **PDF 未实测**：环境缺 PyMuPDF/pypdf。
8. **整目录重建**：`manifest` 变化即全量重建；真正增量在 E10。

## 7. 复现命令

```powershell
# 机制测试
python -m pytest -q

# 数据快照
python scripts/snapshot.py --root data/kb --name kb

# E00 基线
python scripts/run_eval.py --config configs/E00.yaml

# 与基线做 A/B（示例：改切块/检索后）
python scripts/run_eval.py --config configs/E0x.yaml --baseline <E00_run_id>
```

## 后续变更

（E01 及以后改动系统/平台/指标口径时在此追加，不修改正文。）

### 后续变更 · 2026-10-11 · `config_hash` 改为便携口径

- **触发原因**：本记录 §0 的 `config_hash=e821df85555c` 在新机器/新目录下**无法复现**。
- **定位**：`EngineConfig.fingerprint()` 原为 `sha256(asdict(config))`，`asdict` 含 **`index_dir` 绝对路径**；
  `eval_adapter.MyPipeline._ensure()` 会把 `index_dir` 替换为绝对路径，故仓库一换目录/机器，`config_hash` 即变
  （实测：同一 E00 配置在 `实践项目合集/rag-lab` 得 `d8c850de19d5`、在临时 worktree 得 `01197359d212`，均与记录值不同）。
  该值只影响 `run_id` 的组成，**不影响任何指标**。
- **改动（方案 A）**：`rag_engine/config.py` 新增 `NON_SEMANTIC_FIELDS = {"index_dir","raw_dir"}`，
  `fingerprint()` 只哈希**语义参数**（切块/嵌入/检索/生成），路径不参与。E00 新指纹 = `483d64cf78e9`。
- **验证**：`pytest` 77 passed；同一配置换任意路径 ⇒ 同指纹（便携 ✅）；改 `chunk_size` ⇒ 指纹变（仍随语义变化 ✅）；
  `run_eval --config configs/E00.yaml` ⇒ `recall@5=0.8148 / mrr@5=0.7840 / ndcg@5=0.8965`（与冻结值一致）。
- **兼容性声明**：本记录 §0 的 `e821df85555c` 与所有历史 `config_hash` 由**旧口径（含绝对路径）**产生，
  **不可与旧值直接比较**；新口径下的等价值为 `483d64cf78e9`。指标口径未变（`EVAL_VERSION` 仍为 `v2`）。
