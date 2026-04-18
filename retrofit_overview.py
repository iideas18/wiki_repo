#!/usr/bin/env python3
"""Retrofit ``overview.html`` into every existing committed wiki.

Usage:
  python retrofit_overview.py [project ...] [--force] [--dry-run] [--confirm-each]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SKILL_SCRIPTS = REPO_ROOT / ".github" / "skills" / "wiki-generator" / "scripts"
SKILL_RESOURCES = REPO_ROOT / ".github" / "skills" / "wiki-generator" / "resources"

sys.path.insert(0, str(SKILL_SCRIPTS))
import overview_lib  # noqa: E402
import overview_pass  # noqa: E402


def _iter_project_dirs(explicit: list[str]) -> list[Path]:
    if explicit:
        return [Path(p).resolve() for p in explicit]
    candidates = []
    for child in REPO_ROOT.iterdir():
        if child.is_dir() and (child / "versions.json").is_file():
            candidates.append(child)
    return sorted(candidates)


def _active_version_dir(project: Path) -> Path | None:
    vj = project / "versions.json"
    if not vj.is_file():
        return None
    data = json.loads(vj.read_text(encoding="utf-8"))
    current = data.get("current")
    if not current:
        return None
    vdir = project / current
    return vdir if vdir.is_dir() else None


def run_overview_pass(*, wiki_root: Path, worklist: dict,
                      project_name: str, project_tagline: str) -> int:
    """Invoke the Overview Pass driver. Extracted for monkey-patching in tests."""
    tmp_worklist = wiki_root / "_tmp_worklist.json"
    tmp_worklist.write_text(json.dumps(worklist, ensure_ascii=False), encoding="utf-8")
    try:
        rc = overview_pass.main([
            "--wiki-root", str(wiki_root),
            "--worklist-json", str(tmp_worklist),
            "--project-name", project_name,
            "--project-tagline", project_tagline,
            "--prompt-template", str(SKILL_RESOURCES / "overview_pass.md"),
            "--html-template", str(SKILL_RESOURCES / "overview-template.html"),
        ])
    finally:
        tmp_worklist.unlink(missing_ok=True)
    return rc


def _gate_d(wiki_root: Path) -> bool:
    result = subprocess.run(
        ["bash", str(SKILL_SCRIPTS / "verify.sh"), "--stage=D", f"--project={wiki_root}"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(f"[WARN] Gate D failed for {wiki_root}:\n{result.stdout}\n{result.stderr}\n")
        return False
    return True


def _inject_nav(wiki_root: Path) -> None:
    subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "inject_overview_link.py"), str(wiki_root)],
        check=False,
    )


def retrofit_one(project: Path, *, force: bool, dry_run: bool) -> int:
    if (project / ".no-overview").exists():
        print(f"[skip] {project.name}: .no-overview flag present")
        return 0
    wiki_root = _active_version_dir(project)
    if wiki_root is None:
        print(f"[skip] {project.name}: no active version directory")
        return 0
    if (wiki_root / "overview.html").exists() and not force:
        print(f"[skip] {project.name}: overview.html already exists (use --force to regenerate)")
        return 0
    worklist = overview_lib.discover_worklist(wiki_root)
    if not worklist:
        print(f"[skip] {project.name}: no focus pages found")
        return 0
    if dry_run:
        print(f"[dry-run] {project.name}: would retrofit {sum(len(v) for v in worklist.values())} cards across {len(worklist)} modules")
        return 0
    rc = run_overview_pass(
        wiki_root=wiki_root, worklist=worklist,
        project_name=project.name, project_tagline="",
    )
    if rc != 0:
        print(f"[fail] {project.name}: Copilot exit {rc}")
        return rc
    _gate_d(wiki_root)  # non-blocking in retrofit mode
    _inject_nav(wiki_root)
    print(f"[ok] {project.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Retrofit overview.html into existing wikis.")
    p.add_argument("projects", nargs="*", help="Project directories (default: all)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--confirm-each", action="store_true")
    args = p.parse_args((argv or sys.argv)[1:])

    projects = _iter_project_dirs(args.projects)
    if not projects:
        print("No projects found.", file=sys.stderr)
        return 1
    print(f"Retrofitting {len(projects)} project(s).")
    failures = 0
    for proj in projects:
        if args.confirm_each:
            ans = input(f"Retrofit {proj.name}? [y/N] ").strip().lower()
            if ans != "y":
                continue
        rc = retrofit_one(proj, force=args.force, dry_run=args.dry_run)
        if rc != 0:
            failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
