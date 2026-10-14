# 轮次记录 · R1（解析 / 切块 / 召回 + 系统 S2–S3）

> 轮次 R1 对应 E01–E05 与系统侧阶段二 + 阶段三前半。**本轮尚未完成**（E04/E05 未做），
> 这是**滚动快照**：完成的部分先冻结，后续在此**追加**，不改写。
> 记录约定见 [`../../../guide/records-convention.md`](../../../guide/records-convention.md)；开发纪律见 [`../../../guide/统一开发准则.md`](../../../guide/统一开发准则.md)。

## 0. 元信息

| 项 | 值 |
|---|---|
| 轮次 | R1 |
| 状态 | 🟡 进行中 |
| 日期 | 2026-10-11（各阶段） |
| 系统侧 | S2 ✅ / S3 ✅（首轮未达标，后经改写+重排达标） |
| 实验侧 | E01 ✅ / E02 ✅ / **E03 ❌ 未通过（待修）** / E04 ⬜ / E05 ⬜ |
| 评测协议 | `EVAL_VERSION = v2`（证据制，本轮未变） |
| L1 测试 | 当前 `python -m pytest -q` → **92 passed** |
| 关键基线 | E00 `recall@5=0.8148` → E02(512/80) `0.8519` |

## 1. 系统侧交付（S2 / S3）

### S2 · 文档处理与索引优化（✅）

| 文件 | 职责 |
|---|---|
| `ingest/clean.py` | `normalize_text` / `content_hash` / `clean_documents` / `dedupe_documents` |
| `ingest/metadata.py` | `section_at` / `build_chunk_meta`（source/section/position/updated_at/project_id/trust） |
| `ingest/chunker.py`（扩展） | `chunk_hierarchical`：父块 + 子块（`meta.parent_id`） |
| `retrieve/filters.py` | `matches` / `filter_chunks` / `oversample_k`（过滤前置语义） |
| `retrieve/parent_child.py` | `build_parent_map` / `ParentChildRetriever` |
| `index/indexer.py` | `IncrementalIndexer` / `IndexUpdate`：按 `doc_id` diff，只重建增改、删除旧切片 |
| `index/vector_store.py`（扩展） | `remove_doc_ids`：仅删行，其余行向量逐字节不变 |

- L1：新增增量索引、元数据过滤断言；L2 回归门禁 PASS（`error_rate=0`，`citation_missing_rate` 不退化）。
- **后续变更**：清洗曾导致行号错位（`recall@5` 假性降到 0.7407），已改为**保持行数不变**的清洗，复测回到 `0.8148`。详见 `S2/stage-S2-report.md` §9。

### S3 · 检索质量优化（✅，经修复后达标）

| 文件 | 职责 |
|---|---|
| `index/bm25_store.py` | BM25（ASCII 词 + 中文 2-gram；先过滤后排序） |
| `retrieve/sparse.py` | `SparseRetriever` |
| `retrieve/hybrid.py` | `rrf_fuse`（Σ1/(k+rank)）+ `HybridRetriever` |
| `retrieve/rerank.py` | `LexicalReranker`（离线替身）+ `IdfReranker` |
| `retrieve/rewrite.py` | `rewrite` / `multi_query`（中→英术语扩展） |

- **首轮 3 次未达标**（`mrr Δ<0.10`）：基线在该小套件上已接近上限、且 `retrieval_v1` 与真实 kb 语料不对齐。
- **修复后达标**：扩术语表 + IDF 重排 + 多查询融合 → `demo_multi` 系统 `mrr 0.7417→0.9667`、`recall@3 0.85→0.975`，exit 0。详见 `S3/stage-S3-report.md` §8。

## 2. 实验侧交付（E01 / E02 / E03）

| 实验 | 主变量 | 交付 | 结论 |
|---|---|---|---|
| **E01** | 解析器契约（不改系统行为） | `tests/test_parser_contract.py`、`configs/E01.yaml` | ✅ PASS，`recall@5` 持平 0.8148 |
| **E02** | 切块 `size/overlap`（256/512 vs 400） | `configs/E02_{256,512}.yaml`、`configs/E02.yaml`、`tests/test_chunk_params.py` | ✅ PASS，512/80 → `recall@5 0.8148→0.8519` |
| **E03** | 符号级切块（AST 函数/类/方法） | `ingest/symbol_chunker.py`、`tests/test_symbol_chunking.py`、`configs/E03.yaml` | ❌ **未通过**，`recall@5 0.8519→0.5926` |

## 3. 关键数值一览

| 阶段 | 主指标 | 基线 | 本次 | Δ | 判定 |
|---|---|---|---|---|---|
| E01 | `recall@5` | 0.8148 | 0.8148 | +0.0000 | PASS |
| E02 | `recall@5` | 0.8148 | 0.8519 | **+0.0371** | PASS |
| E03 | `recall@5` | 0.8519 | 0.5926 | **−0.2593** | **FAIL** |
| S3（demo 语料） | `mrr` | 0.7417 | 0.9667 | **+0.2250** | PASS（修复后） |

