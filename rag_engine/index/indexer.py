"""增量索引（阶段二）：以 ``doc_id`` 为单位 diff，只重建受影响的切片与向量。

不变量（L1 硬断言）：
- 只有 ``added`` / ``changed`` 的文档会被重新切块与嵌入；
- ``removed`` / ``changed`` 的旧切片被删除；
- 其余文档的 ``chunk_id`` 与向量**逐字节不变**。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from ..ingest.chunker import chunk_document
from ..schema import Chunk, Document


@dataclass
class IndexUpdate:
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    reused: list[str] = field(default_factory=list)
    chunks_rebuilt: int = 0

    def as_dict(self) -> dict:
        return {
            "added": sorted(self.added), "changed": sorted(self.changed),
            "removed": sorted(self.removed), "reused": sorted(self.reused),
            "chunks_rebuilt": self.chunks_rebuilt,
        }


def _fingerprint(doc: Document, size: int, overlap: int) -> str:
    payload = f"{size}:{overlap}:{doc.text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class IncrementalIndexer:
    def __init__(self, store, embedder, size: int = 400, overlap: int = 80,
                 chunk_fn=None, meta_fn=None) -> None:
        self.store = store
        self.embedder = embedder
        self.size = size
        self.overlap = overlap
        self.chunk_fn = chunk_fn or (lambda doc: chunk_document(doc, size=size, overlap=overlap))
        self.meta_fn = meta_fn
        self.fingerprints: dict[str, str] = {}

    # ------------------------------------------------------------ 主流程
    def update(self, docs: list[Document]) -> IndexUpdate:
        current = {doc.doc_id: _fingerprint(doc, self.size, self.overlap) for doc in docs}
        by_id = {doc.doc_id: doc for doc in docs}

        added = [d for d in current if d not in self.fingerprints]
        changed = [d for d in current
                   if d in self.fingerprints and self.fingerprints[d] != current[d]]
        removed = [d for d in self.fingerprints if d not in current]
        reused = [d for d in current if d in self.fingerprints and self.fingerprints[d] == current[d]]

        if removed or changed:
            self.store.remove_doc_ids(set(removed + changed))

        update = IndexUpdate(added=added, changed=changed, removed=removed, reused=reused)
        rebuild_ids = added + changed
        if rebuild_ids:
            chunks: list[Chunk] = []
            for doc_id in rebuild_ids:
                chunks.extend(self._chunk(by_id[doc_id]))
            if chunks:
                vectors = self.embedder.embed([c.text for c in chunks])
                self.store.add(chunks, vectors)
            update.chunks_rebuilt = len(chunks)

        self.fingerprints = dict(current)
        return update

    def _chunk(self, doc: Document) -> list[Chunk]:
        chunks = self.chunk_fn(doc)
        if self.meta_fn is not None:
            for chunk in chunks:
                chunk.meta.update(self.meta_fn(doc, chunk))
        return chunks

    # ------------------------------------------------------------ 持久化
    def save(self, directory: Path | str) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "indexer.json").write_text(
            json.dumps({"size": self.size, "overlap": self.overlap, "fingerprints": self.fingerprints},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, directory: Path | str) -> None:
        path = Path(directory) / "indexer.json"
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self.fingerprints = dict(data.get("fingerprints", {}))
