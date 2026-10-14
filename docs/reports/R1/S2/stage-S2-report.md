# rag-lab · S2 阶段报告 · 文档处理与索引优化

- 阶段：S2（系统侧《implementation-plan》阶段二）
- 轮次归属：R1（阶段二 + 阶段三前半）
- 状态：✅ 已完成（L1 + L2 通过）
- 日期：2026-10-11
- 架构说明：[`stage-S2-architecture.md`](stage-S2-architecture.md)
- 架构图（Archify）：`../../../../.archify/architecture-s2-index-20261011-040000/s2-index-architecture.html`

## 1. 目标（清单项）
清洗/去重/格式统一；固定长度 vs 语义 vs 层级切块；Chunk Metadata；Metadata Filtering；
Parent-Child；更新/删除/增量索引——**只重建受影响的索引**。

## 2. 交付物

| 文件 | 职责 |
|---|---|
| `rag_engine/ingest/clean.py` | `normalize_text` / `content_hash` / `clean_documents` / `dedupe_documents`（同源留最新、跨源内容去重） |
| `rag_engine/ingest/metadata.py` | `section_at` / `build_chunk_meta`（source/section/position/updated_at/project_id/trust + 定位） |
| `rag_engine/ingest/chunker.py`（扩展） | `chunk_hierarchical`：父块 + 子块（`meta.parent_id`），id 稳定 |
| `rag_engine/retrieve/filters.py` | `matches` / `filter_chunks` / `oversample_k`（过滤前置语义） |
| `rag_engine/retrieve/parent_child.py` | `build_parent_map` / `ParentChildRetriever` |
| `rag_engine/index/indexer.py` | `IncrementalIndexer` + `IndexUpdate`：以 `doc_id` diff，只重建 added/changed，删除 removed/changed 旧切片 |
| `rag_engine/index/vector_store.py`（扩展） | `remove_doc_ids`：仅行切片，保留行向量逐字节不变 |
| `rag_engine/pipeline.py`（接入） | 建索引路径加入 清洗 → 去重 → 元数据 enrichment（切块契约与 `chunk_id` 不变） |
| `tests/test_incremental_index.py` | L1：只重建受影响切片、其余向量逐字节不变、增删改、状态持久化 |
| `tests/test_metadata_filter.py` | L1：过滤后 100% 命中满足条件；matches/oversample 语义 |

## 3. 测试方法

- **L1**：`python -m pytest -q` → **51 passed**（新增 6 项）。
- **L2 门禁**：`python -m rag_eval.runner --stage S2 --system my_pipeline --baseline S1__my_pipeline`

## 4. 结果

| 门禁 / 检查 | 基线 | 本次 | Δ | 判定 |
|---|---|---|---|---|
| `error_rate`（主） | 0.0 | 0.0 | +0.0000 | **PASS** |
| `citation_missing_rate`（护栏） | 0.0 | 0.0 | +0.0000 | **PASS** |
| L1 增量索引：仅重建受影响切片 | — | — | — | PASS |
| L1 增量索引：其余向量逐字节不变 | — | — | — | PASS |
| L1 元数据过滤：命中 100% 满足条件 | — | — | — | PASS |

退出码 0。

## 5. 测试轮次与失败记录

| 轮次 | 结果 | 原因 |
|---|---|---|
| 第 1 次 | L2 FAIL | `(suite_sha256)` 不一致：仓库初始提交中 **S1 基线与 smoke_v1 套件的哈希不匹配**（基线 486dcb20 vs 当前 7338945f），Δ 被作废 |
| 处理 | — | 备份旧基线为 `baselines/_invalid_S1__my_pipeline_suite486dcb20.json`；用**原始 S1 流水线**（`git stash` 掉 S2 改动后 `--freeze`）在**当前套件**上重新冻结有效基线 |
| 第 2 次 | **PASS** | 退出码 0，两门禁均 PASS |

> 说明：第 1 次失败是**仓库既有数据缺陷**（同一提交内基线/套件哈希不自洽），非 S2 代码问题；已按"基线只读、新基线=新文件"的纪律备份旧文件并重冻有效基线。

## 6. DoD 核对
- ✅ 改动 1 个文档仅重建受影响切片（L1 断言嵌入文本 = 该文档切片）；
- ✅ 可按来源/项目过滤（`store.search(..., flt=...)` + `filters` 语义）；
- ✅ 答案可回溯到 `source + position`（元数据含 source/section/position/行号）。

## 7. 边界与不做
- 语义/层级切块当前以「层级（Parent-Child）」落地；语义切块（按嵌入相似度断句）留待 S3 之后按证据引入。
- 增量索引为**全量 diff**（按 `doc_id` 指纹）而非文件系统事件监听；文件监听属后续工程项。
- S2 的 L2 是**回归门禁**，机制正确性由 L1 承担（协议既定）。

## 8. 演进映射（后续会改哪些文件）
- `index/bm25_store.py`、`retrieve/{sparse,hybrid,rerank,rewrite}.py` → S3。
- `context/builder.py` → S4。
- `code_rag/*` + `data/eval_suites/code_v1.jsonl` → S5。
- `service/*`、`Dockerfile` → S7。

---

## 9. 后续变更（2026-10-11）

> 按《实践项目合集·统一开发准则》第 2 条：历史报告**只追加、不改写**。以上正文保持原样。

- **触发原因**：RAG 实验线建基线时发现 **E00 不复现**（R0 冻结 `recall@5=0.8148` → 现行代码 `0.7407`）。
- **定位（二分）**：R0 worktree 复现 0.8148；现仓库逐项还原后定位到 `rag_engine/pipeline.build` 新增的
  `clean_documents`。根因：`ingest/clean.py::normalize_text` 的"连续空行压缩"会**删行**，使 `gold_evidence`
  （file/line 区间）行号错位 → 覆盖式 recall 假性下降（去重与元数据 enrichment 无责）。
- **改动**：`normalize_text` 改为**仅做 BOM 去除 + 换行归一，保持行数不变**（不再压缩空行、不再逐行 rstrip）。
  S2 的"清洗 + 去重 + 元数据 enrichment"仍保留。
- **复测**：`python -m pytest -q` → **77 passed**；`run_eval --config configs/E00.yaml` →
  `recall@5=0.8148 / mrr@5=0.7840 / ndcg@5=0.8965 / answer_accuracy=0.6875`（**与 R0 冻结值一致**）。
- **影响面**：S2 的 L1/L2 结论不变；证据制评测不再受清洗影响；后续 E 线可在稳定基线上推进。
