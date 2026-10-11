"""Query Rewrite / Multi-query（阶段三，离线确定性实现）。

- 极小同义词表把中文查询扩到对应的英文标识符/术语，缓解"中文提问 vs 英文实现"的词面缺口。
- 返回**改写后的多条查询**（含原查询），供多路召回合并。
"""

from __future__ import annotations

from ..index.bm25_store import tokenize

SYNONYMS: dict[str, str] = {
    "切块": "chunk chunking",
    "向量": "vector embedding",
    "检索": "retrieve retrieval",
    "重排": "rerank reranker",
    "索引": "index indexer",
    "引用": "citation",
    "上下文": "context",
    "预算": "budget token",
    "增量": "incremental index",
    "去重": "dedupe deduplication",
    "过滤": "filter filtering",
    "服务": "service fastapi mcp",
    "隔离": "isolation project",
    "符号": "symbol ast",
    "依赖": "dependency deps",
}


def rewrite(question: str, limit: int = 4) -> list[str]:
    """返回 [原查询, 原查询+扩展词]（去重、确定性）。"""
    seen = set(tokenize(question))
    extras: list[str] = []
    for term in tokenize(question):
        expansion = SYNONYMS.get(term)
        if expansion:
            for word in expansion.split():
                if word not in seen:
                    seen.add(word)
                    extras.append(word)
    queries = [question]
    if extras:
        queries.append(question + " " + " ".join(extras[:limit]))
    return queries


def multi_query(question: str, limit: int = 4) -> list[str]:
    return rewrite(question, limit=limit)
