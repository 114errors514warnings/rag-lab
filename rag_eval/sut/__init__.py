"""被测系统注册表。真实系统在此注册，评测代码不变。

``rag_eval`` 刻意不依赖任何 RAG 实现：真实系统通过**可选导入**注册，缺少时
（例如只有评测骨架的环境）依旧能跑桩系统与协议自检。
"""

from __future__ import annotations

from .base import Sut
from .stub_dense import StubDense
from .stub_hybrid import StubHybrid

#: key -> 工厂。真实系统落地后替换为例如 "chroma_bm25": lambda: ChromaBm25Sut(...)
REGISTRY: dict[str, object] = {
    "stub_dense": StubDense,
    "stub_hybrid": StubHybrid,
}


def _register_real_systems() -> None:
    try:
        from rag_engine.eval_adapter import MyPipeline
    except Exception:  # noqa: BLE001 - 真实系统缺失不应影响桩系统
        return
    REGISTRY["my_pipeline"] = MyPipeline


_register_real_systems()

__all__ = ["Sut", "REGISTRY"]
