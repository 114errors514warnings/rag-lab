"""实验配置：一次实验 = 一个 YAML，声明"改哪个主变量、其余冻结"。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ENGINE_FIELDS = {
    "chunk_size", "chunk_overlap", "chunking", "embed_provider", "embed_dim", "embed_model",
    "top_k", "rewrite", "retrieval", "rerank", "rerank_model", "rerank_candidates", "min_relevance",
    "generator", "gen_model", "max_context_chunks", "raw_dir",
}


@dataclass
class ExperimentConfig:
    experiment_id: str
    description: str = ""
    dataset: str = "data/golden/cases.jsonl"
    #: all | dev | validation | blind
    suite_split: str = "all"
    k: int = 5
    #: 被测系统（rag_engine）配置覆盖项
    system: dict = field(default_factory=dict)
    #: 预声明门槛：{metric: {"min_delta":..|"max":..|"max_delta":..}}
    gates: dict = field(default_factory=dict)
    #: 对比基线 run_id 或 metrics.json 路径
    baseline: str | None = None

    @classmethod
    def from_file(cls, path: Path | str) -> "ExperimentConfig":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        unknown = set(data) - {
            "experiment_id", "description", "dataset", "suite_split", "k",
            "system", "gates", "baseline",
        }
        if unknown:
            raise ValueError(f"未知配置字段：{sorted(unknown)}")
        system = data.get("system", {}) or {}
        bad = set(system) - ENGINE_FIELDS
        if bad:
            raise ValueError(f"system 中出现未知引擎字段：{sorted(bad)}")
        return cls(**data)

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"id": self.experiment_id, "k": self.k, "split": self.suite_split, "system": self.system},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
