"""被测系统（System Under Test）接入协议。

真实 RAG 系统只要实现 `answer(case, k) -> SystemAnswer`，即可被本评测协议接管，
无需修改评测代码——这是"固定测试方法"能跨阶段复用的前提。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..schema import EvalCase, SystemAnswer


@runtime_checkable
class Sut(Protocol):
    #: 系统标识（进入报告，例如 "chroma+bm25+cross-encoder"）
    name: str
    #: 配置摘要（配置一改即变，用于报告可追溯）
    config_hash: str

    def answer(self, case: EvalCase, k: int) -> SystemAnswer:
        """返回答案 + 检索结果 + 引用 + 用量。"""
        ...
