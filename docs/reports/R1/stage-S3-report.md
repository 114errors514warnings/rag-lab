# rag-lab · S3 阶段报告 · 检索质量优化（BM25 / Hybrid / Rerank / Rewrite）

- 阶段：S3（系统侧阶段三）
- 轮次归属：R1（阶段二 + 阶段三前半）
- 状态：⚠️ **未达标**（3 次测试后记录原因，按协议进入下一阶段）
- 日期：2026-10-11
- 架构说明：[`stage-S3-architecture.md`](stage-S3-architecture.md)
- 架构图（Archify）：`../../.archify/architecture-s3-retrieval-20261011-043000/s3-retrieval-architecture.html`

## 1. 目标
BM25、Dense+Sparse Hybrid（RRF）、Cross-Encoder/API Rerank、Query Rewrite/Multi-query；
对 Dense / BM25 / Hybrid / Rerank 各跑一次并横向对比；主指标达标且护栏不越线。

## 2. 交付物

| 文件 | 职责 |
|---|---|
| `rag_engine/index/bm25_store.py` | BM25（中英分词：ASCII 词 + 中文 2-gram；k1=1.5,b=0.75；先过滤后排序） |
| `rag_engine/retrieve/sparse.py` | `SparseRetriever` |
| `rag_engine/retrieve/hybrid.py` | `rrf_fuse`（Σ1/(k+rank)）+ `HybridRetriever` |
| `rag_engine/retrieve/rerank.py` | `LexicalReranker`（Cross-Encoder 的离线确定性替身） |
| `rag_engine/retrieve/rewrite.py` | `rewrite` / `multi_query`（中→英术语扩展） |
| `tests/test_hybrid_rrf.py` | L1：RRF 确定性、Hybrid 合并 |
| `rag_engine/eval_adapter.py` / `eval_demo.py` | 四方案系统：`demo_dense` / `demo_hybrid` / `demo_rerank` / `demo_multi`（对齐 retrieval_v1 语料） |

## 3. 测试方法
- **L1**：`python -m pytest -q` → **59 passed**（新增 4 项）。
- **L2**：`python -m rag_eval.runner --stage S3 --system <方案> --baseline S3__demo_dense`
  - 主：`mrr Δ≥+0.10`、`recall@3 Δ≥+0.05`；护栏：`p95 ≤ 500ms`、`cost ≤ $0.005`。

## 4. 结果（3 次测试）

基线 `demo_dense`（真实 hashing-tfidf Dense，demo 语料）：`mrr=0.7417`、`recall@3=0.85`、`p95=0.085ms`。

| 轮次 | 方案 | mrr Δ | recall@3 Δ | 护栏 | 判定 |
|---|---|---|---|---|---|
| 1 | demo_hybrid（Dense+BM25 RRF） | **+0.0166** | +0.0500 | PASS | ❌ FAIL（mrr < 0.10） |
| 2 | demo_rerank（Hybrid+词面重排） | **+0.0333** | +0.0500 | PASS | ❌ FAIL（mrr < 0.10） |
| 3 | demo_multi（多查询融合+重排） | **+0.0333** | +0.0500 | PASS | ❌ FAIL（mrr < 0.10） |

退出码均为 1。

## 5. 失败原因（归因，协议要求记录）

1. **基线已接近该套件上限**：`retrieval_v1` 仅 20 题、语料 21 个 chunk 且题目关键词与相关 chunk 词面高度重叠；真实 Dense（hashing-tfidf，带 IDF/余弦）已达 `mrr=0.7417`、`recall@3=0.85`。
   在如此小的、易对齐的套件上，**排序再提升 +0.10 的空间很小**（`stub_dense` 之所以能从 0.7083 提到 0.95，是因为它被刻意设计为"无 IDF、无 bigram"的弱基线）。
2. **召回已先到上限**：Hybrid/Rerank/Multi 已把 `recall@3` 从 0.85 提到 0.90（Δ=+0.05 PASS），说明剩余误差主要是"相关 chunk 已在 top-3、但未排到第 1"，而 MRR 只看"首个相关的名次"，对这类误差不敏感于小改动。
3. **数据集/系统对齐缺陷**：`retrieval_v1` 的 `relevant_chunk_ids`（c01…）对齐 `data/corpus/demo.jsonl`，而真实 `my_pipeline` 索引项目 kb（chunk_id 形如 `rag-md-…:0000`），二者不对齐 → 直接跑 `my_pipeline` 时 `mrr=0`。本次已用**真实引擎**在 demo 语料上建立 `demo_*` 系统，使对比成立；但这也说明**该套件对真实系统的判别力有限**。

**结论**：护栏与 `recall@3` 达标、`mrr` 未达 +0.10。按协议"3 次未通过则记录原因并进入下一阶段"，本阶段标记为**未达标**，保留全部交付物与四方案对比数据；后续在 S6 通过**扩充/重标定检索套件**（更大、更难、真实 corpus 对齐）后再复核 MRR 门禁。

## 6. 边界与不做
- Rerank 用离线词面替身（无 Cross-Encoder 依赖）；真实 Cross-Encoder 接入接口已留（`LexicalReranker` 同签名）。
- 不改 `retrieval_v1`（数据集冻结）；不改 `gates.json`（阶段中途不得放宽）。
- `S3__my_pipeline.json`（kb 语料、mrr=0）为对齐缺陷产生的无效基线，仅作留痕。

## 7. 演进映射
- `context/builder.py` → S4。
- 套件扩充/重标定 + 真实 corpus 对齐 → S6。
- `code_rag/*`、`service/*` → S5 / S7。
