"""加载与解析：TXT / Markdown / PDF -> Document。

- ``doc_id`` 由来源相对路径派生（稳定、可读），保证增量索引与评测对齐。
- PDF 解析为**可选依赖**（PyMuPDF 优先，pypdf 兜底）；缺失时给出明确报错，
  不影响 md/txt 主链路。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ..schema import Document

_SUPPORTED = {".md", ".markdown", ".txt", ".pdf", ".py"}
_SLUG = re.compile(r"[^0-9a-zA-Z]+")


def _make_doc_id(rel_source: str) -> str:
    slug = _SLUG.sub("-", rel_source).strip("-").lower()[:48] or "doc"
    digest = hashlib.sha1(rel_source.encode("utf-8")).hexdigest()[:6]
    return f"{slug}-{digest}"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    try:  # 优先 PyMuPDF
        import fitz  # type: ignore

        with fitz.open(path) as pdf:
            return "\n".join(page.get_text() for page in pdf)
    except ImportError:
        pass
    try:  # 兜底 pypdf
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except ImportError as exc:  # noqa: PERF203
        raise RuntimeError(
            f"解析 PDF 需要 PyMuPDF 或 pypdf，二者均未安装：{path}"
        ) from exc


def load_file(path: Path | str, root: Path | str | None = None,
              project_id: str | None = None) -> Document:
    """解析单个文件；``root`` 用于计算相对来源路径。"""
    path = Path(path)
    if path.suffix.lower() not in _SUPPORTED:
        raise ValueError(f"不支持的文件类型：{path.suffix}（支持 {sorted(_SUPPORTED)}）")
    root_path = Path(root) if root is not None else path.parent
    try:
        rel = path.resolve().relative_to(root_path.resolve()).as_posix()
    except ValueError:
        rel = path.name
    if path.suffix.lower() == ".pdf":
        text = _read_pdf(path)
    else:
        text = _read_text(path)
    return Document(
        doc_id=_make_doc_id(rel),
        source=rel,
        doc_type=path.suffix.lower().lstrip("."),
        text=text,
        project_id=project_id,
    )


def iter_source_files(raw_dir: Path | str) -> list[Path]:
    """递归列出目录下所有受支持文件（按路径排序，保证确定性）。"""
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        return []
    files = [p for p in raw_dir.rglob("*") if p.is_file() and p.suffix.lower() in _SUPPORTED]
    return sorted(files, key=lambda p: p.as_posix())


def load_dir(raw_dir: Path | str, project_id: str | None = None) -> list[Document]:
    """加载目录下全部文档。"""
    raw_dir = Path(raw_dir)
    return [load_file(p, root=raw_dir, project_id=project_id) for p in iter_source_files(raw_dir)]


def load_tree(root: Path | str) -> list[Document]:
    """加载一个目录树，支持多项目隔离（手册 2.1）。

    - 顶层文件：``project_id=None``（文档集合）。
    - 每个一级子目录：``project_id=<子目录名>``（独立代码项目）。
    - ``source`` 始终相对 ``root``（如 ``proj-auth/auth.py``），便于证据映射并区分项目。
    """
    root = Path(root)
    docs: list[Document] = [load_file(p, root=root) for p in iter_source_files(root)
                            if p.parent.resolve() == root.resolve()]
    for sub in sorted((d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")),
                      key=lambda d: d.name):
        docs.extend(load_file(p, root=root, project_id=sub.name) for p in iter_source_files(sub))
    return docs
