"""Golden Dataset 加载与分层。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rag_eval.schema import EvalCase


def load_cases(path: Path | str) -> tuple[list[EvalCase], str]:
    raw = Path(path).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()[:16]
    cases: list[EvalCase] = []
    for lineno, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            # 手册字段名 -> 内部 schema
            row.setdefault("id", row.pop("case_id", None) or row.get("id"))
            row.setdefault("question", row.pop("query", None) or row.get("question"))
            cases.append(EvalCase(**row))
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"[golden 格式错误] {path}:{lineno} -> {exc}") from exc
    return cases, sha


def filter_split(cases: list[EvalCase], split: str) -> list[EvalCase]:
    if split in ("all", "", None):
        return cases
    if split == "answerable":
        return [c for c in cases if c.query_type != "no_answer" and c.gold_evidence]
    return [c for c in cases if c.split == split]


def by_query_type(cases: list[EvalCase]) -> dict[str, list[EvalCase]]:
    groups: dict[str, list[EvalCase]] = {}
    for case in cases:
        groups.setdefault(case.query_type or "unknown", []).append(case)
    return groups
