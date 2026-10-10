"""数据快照：排除规则与 digest 稳定性。"""

from __future__ import annotations

from scripts.snapshot import build_snapshot


def _write(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_snapshot_excludes_and_hashes(tmp_path) -> None:
    _write(tmp_path / "a.md", "hello")
    _write(tmp_path / "proj" / "b.py", "print(1)")
    _write(tmp_path / "node_modules" / "z.js", "junk")
    _write(tmp_path / ".env", "SECRET=1")
    _write(tmp_path / "id_rsa", "key")

    snap = build_snapshot(tmp_path)
    files = set(snap["files"])
    assert "a.md" in files
    assert "proj/b.py" in files
    assert not any("node_modules" in f for f in files)
    assert ".env" not in files
    assert "id_rsa" not in files
    assert snap["n_files"] == len(files)
    assert len(snap["digest"]) == 16


def test_snapshot_digest_is_stable(tmp_path) -> None:
    _write(tmp_path / "a.md", "hello")
    first = build_snapshot(tmp_path)["digest"]
    second = build_snapshot(tmp_path)["digest"]
    assert first == second
    _write(tmp_path / "a.md", "changed")
    assert build_snapshot(tmp_path)["digest"] != first
