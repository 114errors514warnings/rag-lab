"""Query Rewrite / Multi-query（阶段三，离线确定性实现）。

- 极小同义词表把中文查询扩到对应的英文标识符/术语，缓解"中文提问 vs 英文实现"的词面缺口。
- 返回**改写后的多条查询**（含原查询），供多路召回合并。
"""

from __future__ import annotations

from ..index.bm25_store import tokenize

SYNONYMS: dict[str, str] = {
    "切块": "chunk chunking overlap",
    "向量": "vector embedding dense",
    "检索": "retrieve retrieval search",
    "重排": "rerank reranker cross-encoder",
    "精排": "重排 rerank cross-encoder 候选 耗时",
    "索引": "index indexer",
    "引用": "citation",
    "上下文": "context token",
    "预算": "budget token",
    "增量": "incremental index",
    "去重": "dedupe deduplication",
    "过滤": "filter project_id isolation",
    "服务": "service fastapi mcp",
    "隔离": "isolation project_id project",
    "符号": "symbol ast 代码",
    "依赖": "dependency deps 调用",
    # 中文提问 ↔ 术语/英文实现（缓解词面不重叠）
    "原理": "向量 嵌入 dense retrieval",
    "相似度": "向量 嵌入 dense",
    "省钱": "成本 预算 token 控制",
    "压缩": "上下文 长度 限制 预算 token",
    "回答": "上下文 长度",
    "代码": "ast 符号 code",
    "代码库": "ast 符号 code",
    "越权": "隔离 project_id 过滤",
    "串味": "隔离 project_id",
    "串到": "隔离 project_id",
    "仓库": "项目 project_id",
    "混进": "隔离 过滤 project_id",
    "防止": "隔离 过滤",
    "避免": "隔离 过滤 project_id",
    "项目": "project_id 隔离 过滤",
    "耗时": "latency 开销 重排",
    "时间": "耗时 latency",
    "稀疏": "bm25 检索",
    "稠密": "dense 向量",
    "融合": "rrf reciprocal rank",
}


def rewrite(question: str, limit: int = 8) -> list[str]:
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


def multi_query(question: str, limit: int = 8) -> list[str]:
    return rewrite(question, limit=limit)
