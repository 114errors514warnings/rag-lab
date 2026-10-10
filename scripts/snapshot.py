"""数据快照：固定一次实验的"数据 + 代码 + 解析器"状态。

产出 ``snapshots/{name}.json``：
- 每个源文件的相对路径 + sha256
- 聚合 digest（所有文件哈希排序后合并）
- git commit（若在仓库中）
- parser 版本
- 排除规则

用途：作为 ``run_id`` 的成分，保证"同快照才可比"；配合 E10（增量/新鲜度）核对旧索引残留。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PARSER_VERSION = "loader-v1"
SUPPORTED = {".md", ".markdown", ".txt", ".pdf", ".py", ".json", ".yaml", ".yml"}
#: 默认排除目录/文件名（手册 2.1）
DEFAULT_EXCLUDE_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}
DEFAULT_EXCLUDE_FILES = {".env"}
SECRET_SUFFIX = {".pem", ".key"}
SECRET_HINT = ("secret", "credential", "password", "id_rsa")


def _is_excluded(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if any(part in DEFAULT_EXCLUDE_DIRS for part in rel_parts):
        return True
    name = path.name.lower()
    if name in DEFAULT_EXCLUDE_FILES:
        return True
    if path.suffix.lower() in SECRET_SUFFIX:
        return True
    return any(hint in name for hint in SECRET_HINT)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_commit(root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root,
            capture_output=True, text=True, timeout=10,
        )
    except Exception:  # noqa: BLE001
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def build_snapshot(root: Path | str):  # noqa: ANN201 - 返回结构化 dict
    root = Path(root)
    files: dict[str, str] = {}
    if root.exists():
        for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED:
                continue
            if _is_excluded(path, root):
                continue
            files[path.relative_to(root).as_posix()] = _file_sha256(path)

    aggregate = hashlib.sha256()
    for rel in sorted(files):
        aggregate.update(f"{rel}:{files[rel]}\n".encode("utf-8"))

    return {
        "name": root.name,
        "root": root.as_posix(),
        "git_commit": _git_commit(root),
        "parser_version": PARSER_VERSION,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "n_files": len(files),
        "digest": aggregate.hexdigest()[:16],
        "exclude": {
            "dirs": sorted(DEFAULT_EXCLUDE_DIRS),
            "files": sorted(DEFAULT_EXCLUDE_FILES),
            "secret_suffix": sorted(SECRET_SUFFIX),
        },
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成数据快照")
    parser.add_argument("--root", default="data/raw", help="要快照的目录")
    parser.add_argument("--name", default=None, help="快照名（默认取目录名）")
    parser.add_argument("--out", default="snapshots", help="输出目录")
    args = parser.parse_args(argv)

    root = ROOT / args.root if not Path(args.root).is_absolute() else Path(args.root)
    snap = build_snapshot(root)
    if args.name:
        snap["name"] = args.name

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{snap['name']}.json"
    out_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"snapshot -> {out_path}")
    print(f"  files={snap['n_files']} digest={snap['digest']} commit={snap['git_commit']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
