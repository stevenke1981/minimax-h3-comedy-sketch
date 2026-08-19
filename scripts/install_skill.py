#!/usr/bin/env python3
"""將本 Skill 複製或連結到 Hermes skills 根目錄。"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_NAMES = {".venv", ".git", "__pycache__", "build", "output", ".pytest_cache"}


def ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDE_NAMES or name.endswith(".pyc")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="安裝 minimax-h3-comedy-sketch Skill")
    parser.add_argument("--target-dir", required=True, help="Agent skills 根目錄")
    parser.add_argument("--name", default="minimax-h3-comedy-sketch")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--link", action="store_true", help="建立 symbolic link，而不是複製")
    args = parser.parse_args(argv)

    target_root = Path(args.target_dir).expanduser().resolve()
    target = target_root / args.name
    target_root.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if not args.force:
            print(f"[err] 已存在；使用 --force: {target}", file=sys.stderr)
            return 2
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)

    if args.link:
        try:
            os.symlink(SKILL_ROOT, target, target_is_directory=True)
        except OSError as exc:
            print(f"[warn] 建立連結失敗，改用複製: {exc}", file=sys.stderr)
            shutil.copytree(SKILL_ROOT, target, ignore=ignore)
    else:
        shutil.copytree(SKILL_ROOT, target, ignore=ignore)
    print(f"INSTALLED={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
