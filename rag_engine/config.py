"""引擎配置。``fingerprint()`` 即报告里的 ``config_hash``：配置一改就变。

**便携性约定（2026-10-11 起）**：``config_hash`` 只覆盖**语义参数**（切块/嵌入/检索/生成），
**不包含路径类字段**（``index_dir``/``raw_dir``），因此同一份配置在不同机器/目录下得到相同指纹。
历史记录的 ``config_hash`` 由旧口径（含绝对路径）产生，**不可与新值直接比较**；见
``docs/reports/R0/round-0.md`` 的「后续变更」。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

#: 不计入指纹的字段：路径随机器/目录变化，与检索语义无关
NON_SEMANTIC_FIELDS = frozenset({"index_dir", "raw_dir"})


@dataclass(frozen=True)
class EngineConfig:
    # --- 切块 ---
    chunk_size: int = 400  # 字符数（中英通用）
    chunk_overlap: int = 80
    #: 切块模式：fixed（定长，默认）| symbol（代码按函数/类/方法切，非代码退回定长）
    chunking: str = "fixed"

    # --- Embedding ---
    embed_provider: str = "hashing"  # hashing（离线默认）| openai
    embed_dim: int = 1024
    embed_model: str = "text-embedding-3-small"  # 仅 openai 提供者使用

    # --- 检索 ---
    top_k: int = 3
    #: 检索模式：dense（默认）| bm25 | hybrid（Dense+BM25 的 RRF 融合）
    retrieval: str = "dense"
    #: 查询改写/多查询：none（默认）| multi
    rewrite: str = "none"
    #: 重排：none（默认）| lexical | idf | siliconflow
    rerank: str = "none"
    #: 重排模型（rerank=siliconflow 时使用）
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    #: 重排候选数（先召回该数量，再重排到 top_k）
    rerank_candidates: int = 50
    #: 拒答阈值：dense=余弦；rerank=rerank 分数（bm25/hybrid 无重排时不使用）
    min_relevance: float = 0.0

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
        data = {k: v for k, v in asdict(self).items() if k not in NON_SEMANTIC_FIELDS}
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
