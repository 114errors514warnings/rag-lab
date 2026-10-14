"""Embedding 层：离线确定性默认实现 + 可选 API 实现（OpenAI / SiliconFlow）。"""

from .embedder import (
    Embedder,
    HashingTfidfEmbedder,
    OpenAIEmbedder,
    SiliconFlowEmbedder,
    build_embedder,
)

__all__ = [
    "Embedder",
    "HashingTfidfEmbedder",
    "OpenAIEmbedder",
    "SiliconFlowEmbedder",
    "build_embedder",
]
