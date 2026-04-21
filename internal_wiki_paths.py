#!/usr/bin/env python3
"""Shared path helpers for the internal wiki repository."""

from __future__ import annotations

import re
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PUBLIC_PROJECTS_ROOT = REPO_ROOT / "wiki"
INTERNAL_PROJECTS_ROOT = REPO_ROOT / "internal"
CANONICAL_PROJECTS_ROOT = PUBLIC_PROJECTS_ROOT
HUB_INDEX = REPO_ROOT / "index.html"
INTERNAL_HUB_INDEX = INTERNAL_PROJECTS_ROOT / "index.html"

TIMESTAMP_RE = re.compile(r"^\d{8}_\d{6}$")
ROOT_NON_PROJECT_DIRS = {
    "__pycache__",
    "docs",
    "internal",
    "logs",
    "tests",
    "wiki",
}


def normalize_root_name(root_name: str | None = None) -> str:
    """Normalize a logical content-root selector."""
    root = (root_name or "public").strip().lower()
    if root not in {"public", "internal"}:
        raise ValueError(f"Unsupported wiki root: {root_name}")
    return root


def get_named_projects_root(root_name: str | None = None) -> Path:
    """Return the configured projects root for a logical site."""
    root = normalize_root_name(root_name)
    return PUBLIC_PROJECTS_ROOT if root == "public" else INTERNAL_PROJECTS_ROOT


def get_hub_index(root_name: str | None = None) -> Path:
    """Return the hub index path for a logical site."""
    root = normalize_root_name(root_name)
    return HUB_INDEX if root == "public" else INTERNAL_HUB_INDEX


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


def get_projects_root(root_name: str | None = None) -> Path:
    """Return the canonical projects root for a logical site.

    Public mode preserves the historical fallback to the repo root when `wiki/`
    does not yet exist. Internal mode stays rooted at `internal/` explicitly.
    """
    root = normalize_root_name(root_name)
    projects_root = get_named_projects_root(root)
    if root == "public":
        if projects_root.is_dir():
            return projects_root
        return REPO_ROOT
    return projects_root


def _iter_root_projects(root: Path) -> list[Path]:
    try:
        entries = sorted(root.iterdir())
    except OSError:
        return []
    return [entry for entry in entries if is_project_dir(entry)]


def iter_project_dirs(root_name: str | None = None) -> list[Path]:
    """Enumerate project directories with mixed-layout migration support.

    If both repo-root and `wiki/` layouts are visible, prefer `wiki/<slug>` for any
    duplicate slug and keep repo-root projects only for slugs that have not moved yet.
    """
    root = normalize_root_name(root_name)
    if root == "internal":
        projects_root = get_named_projects_root(root)
        if not projects_root.is_dir():
            return []
        return _iter_root_projects(projects_root)

    projects_by_slug: dict[str, Path] = {}
    if CANONICAL_PROJECTS_ROOT.is_dir():
        for project_dir in _iter_root_projects(CANONICAL_PROJECTS_ROOT):
            projects_by_slug[project_dir.name] = project_dir
    for project_dir in _iter_root_projects(REPO_ROOT):
        projects_by_slug.setdefault(project_dir.name, project_dir)
    return [projects_by_slug[name] for name in sorted(projects_by_slug)]


def resolve_project_dir(name_or_path: str, root_name: str | None = None) -> Path:
    """Resolve a project argument to the canonical directory for that slug."""
    root = normalize_root_name(root_name)
    candidate = Path(name_or_path)
    if candidate.is_absolute() or len(candidate.parts) > 1 or name_or_path.startswith("."):
        if candidate.exists():
            return candidate.resolve()

    canonical_root = get_named_projects_root(root)
    canonical = canonical_root / name_or_path
    if canonical.is_dir():
        return canonical

    if root == "internal":
        if candidate.exists():
            return candidate.resolve()
        repo_candidate = (REPO_ROOT / candidate).resolve()
        if repo_candidate.exists():
            return repo_candidate
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


def relative_href(from_path: Path, to_path: Path) -> str:
    """Render a POSIX relative href from one file path to another path."""
    return Path(os.path.relpath(to_path.resolve(), start=from_path.resolve().parent)).as_posix()