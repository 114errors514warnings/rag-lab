"""分页相关工具（proj-alpha）。"""

from __future__ import annotations

MAX_PAGE_SIZE = 100


def validate_page(page: int) -> bool:
    """校验分页参数是否合法。"""
    if not isinstance(page, int):
        return False
    return 1 <= page <= MAX_PAGE_SIZE


def paginate(items: list, page: int, size: int = 20) -> list:
    if not validate_page(page):
        raise ValueError("invalid page")
    start = (page - 1) * size
    return items[start:start + size]
