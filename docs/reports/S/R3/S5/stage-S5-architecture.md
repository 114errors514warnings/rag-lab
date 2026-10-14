# rag-lab · S5 架构说明 · Code RAG

> 报告：[`stage-S5-report.md`](stage-S5-report.md)
> 架构图（Archify，全闸门通过）：`../../../../../.archify/architecture-s5-code-20261011-124500/s5-code-architecture.html`

## 1. 组件与职责
| 组件 | 职责 | 文件 |
|---|---|---|
| scanner | 递归列出 `.py` | `code_rag/ast_indexer.py::scan_python_files` |
| ast_indexer | 顶层函数→function、类→class、类体函数→method；块头 meta | `code_rag/ast_indexer.py::extract_symbols` |
| deps | 由 meta.deps 构建 callers/callees 图 | `code_rag/deps.py` |

## 2. 数据流
```
data/code_corpus/<project>/*.py ─▶ scan ─▶ AST ─▶ Symbol Chunk
   meta = {symbol, kind, file, project_id, start_line, end_line, deps}
        ─▶ Dense/BM25 ─▶ 按 project_id 过滤 ─▶ 回答 / get_symbol
```

## 3. 关键契约
- `chunk_id = f"{project_id}:{rel_in_project}:{symbol}"`（稳定、可复现）。
- `chunk.meta["deps"]`：被调用名 + 导入模块名。
- `build_dependency_graph(chunks) -> {symbol: {kind, file, project_id, callers[], callees[]}}`。

## 4. 隔离契约（硬）
- 检索一律 `flt={"project_id": case.project_id}`（前置过滤）；
- `leakage_rate` = 命中中非目标 project 的比例，必须为 0。

## 5. 套件
`data/eval_suites/code_v1.jsonl`：`{id, question, expected_symbols[], relevant_chunk_ids[], project_id, split}`，含 proj-alpha / proj-beta 两项目。

## 6. 边界与演进
- 静态 AST，无类型推断/动态调用；Tree-sitter 与增量监听留待后续。
- `get_symbol` 的服务化见 S7 `service/api.py` 与 `service/mcp_server.py`。
