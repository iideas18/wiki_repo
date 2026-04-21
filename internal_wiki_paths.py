#!/usr/bin/env python3
"""Shared path helpers for the internal wiki repository."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
CANONICAL_PROJECTS_ROOT = REPO_ROOT / "wiki"
HUB_INDEX = REPO_ROOT / "index.html"

TIMESTAMP_RE = re.compile(r"^\d{8}_\d{6}$")
ROOT_NON_PROJECT_DIRS = {
    "__pycache__",
    "docs",
    "logs",
    "tests",
    "wiki",
}


def is_project_dir(path: Path) -> bool:
    """Return True when a directory looks like a wiki project root."""
    if not path.is_dir() or path.name.startswith("."):
        return False
    if path.parent == REPO_ROOT and path.name in ROOT_NON_PROJECT_DIRS:
        return False
    if (path / "versions.json").is_file():
        return True
    if (path / "index.html").is_file() and (path / "search-index.json").is_file():
        return True

    try:
        children = sorted(path.iterdir(), reverse=True)
    except OSError:
        return False

    for child in children:
        if not child.is_dir() or not TIMESTAMP_RE.match(child.name):
            continue
        if (child / "index.html").is_file():
            return True
    return False


def get_projects_root() -> Path:
    """Return the canonical projects root when it exists, else the repo root."""
    if CANONICAL_PROJECTS_ROOT.is_dir():
        return CANONICAL_PROJECTS_ROOT
    return REPO_ROOT


def _iter_root_projects(root: Path) -> list[Path]:
    try:
        entries = sorted(root.iterdir())
    except OSError:
        return []
    return [entry for entry in entries if is_project_dir(entry)]


def iter_project_dirs() -> list[Path]:
    """Enumerate project directories with mixed-layout migration support.

    If both repo-root and `wiki/` layouts are visible, prefer `wiki/<slug>` for any
    duplicate slug and keep repo-root projects only for slugs that have not moved yet.
    """
    projects_by_slug: dict[str, Path] = {}
    if CANONICAL_PROJECTS_ROOT.is_dir():
        for project_dir in _iter_root_projects(CANONICAL_PROJECTS_ROOT):
            projects_by_slug[project_dir.name] = project_dir
    for project_dir in _iter_root_projects(REPO_ROOT):
        projects_by_slug.setdefault(project_dir.name, project_dir)
    return [projects_by_slug[name] for name in sorted(projects_by_slug)]


def resolve_project_dir(name_or_path: str) -> Path:
    """Resolve a project argument to the canonical directory for that slug."""
    candidate = Path(name_or_path)
    if candidate.is_absolute() or len(candidate.parts) > 1 or name_or_path.startswith("."):
        if candidate.exists():
            return candidate.resolve()

    canonical = CANONICAL_PROJECTS_ROOT / name_or_path
    if canonical.is_dir():
        return canonical

    legacy = REPO_ROOT / name_or_path
    if legacy.is_dir() and is_project_dir(legacy):
        return legacy

    if candidate.exists():
        return candidate.resolve()

    repo_candidate = (REPO_ROOT / candidate).resolve()
    if repo_candidate.exists():
        return repo_candidate

    return canonical if CANONICAL_PROJECTS_ROOT.is_dir() else legacy


def repo_relative(path: Path) -> str:
    """Render a repo-relative POSIX path when possible."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()