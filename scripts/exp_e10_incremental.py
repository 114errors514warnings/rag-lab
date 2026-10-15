"""E10 · 增量索引 vs 全量重建 的演示与度量。

复用 S2 的 ``IncrementalIndexer``（未新造）。做法：
1. 在真实语料 ``data/kb`` 上做一次**全量**索引，记录块数与耗时；
2. 改动 1 个文档，做**增量**更新，记录重建块数与耗时；
3. 断言：**未被改动的文档块与向量逐字节不变**，且只重建受影响切片；
4. 输出 JSON 汇总（供 E10 报告引用）。

约定：用离线 hashing 向量（确定性、无网络），故耗时反映本地计算；“重建块数”即真实项目中
API Embedding 的调用量，是最主要的成本代理。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_engine.config import EngineConfig  # noqa: E402
from rag_engine.embed.embedder import build_embedder  # noqa: E402
from rag_engine.index.indexer import IncrementalIndexer  # noqa: E402
from rag_engine.index.vector_store import NumpyVectorStore  # noqa: E402
from rag_engine.ingest.chunker import chunk_documents  # noqa: E402
from rag_engine.ingest.clean import clean_documents, dedupe_documents  # noqa: E402
from rag_engine.ingest.loader import load_tree  # noqa: E402
from rag_engine.schema import Document  # noqa: E402

TARGET_SUFFIX = "proj-auth/auth.py"


def _matrix_map(store: NumpyVectorStore) -> dict[str, np.ndarray]:
    return {c.chunk_id: store._matrix[i].copy() for i, c in enumerate(store.chunks)}


def main() -> int:
    cfg = EngineConfig()  # chunk 400/80, hashing
    docs = dedupe_documents(clean_documents(load_tree(ROOT / cfg.raw_dir)))[0]

    # 参考 embedder（对全量语料拟合 idf），增量更新复用它
    chunks = chunk_documents(docs, cfg.chunk_size, cfg.chunk_overlap)
    embedder = build_embedder("hashing", cfg.embed_dim, "", [c.text for c in chunks])

    # ---- 全量 ----
    store = NumpyVectorStore()
    indexer = IncrementalIndexer(store, embedder, cfg.chunk_size, cfg.chunk_overlap)
    t0 = time.perf_counter()
    first = indexer.update(docs)
    full_s = time.perf_counter() - t0
    full_chunks = len(store.chunks)
    before = _matrix_map(store)

    # ---- 增量（改动 1 个文档）----
    docs2 = [
        Document(doc_id=d.doc_id, source=d.source, doc_type=d.doc_type, project_id=d.project_id,
                 text=(d.text + "\n# E10: changed\n" if d.source.endswith(TARGET_SUFFIX) else d.text))
        for d in docs
    ]
    t0 = time.perf_counter()
    inc = indexer.update(docs2)
    inc_s = time.perf_counter() - t0
    after = _matrix_map(store)

    target_ids = {c.chunk_id for c in store.chunks if str(c.meta.get("source", "")).endswith(TARGET_SUFFIX)}
    untouched = [cid for cid in before if cid not in target_ids]
    unchanged = all(cid in after and np.array_equal(before[cid], after[cid]) for cid in untouched)

    result = {
        "corpus_files": len(docs),
        "full": {"chunks": full_chunks, "seconds": round(full_s, 3), "added_docs": len(first.added)},
        "incremental": {
            "changed_docs": sorted(inc.changed), "reused_docs": len(inc.reused),
            "chunks_rebuilt": inc.chunks_rebuilt, "seconds": round(inc_s, 3),
        },
        "unaffected_vectors_byte_identical": unchanged,
        "untouched_chunks": len(untouched),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    ok = unchanged and len(inc.changed) == 1 and inc.chunks_rebuilt < full_chunks
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
