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

---

## 后续变更 · 架构说明整篇重述（2026-10-14）

> 按《实践项目合集·统一开发准则》第 3 条：架构说明被改动时在末尾追加「后续变更」并**整篇重述**（标注修改时间），**不改动上文原文**。
> 触发：E03 两次修复尝试（① 模块剩余块；② 符号 ∪ 定长）已落地，上文 §1 只描述 `fixed`/`symbol` 两种模式，已过时。以下为**修改后的完整架构说明**。

### 1. 切块模式（树 · 2026-10-14 版）

```
rag_engine/config.py  EngineConfig.chunking ∈ {fixed, symbol, symbol_union}
        │
        ▼
rag_engine/pipeline.py::RAGPipeline.build
├── "fixed"        → ingest/chunker.chunk_documents(size, overlap)
├── "symbol"       → ingest/symbol_chunker.chunk_documents_symbol(size, overlap)
└── "symbol_union" → ingest/symbol_chunker.chunk_documents_symbol_union(size, overlap)
        │
        ├── .py  → AST 顶层：FunctionDef/AsyncFunctionDef→function；
        │          ClassDef→class + 类体函数→method；
        │          补「模块剩余块」：不属任何符号、且连续的行区段 → kind="module"
        │          （`_node_span` 含装饰器行；符号块+模块块按起始行排序后统一编号）
        └── 其它 / SyntaxError → 回退 ingest/chunker.chunk_document（定长）
        │
        ▼
元数据 enrichment：跳过**自带 `kind`** 的块（符号块/模块块），仅定长块补 `build_chunk_meta`
   （`symbol_union` 保留的定长块同样走 enrichment）

symbol_union = symbol(含模块) ∪ 非冗余定长
  · 定长块若被**任一**符号/模块块"完整包含" → 视为冗余丢弃
  · 保留的定长块 id 加 `F` 前缀：`{doc_id}:F{seq:04d}`
```

### 2. 符号切块内部结构（`ingest/symbol_chunker.py`）

```
_node_span(node)                 # (start_line, end_line)，含装饰器行
_module_spans(lines, spans)      # 未被任何符号覆盖、且连续、去首尾空白后仍非空的区段
chunk_document_symbols(doc)      # .py → [符号块 + 模块块]；非 py / 语法错误 → []
chunk_documents_symbol(...)      # 逐文档；空则回退定长
chunk_documents_symbol_union(...)  # 符号(+模块)块 ∪ 非冗余定长块
```

### 3. 切块产物与命名空间

- **块种类 `meta.kind`**：`function` / `class` / `method` / `module`；定长块经 enrichment 后 `kind="text"`。
- **`meta` 字段**：`source / doc_type / symbol / kind / file / start / end / start_line / end_line / order / updated_at / project_id`
  （模块块 `symbol=None`；定长块另含 `section / position / trust`）。
- **`chunk_id` 命名空间**：
  - `symbol` / `symbol_union` 的**符号块与模块块**：`{doc_id}:{seq:04d}`（按起始行排序，连续稳定）；
  - `symbol_union` 的**定长块**：`{doc_id}:F{seq:04d}`；
  - `fixed`：`{doc_id}:{seq:04d}`。

### 4. 契约与不变量

- `chunk_id` 稳定；`symbol` 模式序号连续（同文档同参数恒定）。
- **全非空源行覆盖**（符号块 ∪ 模块块）——新增不变量，由 L1 `test_all_nonempty_source_lines_are_covered` 断言。
- 非代码 / 语法错误 ⇒ 回退定长，不改变定长契约。
- 仅作用于 `.py`；不影响嵌入/检索/生成接口。
- `config_hash` 因 `chunking` 字段（语义参数）而全面变化。
- 数据/基线只读；历史报告/架构说明**只增不改**。

### 5. 本轮实测与状态（均以 E02 定长 512/80 `recall@5=0.8519` 为基线）

| 尝试 | 模式 | `recall@5` | `mrr@5` | 判定 |
|---|---|---|---|---|
| 1 | `symbol`（纯符号块） | 0.5926 | 0.6698 | FAIL |
| 2 | `symbol` + 模块剩余块 | 0.8148 | 0.7698 | FAIL |
| 3 | `symbol_union` | 0.7037 | 0.7870 | FAIL（`mrr` 护栏 PASS） |

L1：`python -m pytest -q` → 96 passed。**状态：未达标（3 次尝试）**；`symbol` 与 `symbol_union`
作为可选 `chunking` 模式保留（结构化/可归因价值），R1 转入 E05。详见 [`stage-E03-report.md`](stage-E03-report.md) §8、§9。

### 6. 边界

- 语义切块（按嵌入相似度断句）未做；增量索引为全量 diff，非文件事件监听。
- `symbol_union` 的定长块仅保留"非冗余"部分；不做加权/去重排序。
- E03 未达标，**未冻结基线**。

