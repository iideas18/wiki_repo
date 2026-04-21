#!/usr/bin/env python3
"""Generate versions.json for each wiki project.

Scans project directories for timestamped wiki snapshots and writes a
versions.json manifest that the in-page version switcher reads at runtime.

Usage:
    python3 generate_versions.py                  # all projects
    python3 generate_versions.py oclgrind gem5    # specific projects
    python3 generate_versions.py --list           # dry-run: print detected versions
"""

import argparse
import json
import re
import sys
import glob
from pathlib import Path

from internal_wiki_paths import iter_project_dirs, repo_relative, resolve_project_dir

TIMESTAMP_RE = re.compile(r"^\d{8}_\d{6}$")


def extract_meta(index_path: Path) -> dict | None:
    """Extract wiki-* meta tags from an index.html."""
    try:
        text = index_path.read_text(encoding="utf-8", errors="ignore")[:4096]
    except OSError:
        return None

    date_m = re.search(r'<meta\s+name="wiki-generated"\s+content="([^"]*)"', text)
    rev_m = re.search(r'<meta\s+name="wiki-source-rev"\s+content="([^"]*)"', text)
    title_m = re.search(r"<title>([^<]+)</title>", text)

    if not date_m:
        return None

    return {
        "date": date_m.group(1),
        "rev": rev_m.group(1) if rev_m else "",
        "title": title_m.group(1).strip() if title_m else "",
    }


def count_pages(version_dir: Path) -> int:
    """Count HTML files in a version directory."""
    return len(glob.glob(str(version_dir / "**/*.html"), recursive=True))


def find_versions(project_dir: Path) -> list[dict]:
    """Find all timestamped versions in a project directory."""
    versions = []
    for sub in sorted(project_dir.iterdir(), reverse=True):
        if not sub.is_dir() or not TIMESTAMP_RE.match(sub.name):
            continue
        idx = sub / "index.html"
        if not idx.is_file():
            continue

        meta = extract_meta(idx)
        if not meta:
            continue

        versions.append({
            "timestamp": sub.name,
            "date": meta["date"],
            "rev": meta["rev"],
            "pages": count_pages(sub),
            "latest": False,
        })

    if versions:
        versions[0]["latest"] = True  # already sorted newest-first

    return versions


def generate_for_project(project_dir: Path, list_only: bool = False) -> list[dict]:
    """Generate versions.json for a single project. Returns the version list."""
    versions = find_versions(project_dir)
    if not versions:
        return []

    if list_only:
        return versions

    out_path = project_dir / "versions.json"
    out_path.write_text(json.dumps(versions, indent=2) + "\n", encoding="utf-8")
    return versions


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate versions.json manifests for wiki projects.")
    parser.add_argument("projects", nargs="*", help="Specific project slugs or paths")
    parser.add_argument("--list", action="store_true", help="Print versions without writing files")
    parser.add_argument("--root", choices=("public", "internal"), default="public", help="Select which content root to scan")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    opts = _parse_args(sys.argv[1:] if argv is None else argv)

    if opts.projects:
        dirs = [resolve_project_dir(name, root_name=opts.root) for name in opts.projects]
    else:
        dirs = iter_project_dirs(root_name=opts.root)

    total = 0
    for d in dirs:
        if not d.is_dir():
            continue
        versions = generate_for_project(d, list_only=opts.list)
        if not versions:
            continue
        total += 1
        name = d.name
        if opts.list:
            print(f"{name}:")
            for v in versions:
                tag = " (latest)" if v["latest"] else ""
                rev = f" ({v['rev'][:7]})" if v["rev"] else ""
                print(f"  {v['timestamp']}  {v['date']}{rev}  {v['pages']} pages{tag}")
        else:
            print(f"  {repo_relative(d / 'versions.json')}  ({len(versions)} version(s))")

    if not opts.list:
        print(f"Generated versions.json for {total} project(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
