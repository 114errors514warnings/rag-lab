"""向量索引：默认 numpy 内积后端（等价 FAISS IndexFlatIP 的语义）。

- 向量已 L2 归一化 => 内积即余弦相似度。
- 支持 metadata 过滤（阶段二在此扩展"先过滤再检索"）。
- 支持磁盘持久化：``vectors.npy`` + ``chunks.jsonl``。

当环境提供 FAISS 或 Chroma 时，只需实现同一 ``VectorStore`` 协议并替换默认后端，
检索层与评测层不变。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, Sequence, runtime_checkable

import numpy as np

from ..schema import Chunk, Retrieved


@runtime_checkable
class VectorStore(Protocol):
    def add(self, chunks: Sequence[Chunk], vectors: np.ndarray) -> None: ...
    def search(self, query_vec: np.ndarray, k: int, flt: dict | None = None) -> list[Retrieved]: ...
    def __len__(self) -> int: ...


def _matches(meta: dict, flt: dict | None) -> bool:
    if not flt:
        return True
    return all(meta.get(key) == value for key, value in flt.items())


class NumpyVectorStore:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self._matrix: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.chunks)

    def add(self, chunks: Sequence[Chunk], vectors: np.ndarray) -> None:
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.shape[0] != len(chunks):
            raise ValueError(f"chunks={len(chunks)} 与 vectors={vectors.shape[0]} 数量不一致")
        if vectors.ndim != 2:
            raise ValueError("vectors 必须为二维数组")
        self._matrix = vectors if self._matrix is None else np.vstack([self._matrix, vectors])
        self.chunks.extend(chunks)

    def search(self, query_vec: np.ndarray, k: int, flt: dict | None = None) -> list[Retrieved]:
        if not self.chunks or k <= 0:
            return []
        q = np.asarray(query_vec, dtype=np.float32).reshape(-1)
        scores = self._matrix @ q  # 归一化向量 => 余弦
        order = sorted(
            range(len(self.chunks)),
            key=lambda i: (-float(scores[i]), self.chunks[i].chunk_id),
        )
        hits: list[Retrieved] = []
        for i in order:
            chunk = self.chunks[i]
            if not _matches(chunk.meta, flt):
                continue
            hits.append(Retrieved(chunk=chunk, score=round(float(scores[i]), 6)))
            if len(hits) >= k:
                break
        return hits

    # ------------------------------------------------------------ 持久化
    def save(self, directory: Path | str) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        matrix = self._matrix if self._matrix is not None else np.zeros((0, 0), dtype=np.float32)
        np.save(directory / "vectors.npy", matrix)
        with open(directory / "chunks.jsonl", "w", encoding="utf-8") as fh:
            for chunk in self.chunks:
                fh.write(
                    json.dumps(
                        {"chunk_id": chunk.chunk_id, "doc_id": chunk.doc_id,
                         "text": chunk.text, "meta": chunk.meta},
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    @classmethod
    def load(cls, directory: Path | str) -> "NumpyVectorStore":
        directory = Path(directory)
        store = cls()
        chunks: list[Chunk] = []
        with open(directory / "chunks.jsonl", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                chunks.append(Chunk(chunk_id=row["chunk_id"], doc_id=row["doc_id"],
                                    text=row["text"], meta=row.get("meta", {})))
        matrix = np.load(directory / "vectors.npy")
        store._matrix = matrix if matrix.size else None
        store.chunks = chunks
        return store
