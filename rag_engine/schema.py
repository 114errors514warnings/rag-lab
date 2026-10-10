"""系统本体的数据契约（阶段一）。

与 ``rag_eval.schema`` 刻意区分：这里是**实现内部**的结构，评测契约在 ``rag_eval``。
两者通过 ``eval_adapter`` 转换，避免实现细节渗进评测协议。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Document:
    """解析后的一篇原始文档。"""

    doc_id: str
    source: str  # 相对来源路径，进报告用于回溯
    doc_type: str  # md / txt / pdf / py ...
    text: str
    updated_at: str | None = None
    project_id: str | None = None


@dataclass
class Chunk:
    """切块产物。``chunk_id`` 必须稳定：同文档 + 同参数 => 同 id。

    稳定 id 是增量索引（阶段二）与评测可复现（baseline 对照）的前提。
    """

    chunk_id: str
    doc_id: str
    text: str
    meta: dict = field(default_factory=dict)


@dataclass
class Retrieved:
    """一次检索命中。"""

    chunk: Chunk
    score: float
