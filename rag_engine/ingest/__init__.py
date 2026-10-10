"""文档摄入：解析 TXT / Markdown / PDF 为一个统一的 ``Document``。"""

from .chunker import chunk_document, chunk_documents
from .loader import iter_source_files, load_dir, load_file

__all__ = ["load_file", "load_dir", "iter_source_files", "chunk_document", "chunk_documents"]
