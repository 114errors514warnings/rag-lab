"""Embedding 实现。

- :class:`HashingTfidfEmbedder`：离线默认。CJK/拉丁词与二元组经**带符号哈希**
  投到固定维度，做 TF-IDF 加权后 L2 归一化。它不是神经网络模型，但确实是
  "把文本映射到稠密向量再算余弦"的真实链路，零下载、可复现，用于让阶段一/门禁
  在无网络环境下就能跑通。
- :class:`OpenAIEmbedder` / :class:`SiliconFlowEmbedder`：可选。通过 **OpenAI 兼容 API**
  调用真实语义向量；SiliconFlow 走其免费模型 ``BAAI/bge-m3``（dim=1024）。
  需要环境变量（默认 ``OPENAI_API_KEY`` / ``SILICONFLOW_API_KEY``），密钥不入库。

所有实现的输出都 L2 归一化 => 内积即余弦，向量库统一用内积检索。
"""

from __future__ import annotations

import json
import hashlib
import math
import os
from pathlib import Path
from typing import Protocol, Sequence, runtime_checkable

import numpy as np

from ..utils import tokenize

_DIGEST = 8  # blake2b 摘要字节数


@runtime_checkable
class Embedder(Protocol):
    name: str
    dim: int

    def fit(self, texts: Sequence[str]) -> "Embedder": ...

    def embed(self, texts: Sequence[str]) -> np.ndarray: ...


def _bucket_sign(token: str, dim: int) -> tuple[int, float]:
    h = int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=_DIGEST).digest(), "big")
    bucket = h % dim
    sign = 1.0 if (h >> 63) & 1 == 0 else -1.0
    return bucket, sign


class HashingTfidfEmbedder:
    def __init__(self, dim: int = 1024, bigrams: bool = True) -> None:
        if dim <= 0:
            raise ValueError("dim 必须为正")
        self.dim = dim
        self.bigrams = bigrams
        self.idf: np.ndarray | None = None
        self.name = f"hashing-tfidf(dim={dim},bigrams={bigrams})"

    # ------------------------------------------------------------------ fit
    def fit(self, texts: Sequence[str]) -> "HashingTfidfEmbedder":
        df = np.zeros(self.dim, dtype=np.float64)
        for text in texts:
            buckets = {_bucket_sign(tok, self.dim)[0] for tok in set(tokenize(text, self.bigrams))}
            for b in buckets:
                df[b] += 1.0
        n = max(len(texts), 1)
        self.idf = np.log((n + 1.0) / (df + 1.0)) + 1.0
        return self

    # ---------------------------------------------------------------- embed
    def _raw(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float64)
        counts: dict[str, int] = {}
        for tok in tokenize(text, self.bigrams):
            counts[tok] = counts.get(tok, 0) + 1
        for tok, c in counts.items():
            bucket, sign = _bucket_sign(tok, self.dim)
            vec[bucket] += sign * (1.0 + math.log(c))
        return vec

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        mat = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            v = self._raw(text)
            if self.idf is not None:
                v = v * self.idf
            norm = float(np.linalg.norm(v))
            if norm > 0:
                v = v / norm
            mat[i] = v.astype(np.float32)
        return mat

    # ------------------------------------------------------------ 持久化
    def save(self, directory: Path | str) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "embed.json").write_text(
            json.dumps({"kind": "hashing", "dim": self.dim, "bigrams": self.bigrams}),
            encoding="utf-8",
        )
        np.save(directory / "idf.npy", self.idf if self.idf is not None else np.zeros(self.dim))

    @classmethod
    def load(cls, directory: Path | str) -> "HashingTfidfEmbedder":
        directory = Path(directory)
        info = json.loads((directory / "embed.json").read_text(encoding="utf-8"))
        emb = cls(dim=info["dim"], bigrams=info["bigrams"])
        idf = np.load(directory / "idf.npy")
        emb.idf = idf if idf.any() else None
        return emb


class OpenAIEmbedder:
    """OpenAI 兼容的 Embedding API。

    通过 ``base_url`` 可指向任意兼容端点（如 SiliconFlow）；密钥从环境变量读取，
    **不写入代码/配置/报告**。批量切分以适配服务端限额。
    """

    def __init__(self, model: str = "text-embedding-3-small", dim: int = 1024,
                 base_url: str | None = None, api_key_env: str = "OPENAI_API_KEY",
                 batch: int = 32, name: str | None = None) -> None:
        self.model = model
        self.dim = dim
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.batch = max(1, batch)
        self.name = name or f"openai:{model}"
        self._client = None

    def _client_or_create(self):
        if self._client is None:
            try:
                from openai import OpenAI  # type: ignore
            except ImportError as exc:  # pragma: no cover - 环境相关
                raise RuntimeError("未安装 openai，无法使用 API Embedder") from exc
            key = os.environ.get(self.api_key_env)
            if not key:
                raise RuntimeError(f"未设置环境变量 {self.api_key_env}（密钥不入库）")
            self._client = OpenAI(api_key=key, base_url=self.base_url) if self.base_url else OpenAI(api_key=key)
        return self._client

    def fit(self, texts: Sequence[str]) -> "OpenAIEmbedder":  # 无状态
        return self

    def save(self, directory: Path | str) -> None:
        """API Embedder 无状态：只写一个标记文件（记录模型名/维度；向量存于向量库）。"""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "embed.json").write_text(
            json.dumps({"kind": "api", "model": self.model, "dim": self.dim}),
            encoding="utf-8",
        )

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        client = self._client_or_create()
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            resp = client.embeddings.create(model=self.model, input=list(texts[i:i + self.batch]))
            out.extend(d.embedding for d in sorted(resp.data, key=lambda x: x.index))
        vecs = np.array(out, dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms


class SiliconFlowEmbedder(OpenAIEmbedder):
    """SiliconFlow（硅基流动）免费 Embedding：默认 ``BAAI/bge-m3``（dim=1024）。"""

    BASE_URL = "https://api.siliconflow.cn/v1"
    DEFAULT_MODEL = "BAAI/bge-m3"

    def __init__(self, model: str = DEFAULT_MODEL, dim: int = 1024, batch: int = 32) -> None:
        super().__init__(model=model or self.DEFAULT_MODEL, dim=dim, base_url=self.BASE_URL,
                         api_key_env="SILICONFLOW_API_KEY", batch=batch,
                         name=f"siliconflow:{model or self.DEFAULT_MODEL}")


def build_embedder(provider: str, dim: int, model: str, corpus_texts: Sequence[str]) -> Embedder:
    if provider == "siliconflow":
        # 模型名须来自 SiliconFlow（含 '/'）；否则回落到默认 bge-m3，避免误用 OpenAI 默认名
        use_model = model if "/" in model else SiliconFlowEmbedder.DEFAULT_MODEL
        return SiliconFlowEmbedder(model=use_model, dim=dim)
    if provider == "openai":
        return OpenAIEmbedder(model=model, dim=dim)
    emb = HashingTfidfEmbedder(dim=dim)
    return emb.fit(corpus_texts)
