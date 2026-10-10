"""Embedding：确定性、归一化、拟合影响。"""

from __future__ import annotations

import numpy as np

from rag_engine.embed.embedder import HashingTfidfEmbedder


def test_output_shape_and_norm() -> None:
    emb = HashingTfidfEmbedder(dim=256).fit(["abcd", "abcd", "wxyz"])
    vecs = emb.embed(["abcd", "wxyz"])
    assert vecs.shape == (2, 256)
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-5)


def test_deterministic_for_same_input() -> None:
    a = HashingTfidfEmbedder(dim=64).fit(["x", "y"])
    b = HashingTfidfEmbedder(dim=64).fit(["x", "y"])
    assert np.allclose(a.embed(["hello world"]), b.embed(["hello world"]))


def test_save_load_roundtrip(tmp_path) -> None:
    emb = HashingTfidfEmbedder(dim=128).fit(["alpha", "beta", "alpha"])
    emb.save(tmp_path)
    loaded = HashingTfidfEmbedder.load(tmp_path)
    assert np.allclose(emb.embed(["alpha"]), loaded.embed(["alpha"]))