## 4. 契约与口径变化

1. **E03 引入 `config.chunking`（`fixed`\|`symbol`）** ⇒ `EngineConfig` 结构变化，**所有配置的 `config_hash` 随之变化**（含 E00/E01/E02）。历史报告的 `config_hash` 与现口径**不可直接比较**。
2. **评测口径未变**：`EVAL_VERSION` 仍为 `v2`；证据制、覆盖式 recall、配对 bootstrap 均沿用。
3. **S2 清洗语义变更**：`normalize_text` 从"压缩空行"改为"保持行数"，属实现修正，不改变指标定义。
4. 冻结纪律未破：数据集、基线只读；新基线 = 新文件。

## 5. 未闭环问题

1. **E03 未通过（阻塞 R1 收尾）**
   - 根因（实测）：符号块只覆盖函数/类/方法体，**丢失模块级区域**（imports / docstring / 常量 / 顶层语句），落在这些行的 `gold_evidence` 无法被检索。
   - 修法（见 `../../E/E03/stage-E03-report.md` §5）：为代码文件补**"模块剩余块"**（`meta.kind="module"`），或采用 **定长 ∪ 符号** 并集；修后复测并转绿。
2. **`retrieval_v1` 与真实 kb 语料不对齐**：其 `relevant_chunk_ids` 指向 demo 语料，直接跑真实 `my_pipeline` 时 `mrr=0`。S3 已用 `demo_*` 系统使对比成立；根治在 **S6 扩充/重标定检索套件**。

## 6. 边界（本轮未做）

- **E04（Embedding）未做**：需先决定"真实本地模型 / API / 暂保持离线（记 `BASELINE`）"。
- **E05（Dense/BM25/Hybrid + 拒答）未做**：`sparse/hybrid` 已在 S3 实现，待接入选型与 `min_relevance` 拒答（顺带修 `no_answer_accuracy=0`）。
- 语义切块（按嵌入相似度断句）留待 E04 之后；增量监听为全量 diff，非文件事件。
- PDF 解析未实测（环境缺解析库）。

## 7. 演进映射

| 文件 / 资产 | 本轮形态 | 后续会怎么动 |
|---|---|---|
| `configs/E03.yaml` / `ingest/symbol_chunker.py` | 符号块，缺模块级 | E03 修复：补"模块剩余块"或定长∪符号 |
| `embed/embedder.py` | 离线 hashing-tfidf | **E04** 换真实语义向量（可选后端，接口不变） |
| `retrieve/{sparse,hybrid}.py` | 已在 S3 实现 | **E05** 接入 `system.retrieval` 选型 + `min_relevance` 拒答 |
| `configs/` | E00–E03 | 增 `E04.yaml`、`E05_{dense,bm25,hybrid}.yaml` |
| `data/eval_suites/` | 冻结 | S6 扩充/重标定（新套件 = 新文件） |

## 8. 复现命令

```powershell
# L1
python -m pytest -q

# 本轮各阶段（与冻结基线配对）
python scripts/run_eval.py --config configs/E01.yaml --baseline <E00 run_id>
python scripts/run_eval.py --config configs/E02.yaml --baseline <E00 run_id>
python scripts/run_eval.py --config configs/E03.yaml --baseline <E02 run_id>
```

## 后续变更

（E04/E05 完成后在此追加，不改写正文。）

### 2026-10-14 · E03 修复尝试（模块剩余块）

按 `../../E/E03/stage-E03-report.md` §5 补了"模块剩余块"（`kind="module"`）。复测：`recall@5 0.5926→0.8148`（回到 E00 定长水平），
但相对 E02(512/80) 仍 `recall@5 −0.0371`、`mrr@5 −0.0216`，**门禁仍 FAIL**（逐题仅差 1 题：少覆盖 A13/A18，多覆盖 B06）。
根因：覆盖式 `recall@5` 对多证据题偏好更粗的块，符号块粒度更细。L1 94 passed。
待决策方案见该报告 §8（并集 / 按预算合并 / 保持未达标先推进 E04–E05）。

### 2026-10-14 · E03 尝试 3（符号 ∪ 非冗余定长）→ 仍未达标

按方案 (A) 实现 `chunking=symbol_union`（`configs/E03_union.yaml`）。复测：`recall@5=0.7037`（−0.1481，**FAIL**）、
`mrr@5=0.7870`（PASS）、`p95=0.395`（PASS）；L1 **96 passed**。粗粒度定长块成为干扰、把正确符号块挤出 top-5。
**3 次尝试均未超过 E02(0.8519)，E03 记为未达标**；`symbol`/`symbol_union` 作为可选模式保留，R1 按计划推进 E05。
