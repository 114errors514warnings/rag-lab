"""E04 · L1：API Embedder（SiliconFlow）——不联网，只测构造/回落/密钥缺失报错。"""

from __future__ import annotations

import pytest

from rag_engine.embed.embedder import (
    HashingTfidfEmbedder,
    OpenAIEmbedder,
    SiliconFlowEmbedder,
    build_embedder,
)


def test_siliconflow_embedder_metadata() -> None:
    emb = SiliconFlowEmbedder()
    assert emb.dim == 1024
    assert emb.model == "BAAI/bge-m3"
    assert emb.base_url == "https://api.siliconflow.cn/v1"
    assert emb.api_key_env == "SILICONFLOW_API_KEY"
    assert emb.name == "siliconflow:BAAI/bge-m3"


def test_build_embedder_selects_provider() -> None:
    assert isinstance(build_embedder("siliconflow", 1024, "BAAI/bge-m3", []), SiliconFlowEmbedder)
    assert isinstance(build_embedder("openai", 1024, "text-embedding-3-small", []), OpenAIEmbedder)
    assert isinstance(build_embedder("hashing", 64, "", ["x"]), HashingTfidfEmbedder)


def test_siliconflow_model_falls_back_when_name_is_not_its_own() -> None:
    # 误用 OpenAI 默认模型名（不含 '/'）时回落到 bge-m3，避免把错误模型发到 SiliconFlow
    emb = build_embedder("siliconflow", 1024, "text-embedding-3-small", [])
    assert emb.model == "BAAI/bge-m3"


def test_embed_without_key_raises(monkeypatch) -> None:
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SILICONFLOW_API_KEY"):
        SiliconFlowEmbedder().embed(["x"])
