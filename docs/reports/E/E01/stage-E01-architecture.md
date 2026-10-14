# rag-lab · E01 架构说明 · 解析器契约基线

> 报告：[`stage-E01-report.md`](stage-E01-report.md)
> **次要阶段**：架构以树形文档表示（未生成 Archify 图，遵循"仅重要阶段出图"的约定）。

## 1. 解析层结构（树）

```
data/kb/                                   # 知识库根（raw_dir）
├── *.md / *.txt                           # 文档集：project_id = None（不属于任何项目）
├── proj-auth/                             # 代码项目 A：project_id = "proj-auth"
│   └── *.py
└── proj-sched/                            # 代码项目 B：project_id = "proj-sched"
    └── *.py

ingest/loader.py
├── iter_source_files(root)   -> [*.md,*.markdown,*.txt,*.py,*.pdf]   （路径排序，确定性）
├── load_file(path, root, project_id) -> Document
│     ├── doc_id   = slug(相对路径) + "-" + sha1(相对路径)[:6]   ← 稳定、可读
│     ├── source   = 相对 root 的 POSIX 路径                     ← 证据映射用
│     ├── doc_type = 后缀去点（md/txt/py/pdf）
│     └── text     = 原文（PDF 走 PyMuPDF/pypdf 可选依赖）
└── load_tree(root) -> [Document]
      ├── 顶层文件            → project_id = None
      └── 一级子目录/<file>   → project_id = <子目录名>，source = "<项目>/<文件>"
```

## 2. 数据流

```
data/kb/** ─▶ iter_source_files ─▶ load_file(每文件) ─▶ Document
   （顶层）project_id=None        （子目录）project_id=<项目名>
        │
        ▼
   chunk_document → embed → vector_store → dense 检索（可按 project_id 过滤）
```

## 3. 关键契约（E01 断言）
- `doc_id`：同文件恒定；由**来源相对路径**派生（不依赖绝对路径）。
- `source`：相对 `root` 的 POSIX 路径（跨机器稳定，供证据映射）。
- `load_tree` 隔离：顶层文档 `project_id=None`；`proj-*` 文件 `project_id=<项目名>` 且 `source` 以 `<项目名>/` 开头。
- 代码文件完整读入（正文含 `def`/`class`/`import`）。

## 4. 不变量与边界
- 不变量：`doc_id` 稳定；`source` 相对；项目隔离由 `project_id` 承载（检索时前置过滤）。
- 边界：PDF 解析为可选依赖（环境缺则报错，不影响 md/txt/py 主链路）；本阶段**不改检索/生成**。
