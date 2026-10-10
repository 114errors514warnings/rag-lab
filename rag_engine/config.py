"""引擎配置。``fingerprint()`` 即报告里的 ``config_hash``：配置一改就变。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class EngineConfig:
    # --- 切块 ---
    chunk_size: int = 400  # 字符数（中英通用）
    chunk_overlap: int = 80

    # --- Embedding ---
    embed_provider: str = "hashing"  # hashing（离线默认）| openai
    embed_dim: int = 1024
    embed_model: str = "text-embedding-3-small"  # 仅 openai 提供者使用

    # --- 检索 ---
    top_k: int = 3
    min_relevance: float = 0.0  # 低于该余弦分视为无命中（不产生引用）

    # --- 生成 ---
    generator: str = "extractive"  # extractive（离线默认）| openai
    gen_model: str = "gpt-4o-mini"
    max_context_chunks: int = 5

    # --- 路径 ---
    raw_dir: str = "data/kb"
    index_dir: str = "data/index"
    #: 参与 Embedding 拟合的目录（hashing 提供者用其统计 idf）
    reserved: tuple[str, ...] = field(default_factory=tuple)

    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
