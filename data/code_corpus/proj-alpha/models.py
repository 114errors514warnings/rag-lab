"""数据模型（proj-alpha）。"""

from __future__ import annotations

from .utils import validate_page


class PageQuery:
    def __init__(self, page: int = 1, size: int = 20) -> None:
        self.page = page
        self.size = size

    def validate(self) -> bool:
        """模型自校验：委托分页校验。"""
        if self.size <= 0:
            return False
        return validate_page(self.page)
