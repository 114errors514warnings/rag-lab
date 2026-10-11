"""Metadata Filtering（阶段二）。

要点：**过滤前置**——在检索入口就按元数据过滤，避免"先取 top-k 再过滤"导致的候选不足。
``NumpyVectorStore.search(..., flt=...)`` 已实现"先过滤后排序"，本模块提供统一的过滤语义与
候选放大工具，供上层需要时使用。
"""

from __future__ import annotations

from typing import Any, Iterable


def matches(meta: dict[str, Any], flt: dict[str, Any] | None) -> bool:
    """元数据是否满足全部过滤条件（相等语义；``None`` 值表示不过滤）。"""
    if not flt:
        return True
    return all(meta.get(key) == value for key, value in flt.items() if value is not None)


def filter_chunks(chunks: Iterable, flt: dict[str, Any] | None) -> list:
    return [c for c in chunks if matches(getattr(c, "meta", {}), flt)]


def oversample_k(k: int, flt: dict[str, Any] | None, factor: int = 3) -> int:
    """需要过滤时放大候选数，保证过滤后仍能凑够 k。"""
    return k * factor if flt else k
