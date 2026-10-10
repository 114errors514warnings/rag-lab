"""加载器：doc_id 稳定、类型校验、目录遍历确定性。"""

from __future__ import annotations

import pytest

from rag_engine.ingest.loader import load_dir, load_file


def test_doc_id_stable_and_source_relative(tmp_path) -> None:
    path = tmp_path / "a.md"
    path.write_text("hello", encoding="utf-8")
    d1 = load_file(path, root=tmp_path)
    d2 = load_file(path, root=tmp_path)
    assert d1.doc_id == d2.doc_id
    assert d1.source == "a.md"
    assert d1.doc_type == "md"


def test_unsupported_type_raises(tmp_path) -> None:
    path = tmp_path / "a.bin"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        load_file(path, root=tmp_path)


def test_load_dir_sorted_and_filtered(tmp_path) -> None:
    (tmp_path / "b.md").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "skip.bin").write_text("x", encoding="utf-8")
    docs = load_dir(tmp_path)
    assert [d.source for d in docs] == ["a.txt", "b.md"]  # 排序确定；.bin 被忽略
