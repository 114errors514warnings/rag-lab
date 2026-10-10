"""桩系统的公共工具：语料加载、分词、打分。

注意：这里的打分是**关键词重叠的占位实现**，不代表真实 Dense 检索。
它们存在的唯一目的，是让"固定测试方法"在真实 RAG 落地之前就能跑通并出报告。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_WORD = re.compile(r"[a-z0-9_]+")
_CJK = re.compile(r"[\u4e00-\u9fff]")

CORPUS_PATH = Path("data/corpus/demo.jsonl")


def load_corpus(path: Path | str = CORPUS_PATH) -> list[dict]:
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def tokenize(text: str, bigrams: bool = True) -> list[str]:
    """ASCII 词 + 中文单字 + （可选）中文二元组。

    bigrams=False 时退化为弱匹配（模拟"只做词面重叠、无短语信息"的朴素检索）。
    """
    low = text.lower()
    tokens = _WORD.findall(low)
    cjk = _CJK.findall(low)
    tokens.extend(cjk)
    if bigrams:
        tokens.extend("".join(pair) for pair in zip(cjk, cjk[1:]))
    return tokens


def idf(corpus: list[dict]) -> dict[str, float]:
    import math

    df: dict[str, int] = {}
    for row in corpus:
        for tok in set(tokenize(row["text"])):
            df[tok] = df.get(tok, 0) + 1
    n = max(len(corpus), 1)
    return {tok: math.log((n + 1) / (c + 1)) + 1.0 for tok, c in df.items()}


def overlap_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    weights: dict[str, float] | None = None,
    normalize: bool = True,
) -> float:
    """词面重叠打分。

    normalize=False 时返回原始重叠计数（不做长度归一化）——这是朴素基线常见缺陷：
    长文档只要命中更多字就排前面，与是否真正相关无关。
    """
    doc_set = set(doc_tokens)
    total = 0.0
    for tok in query_tokens:
        if tok in doc_set:
            total += (weights or {}).get(tok, 1.0)
    if normalize:
        return total / (len(doc_set) ** 0.5 or 1.0)
    return total
