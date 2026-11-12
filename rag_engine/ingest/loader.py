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

#: 默认跳过的目录：版本库/缓存/依赖，进去只会把索引撑大、把检索带偏。
_SKIP_DIR_NAMES = {"__pycache__", "node_modules"}
_SLUG = re.compile(r"[^0-9a-zA-Z]+")


def normalize_extensions(values) -> set[str]:
    """把 ``[".cs", "tscn"]`` / ``[".cs,.tscn"]`` 规整成 ``{".cs", ".tscn"}``。

    传空/None 时返回**默认集合**（不改变既有语料的行为）。
    """
    if not values:
        return set(_SUPPORTED)
    parts: list[str] = []
    for item in values:
        parts.extend(str(item).split(","))
    out = set()
    for raw in parts:
        value = raw.strip().lower()
        if not value:
            continue
        out.add(value if value.startswith(".") else "." + value)
    return out or set(_SUPPORTED)


def _is_excluded(relative: Path, exclude_dirs) -> bool:
    """``exclude_dirs`` 支持目录名（``_backup``）或相对路径（``Tools/Art``）。"""
    if not exclude_dirs:
        return False
    parts = relative.parts
    names = {str(item).strip().strip("/\\").replace("\\", "/") for item in exclude_dirs if str(item).strip()}
    posix = relative.as_posix()
    for entry in names:
        if "/" in entry:
            if posix == entry or posix.startswith(entry + "/"):
                return True
        elif entry in parts:
            return True
    return False


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
              project_id: str | None = None, extensions=None) -> Document:
    """解析单个文件；``root`` 用于计算相对来源路径；``extensions`` 放宽允许的后缀。"""
    path = Path(path)
    allowed = normalize_extensions(extensions)
    if path.suffix.lower() not in allowed:
        raise ValueError(f"不支持的文件类型：{path.suffix}（允许 {sorted(allowed)}）")
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


def iter_source_files(raw_dir: Path | str, extensions=None, exclude_dirs=None) -> list[Path]:
    """递归列出目录下所有受支持文件（按路径排序，保证确定性）。

    ``extensions`` 默认沿用 ``_SUPPORTED``（不改变既有语料的行为）；
    ``exclude_dirs`` 支持目录名（``_backup``）或相对路径（``Tools/Art``）；
    隐藏目录（``.godot`` / ``.ai-memory`` 之类）一律跳过。
    """
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        return []
    allowed = normalize_extensions(extensions)
    files: list[Path] = []
    for path in raw_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        relative = path.relative_to(raw_dir)
        if any(part.startswith(".") or part in _SKIP_DIR_NAMES for part in relative.parts[:-1]):
            continue
        if _is_excluded(relative, exclude_dirs):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.as_posix())


def load_dir(raw_dir: Path | str, project_id: str | None = None, extensions=None,
             exclude_dirs=None) -> list[Document]:
    """加载目录下全部文档。"""
    raw_dir = Path(raw_dir)
    return [load_file(p, root=raw_dir, project_id=project_id, extensions=extensions)
            for p in iter_source_files(raw_dir, extensions, exclude_dirs)]


def load_tree(root: Path | str, extensions=None, exclude_dirs=None) -> list[Document]:
    """加载一个目录树，支持多项目隔离（手册 2.1）。

    - 顶层文件：``project_id=None``（文档集合）。
    - 每个一级子目录：``project_id=<子目录名>``（独立代码项目）。
    - ``source`` 始终相对 ``root``（如 ``proj-auth/auth.py``），便于证据映射并区分项目。
    """
    root = Path(root)
    docs: list[Document] = [load_file(p, root=root, extensions=extensions)
                            for p in iter_source_files(root, extensions, exclude_dirs)
                            if p.parent.resolve() == root.resolve()]
    for sub in sorted((d for d in root.iterdir()
                       if d.is_dir() and not d.name.startswith(".")
                       and d.name not in _SKIP_DIR_NAMES
                       and not _is_excluded(Path(d.name), exclude_dirs)),
                      key=lambda d: d.name):
        docs.extend(load_file(p, root=root, project_id=sub.name, extensions=extensions)
                    for p in iter_source_files(sub, extensions, exclude_dirs))
    return docs
