#!/usr/bin/env python3
"""Idempotently inject an ``Overview`` nav link into every ``index.html``
under the given project directory.

Usage: python inject_overview_link.py <project-dir>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import overview_lib


def _relative_href(index_path: Path, project_root: Path) -> str:
    depth = len(index_path.relative_to(project_root).parts) - 1
    return ("../" * depth) + "overview.html"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <project-dir>", file=sys.stderr)
        return 2
    project_root = Path(argv[1]).resolve()
    if not project_root.is_dir():
        print(f"Not a directory: {project_root}", file=sys.stderr)
        return 2
    changed = 0
    for index_path in project_root.rglob("index.html"):
        href = _relative_href(index_path, project_root)
        text = index_path.read_text(encoding="utf-8", errors="replace")
        new_text, did = overview_lib.inject_nav_link(text, href, "Overview")
        if did:
            index_path.write_text(new_text, encoding="utf-8")
            changed += 1
    print(f"Injected Overview link into {changed} index pages under {project_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
