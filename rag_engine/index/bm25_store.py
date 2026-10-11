"""BM25 关键词索引（阶段三）。

- 中英通用分词：ASCII 词 + 中文连续串的 2-gram（单字不参与，避免噪声）。
- 分数用标准 BM25（k1=1.5, b=0.75）；先按 ``flt`` 过滤，再排序。
- 与 Dense 各出候选，交 ``hybrid.rrf_fuse`` 融合。
"""

from __future__ import annotations

import math
import re
from collections import Counter

from ..schema import Chunk, Retrieved

_TOKEN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for match in _TOKEN.finditer((text or "").lower()):
        seg = match.group()
        if seg[0].isascii():
            out.append(seg)
        else:
            if len(seg) == 1:
                out.append(seg)
            else:
                for i in range(len(seg) - 1):
                    out.append(seg[i:i + 2])
    return out


class BM25Store:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.chunks: list[Chunk] = []
        self._tf: list[Counter] = []
        self._len: list[int] = []
        self._df: Counter = Counter()
        self._avgdl = 0.0

    def __len__(self) -> int:
        return len(self.chunks)

    def add(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            tokens = tokenize(chunk.text)
            tf = Counter(tokens)
            self.chunks.append(chunk)
            self._tf.append(tf)
            self._len.append(len(tokens))
            for term in tf:
                self._df[term] += 1
        self._avgdl = (sum(self._len) / len(self._len)) if self._len else 0.0

    def search(self, query: str, k: int, flt: dict | None = None) -> list[Retrieved]:
        from ..retrieve.filters import matches

        if k <= 0 or not self.chunks:
            return []
        terms = set(tokenize(query))
        total = len(self.chunks)
        avgdl = self._avgdl or 1.0
        scored: list[tuple[float, Chunk]] = []
        for i, chunk in enumerate(self.chunks):
            if not matches(chunk.meta, flt):
                continue
            score = 0.0
            length = self._len[i]
            for term in terms:
                df = self._df.get(term, 0)
                freq = self._tf[i].get(term, 0)
                if not df or not freq:
                    continue
                idf = math.log(1.0 + (total - df + 0.5) / (df + 0.5))
                denom = freq + self.k1 * (1.0 - self.b + self.b * length / avgdl)
                score += idf * freq * (self.k1 + 1.0) / denom
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [Retrieved(chunk=c, score=round(s, 6)) for s, c in scored[:k]]
