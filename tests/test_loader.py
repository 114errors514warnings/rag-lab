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


def test_custom_extensions_include_cs_and_ignore_md(tmp_path) -> None:
    (tmp_path / "a.cs").write_text("class A {}", encoding="utf-8")
    (tmp_path / "b.md").write_text("# doc", encoding="utf-8")
    docs = load_dir(tmp_path, extensions=[".cs"])
    assert [d.source for d in docs] == ["a.cs"]
    assert docs[0].doc_type == "cs"


def test_extensions_accept_comma_string_without_dot(tmp_path) -> None:
    (tmp_path / "a.cs").write_text("class A {}", encoding="utf-8")
    (tmp_path / "b.tscn").write_text("[gd_scene]", encoding="utf-8")
    docs = load_dir(tmp_path, extensions=["cs,tscn"])
    assert sorted(d.source for d in docs) == ["a.cs", "b.tscn"]


def test_exclude_dirs_by_name_and_relative_path(tmp_path) -> None:
    (tmp_path / "keep").mkdir()
    (tmp_path / "keep" / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "_backup").mkdir()
    (tmp_path / "_backup" / "b.md").write_text("b", encoding="utf-8")
    (tmp_path / "Tools" / "Art").mkdir(parents=True)
    (tmp_path / "Tools" / "Art" / "c.md").write_text("c", encoding="utf-8")
    (tmp_path / "Tools" / "d.md").write_text("d", encoding="utf-8")

    assert sorted(d.source for d in load_dir(tmp_path, exclude_dirs=["_backup"])) == [
        "Tools/Art/c.md", "Tools/d.md", "keep/a.md"]
    assert sorted(d.source for d in load_dir(tmp_path, exclude_dirs=["Tools/Art"])) == [
        "Tools/d.md", "_backup/b.md", "keep/a.md"]


def test_hidden_dirs_are_skipped(tmp_path) -> None:
    (tmp_path / ".godot").mkdir()
    (tmp_path / ".godot" / "x.md").write_text("x", encoding="utf-8")
    (tmp_path / "ok.md").write_text("ok", encoding="utf-8")
    assert [d.source for d in load_dir(tmp_path)] == ["ok.md"]


def test_manifest_depends_on_filters(tmp_path) -> None:
    from rag_engine.pipeline import compute_manifest

    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "b.cs").write_text("class B {}", encoding="utf-8")
    default = compute_manifest(tmp_path)
    with_cs = compute_manifest(tmp_path, extensions=[".cs"])
    assert list(default) == ["a.md"]
    assert list(with_cs) == ["b.cs"]
