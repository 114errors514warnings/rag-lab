"""文本工具：确定性分词与 token 估算。

分词口径固定，保证 Embedding 可复现（同输入 => 同向量）。
面向中英混排：CJK 单字 + CJK 二元组 + 拉丁词，均已做小写化。
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9_]+")
_CJK = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str, bigrams: bool = True) -> list[str]:
    """返回确定性 token 列表。"""
    low = text.lower()
    tokens: list[str] = list(_WORD.findall(low))
    cjk = _CJK.findall(low)
    tokens.extend(cjk)
    if bigrams:
        tokens.extend("".join(pair) for pair in zip(cjk, cjk[1:]))
    return tokens


def estimate_tokens(text: str) -> int:
    """粗估 token 数（用于成本/预算观测量，不追求与具体模型题词器一致）。"""
    return len(tokenize(text, bigrams=False))
