"""E01 · L1：解析器契约（doc_id 稳定、多项目隔离、代码解析）。

对应实验 `configs/E01.yaml`：把 E00 里"隐式的解析"变成**有显式断言**的解析器基线。
"""

from __future__ import annotations

from pathlib import Path

from rag_engine.ingest.loader import iter_source_files, load_file, load_tree

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "data" / "kb"


def test_doc_id_is_stable_and_source_derived() -> None:
    files = iter_source_files(KB)
    assert files, "data/kb 下应有可解析文件"
    doc = files[0]
    a = load_file(doc, root=KB)
    b = load_file(doc, root=KB)
    assert a.doc_id == b.doc_id                      # 稳定
    assert a.source and not Path(a.source).is_absolute()   # 相对来源
    assert a.doc_type in {"md", "markdown", "txt", "py", "pdf"}


def test_different_files_get_different_doc_ids() -> None:
    files = sorted(iter_source_files(KB), key=lambda p: p.as_posix())
    assert len(files) >= 2
    a = load_file(files[0], root=KB)
    b = load_file(files[1], root=KB)
    assert a.doc_id != b.doc_id


def test_load_tree_project_isolation() -> None:
    docs = load_tree(KB)
    top = [d for d in docs if d.project_id is None]
    proj = [d for d in docs if d.project_id is not None]
    assert proj, "应包含 proj-* 项目文件"
    assert {"proj-auth", "proj-sched"} <= {d.project_id for d in proj}
    assert all(d.source.startswith(str(d.project_id) + "/") for d in proj)   # 来源带项目前缀
    assert all(not d.source.startswith("proj-") for d in top)               # 顶层文档不属于任何项目


def test_python_files_are_parsed_with_code() -> None:
    pys = [f for f in iter_source_files(KB) if f.suffix == ".py"]
    assert pys, "应包含 .py 代码文件"
    doc = load_file(sorted(pys, key=lambda p: p.as_posix())[0], root=KB)
    assert doc.doc_type == "py"
    assert doc.text.strip()
    assert "def " in doc.text or "class " in doc.text        # 代码正文被完整读入
    assert "import" in doc.text


def test_markdown_and_text_are_supported() -> None:
    kinds = {p.suffix.lower() for p in iter_source_files(KB)}
    assert ".md" in kinds
    # .txt / .py 至少再有一种（本项目 kb 含 .py）
    assert kinds & {".txt", ".py", ".markdown"}
