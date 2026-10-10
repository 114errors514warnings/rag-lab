"""逐阶段 Trace：一条 case 一行，记录"每一阶段看到了什么"。

字段对齐手册第 1 节"必须记录"表：
- 索引：source / chunk_id / start_line / end_line / symbol / project_id
- 召回：原查询 / 各通道 top-N / rank / score / 过滤条件
- 重排：候选集 / 前后排名（阶段三填）
- 组装：选中 chunk / token 数（阶段四填）
- 生成：模型 / 引用 / 答案 / tokens / 延迟

同时给出 **首个失败阶段** 的初判（gold 未入候选 / 候选有但上下文丢 / 上下文有但无引用），
供失败归因决策树后续细化。
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_eval.evidence import evidence_coverage_at_k, normalize_gold_sets


def _unit_dict(chunk) -> dict:
    return {
        "source": chunk.source,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "symbol": chunk.symbol,
        "project_id": chunk.project_id,
    }


def first_failure_stage(case, ans) -> str | None:
    """初判首个失败阶段（用于 errors.csv）。"""
    if ans.error:
        return "error"
    if case.query_type == "no_answer":
        return None if ans.refused else "generation(should_refuse)"
    gold_sets = normalize_gold_sets(case.gold_evidence)
    if not gold_sets:
        return None
    retrieved = [_unit_dict(c) for c in ans.retrieved]
    context = [_unit_dict(c) for c in ans.retrieved if c.chunk_id in set(ans.context_chunk_ids)]
    if evidence_coverage_at_k(retrieved, gold_sets, len(retrieved) or 1) == 0.0:
        return "recall(retrieval)"
    if evidence_coverage_at_k(context, gold_sets, len(context) or 1) == 0.0:
        return "assembly(context)"
    if not ans.citations:
        return "generation(no_citation)"
    return None


def build_trace(case, ans, *, k: int, system: str, config_hash: str) -> dict:
    gold_sets = normalize_gold_sets(case.gold_evidence)
    retrieved = [_unit_dict(c) for c in ans.retrieved]
    context_ids = set(ans.context_chunk_ids)
    return {
        "case_id": case.id,
        "project_id": case.project_id,
        "query": case.question,
        "query_type": case.query_type,
        "split": case.split,
        "difficulty": case.difficulty,
        "filter": {"project_id": case.project_id},
        "index": [
            {"source": u["source"], "start_line": u["start_line"], "end_line": u["end_line"],
             "symbol": u["symbol"], "project_id": u["project_id"]}
            for u in retrieved
        ],
        "retrieval": [
            {"rank": i, "chunk_id": c.chunk_id, "score": c.score}
            for i, c in enumerate(ans.retrieved, start=1)
        ],
        "assembly": {"k": k, "context_chunk_ids": list(ans.context_chunk_ids)},
        "generation": {
            "answer": ans.answer,
            "citations": ans.citations,
            "refused": ans.refused,
            "prompt_tokens": ans.prompt_tokens,
            "completion_tokens": ans.completion_tokens,
            "cost_usd": ans.cost_usd,
            "latency_ms": ans.latency_ms,
        },
        "gold_evidence": case.gold_evidence,
        "gold_sets": gold_sets,
        "first_failure_stage": first_failure_stage(case, ans),
        "system": system,
        "config_hash": config_hash,
    }


def write_traces(path: Path | str, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_traces(path: Path | str) -> list[dict]:
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
