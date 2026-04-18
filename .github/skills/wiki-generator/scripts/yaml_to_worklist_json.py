#!/usr/bin/env python3
"""Convert _worklist.yaml → JSON shape expected by overview_pass.py.

Reads a YAML mapping of module-slug -> [{title, href}, ...] and prints
the same structure as JSON on stdout.
"""
import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    sys.stderr.write("PyYAML required. Install with: pip install pyyaml\n")
    sys.exit(2)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <worklist.yaml>", file=sys.stderr)
        return 2
    data = yaml.safe_load(Path(argv[1]).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.stderr.write("Expected top-level mapping in worklist YAML\n")
        return 2
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
