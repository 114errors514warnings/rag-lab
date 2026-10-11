# rag-lab · E03 架构说明 · 符号级切块（未通过）

> 报告：[`stage-E03-report.md`](stage-E03-report.md)
> **次要阶段**：架构以树形文档表示（未生成 Archify 图）。

## 1. 切块模式（树）

```
rag_engine/config.py  EngineConfig.chunking ∈ {fixed, symbol}
        │
        ▼
rag_engine/pipeline.py::RAGPipeline.build
├── chunking == "fixed"  → ingest/chunker.chunk_documents(size, overlap)
└── chunking == "symbol" → ingest/symbol_chunker.chunk_documents_symbol(size, overlap)
        ├── .py  → AST 顶层：FunctionDef→function；ClassDef→class + 类体函数→method
        │          块头 meta = {symbol, kind, file, start/end, start_line/end_line, project_id}
        └── 其它 → 回退 ingest/chunker.chunk_document（定长）
        （符号块跳过定长元数据 enrichment）
```

## 2. 关键契约
- `chunk_id = f"{doc_id}:{seq:04d}"`，序号连续、稳定（与非符号模式同一命名空间，按文档隔离）。
- 符号块 `meta`：`symbol` / `kind ∈ {function,class,method}` / `file` / `start_line` / `end_line` / `source` / `project_id`。
- 非代码或语法错误 ⇒ 回退定长（`chunk_document_symbols` 返回空）。

## 3. 已知缺陷（本阶段未通过的原因）
- **模块级行未覆盖**：imports / docstring / 常量 / 顶层语句不属任何符号 → 无块承载 ⇒ 证据行不可检索。
- 修复方向：新增"模块剩余块"（`meta.kind="module"`），补齐未覆盖区段。

## 4. 不变量与边界
- 不变量：符号块 id 稳定；非代码回退不改变定长契约。
- 边界：仅 `.py`；不影响嵌入/检索/生成接口；`config_hash` 因新增 `chunking` 字段而全面变化（语义参数）。
