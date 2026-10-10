"""Embedding 层：离线确定性默认实现 + 可选 OpenAI 实现。"""

from .embedder import Embedder, HashingTfidfEmbedder, OpenAIEmbedder, build_embedder

__all__ = ["Embedder", "HashingTfidfEmbedder", "OpenAIEmbedder", "build_embedder"]
