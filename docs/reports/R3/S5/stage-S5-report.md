# rag-lab · S5 阶段报告 · Code RAG 专项

- 阶段：S5｜轮次：R3
- 状态：✅ 完成（L1 + L2 通过，1 次通过）
- 日期：2026-10-11
- 架构说明：[`stage-S5-architecture.md`](stage-S5-architecture.md)
- 架构图（Archify）：`../../../../.archify/architecture-s5-code-20261011-124500/s5-code-architecture.html`

## 1. 目标
扫描代码、AST 结构化切块（函数/类/方法）、符号索引、依赖关系、多项目隔离；自然语言可定位函数，任意用例不混入其它项目。

## 2. 交付物
| 文件 | 职责 |
|---|---|
| `code_rag/ast_indexer.py` | `scan_python_files` / `extract_symbols` / `index_code`：块头写 `symbol/kind/file/span/deps`；chunk_id=`{project}:{file}:{symbol}` |
| `code_rag/deps.py` | `build_dependency_graph`：callers/callees |
| `code_rag/__init__.py` | 导出 |
| `data/code_corpus/{proj-alpha,proj-beta}/*.py` | 两个项目的代码语料（隔离前提） |
| `data/eval_suites/code_v1.jsonl` | 10 题（含 `expected_symbols` + `relevant_chunk_ids` + `project_id` + dev/holdout） |
| `rag_engine/eval_code.py` | `code_rag` / `code_rag_hybrid` 系统 |
| `tests/test_code_symbols.py`、`tests/test_isolation.py` | L1：符号提取、依赖图、项目隔离 |

## 3. 测试方法
- L1：`python -m pytest -q` → **72 passed**（新增 5 项）。
- L2：`python -m rag_eval.runner --stage S5 --system code_rag_hybrid --baseline S5__code_rag`（code_v1, k=10）

## 4. 结果
| 门禁 | 基线 | 本次 | Δ | 判定 |
|---|---|---|---|---|
| `recall@10`（主） | 0.6 | 0.7 | **+0.1000** | **PASS** |
| `leakage_rate`（护栏 = 0） | 0.0 | 0.0 | +0.0000 | **PASS** |

退出码 0。**1 次通过**（另有 1 次 L1 失败：AST 初版用 `ast.walk` 导致方法被当作 function 且 chunk_id 重复 project 前缀；改为按 `tree.body` 顶层结构切分 + `rel_in_project` 后通过）。

## 5. 边界与不做
- 未接 Tree-sitter（正则/AST 已满足当前符号粒度）；Git 变更增量留待工程化。
- `span` 用 AST 行号；`get_symbol` 的 callers/callees 来自静态调用点，不做动态分析。

## 6. 演进映射
- `service/*`、`Dockerfile`（S7）；CI 门禁（S6）。
