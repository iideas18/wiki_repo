#!/usr/bin/env python3
"""Refresh the private internal wiki hub under internal/index.html.

This is a local-only wrapper around update_index.py that pins the content root
to `internal/` and the hub target to `internal/index.html`.
"""

from __future__ import annotations

import sys

import update_index
from internal_wiki_paths import INTERNAL_HUB_INDEX


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    forwarded = ["--root", "internal", "--index", str(INTERNAL_HUB_INDEX)] + args
    return update_index.main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())