"""Tests for internal_wiki_paths.py."""

from pathlib import Path

import internal_wiki_paths


def _make_project(project_root: Path, timestamp: str = "20260421_120000") -> Path:
    project_root.mkdir(parents=True, exist_ok=True)
    version_dir = project_root / timestamp
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    (project_root / "versions.json").write_text("[]\n", encoding="utf-8")
    return project_root


def test_get_projects_root_falls_back_to_repo_root_when_wiki_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(internal_wiki_paths, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(internal_wiki_paths, "CANONICAL_PROJECTS_ROOT", tmp_path / "wiki")
    assert internal_wiki_paths.get_projects_root() == tmp_path


def test_iter_project_dirs_prefers_canonical_projects_root(tmp_path, monkeypatch):
    repo_root = tmp_path
    canonical_root = repo_root / "wiki"
    canonical_root.mkdir()
    _make_project(repo_root / "alpha")
    wiki_alpha = _make_project(canonical_root / "alpha")
    legacy_beta = _make_project(repo_root / "beta")

    monkeypatch.setattr(internal_wiki_paths, "REPO_ROOT", repo_root)
    monkeypatch.setattr(internal_wiki_paths, "CANONICAL_PROJECTS_ROOT", canonical_root)

    projects = internal_wiki_paths.iter_project_dirs()
    assert projects == [wiki_alpha, legacy_beta]


def test_resolve_project_dir_prefers_canonical_slug(tmp_path, monkeypatch):
    repo_root = tmp_path
    canonical_root = repo_root / "wiki"
    canonical_root.mkdir()
    _make_project(repo_root / "alpha")
    wiki_alpha = _make_project(canonical_root / "alpha")

    monkeypatch.setattr(internal_wiki_paths, "REPO_ROOT", repo_root)
    monkeypatch.setattr(internal_wiki_paths, "CANONICAL_PROJECTS_ROOT", canonical_root)

    assert internal_wiki_paths.resolve_project_dir("alpha") == wiki_alpha