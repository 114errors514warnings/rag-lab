"""Parent-Child Retrieval（阶段二）。

小块检索（子块召回更准）、返回父块作生成上下文（信息更完整、来源可回溯）。
父块与子块由 ``chunker.chunk_hierarchical`` 产生，子块 ``meta['parent_id']`` 指向父块。
"""

from __future__ import annotations

from ..schema import Chunk, Retrieved


def build_parent_map(chunks: list[Chunk]) -> dict[str, Chunk]:
    """从块列表构建 ``{parent_id: Chunk}``（含被 ``parent_id`` 引用的父块）。"""
    referenced = {c.meta.get("parent_id") for c in chunks if c.meta.get("parent_id")}
    return {c.chunk_id: c for c in chunks
            if c.meta.get("kind") == "parent" or c.chunk_id in referenced}


class ParentChildRetriever:
    def __init__(self, retriever, parents: dict[str, Chunk], child_k: int = 20) -> None:
        self.retriever = retriever
        self.parents = parents
        self.child_k = child_k

    def retrieve(self, question: str, k: int, flt: dict | None = None) -> list[Retrieved]:
        hits = self.retriever.retrieve(question, max(k, self.child_k), flt=flt)
        out: list[Retrieved] = []
        seen: set[str] = set()
        for hit in hits:
            parent_id = hit.chunk.meta.get("parent_id")
            if not parent_id:
                out.append(hit)
                continue
            if parent_id in seen:
                continue
            seen.add(parent_id)
            parent = self.parents.get(parent_id)
            out.append(Retrieved(chunk=parent, score=hit.score) if parent else hit)
            if len(out) >= k:
                break
        return out[:k]
