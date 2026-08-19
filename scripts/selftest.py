#!/usr/bin/env python3
"""Check that the root-level skill package is complete and runnable as files."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = [
    "SKILL.md",
    "README.md",
    "LICENSE",
    "references/joke-structure.md",
    "templates/人工服務.json",
    "scripts/run_comedy_sketch.py",
    "scripts/qa_and_assemble.py",
    "scripts/install_skill.py",
    "scripts/selftest.py",
]


def fail(msg: str) -> int:
    print(f"[fail] {msg}", file=sys.stderr)
    return 1


def main() -> int:
    missing = [rel for rel in REQUIRED if not (ROOT / rel).is_file()]
    if missing:
        return fail("missing files: " + ", ".join(missing))

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if "minimax-h3-comedy-sketch" not in skill:
        return fail("SKILL.md missing skill name")
    if "MiniMaxH3TurboSampler" in skill and "禁止" not in skill:
        return fail("SKILL.md must forbid turbo, not recommend it")

    sketch = json.loads((ROOT / "templates" / "人工服務.json").read_text(encoding="utf-8"))
    beats = sketch.get("beats") or {}
    for key in ("hook", "setup", "punch", "tag", "callback"):
        if not beats.get(key):
            return fail(f"template missing beat: {key}")
    if not sketch.get("segments"):
        return fail("template has no segments")
    for segment in sketch["segments"]:
        text = str(segment.get("text") or "")
        if not text:
            return fail(f"empty text in segment {segment.get('id')}")
        if len(text) > 48:
            return fail(f"segment {segment.get('id')} longer than T8 comfort zone")

    for rel in (
        "scripts/run_comedy_sketch.py",
        "scripts/qa_and_assemble.py",
        "scripts/install_skill.py",
    ):
        source = (ROOT / rel).read_text(encoding="utf-8")
        ast.parse(source)
        if rel.endswith("run_comedy_sketch.py"):
            if "MiniMaxH3TurboSampler" in source or "ref2v_turbo" in source:
                return fail("runner must not attach turbo LoRA")
            if "dual_clock_euler" not in source or "native_flow" not in source:
                return fail("runner missing T8 dual_clock contract")

    print("SELFTEST_OK")
    print(f"ROOT={ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
