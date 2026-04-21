"""Tests for update_index path normalization helpers."""

import update_index


def test_extract_project_slug_from_legacy_href():
    assert update_index.extract_project_slug_from_href("alpha/20260421_120000/index.html") == "alpha"


def test_extract_project_slug_from_wiki_href():
    assert update_index.extract_project_slug_from_href("wiki/alpha/20260421_120000/index.html") == "alpha"


def test_extract_project_slug_from_internal_href():
    assert update_index.extract_project_slug_from_href("internal/alpha/20260421_120000/index.html") == "alpha"


def test_dedupe_card_grid_prefers_wiki_href_for_same_slug():
    content = """
<div class="card-grid">
  <a class="card" href="alpha/20260421_120000/index.html">
    <h3>Alpha</h3>
  </a>

  <a class="card" href="wiki/alpha/20260422_120000/index.html">
    <h3>Alpha</h3>
  </a>

  <a class="card" href="wiki/beta/20260422_120000/index.html">
    <h3>Beta</h3>
  </a>
</div>

<h2 id="about">About</h2>
"""
    deduped = update_index.dedupe_card_grid(content)
    assert deduped.count('<a class="card" href="') == 2
    assert 'href="wiki/alpha/20260422_120000/index.html"' in deduped
    assert 'href="alpha/20260421_120000/index.html"' not in deduped


def test_dedupe_card_grid_prefers_relative_href_for_internal_same_slug():
    content = """
<div class="card-grid">
  <a class="card" href="internal/alpha/20260422_120000/index.html">
    <h3>Alpha</h3>
  </a>

  <a class="card" href="alpha/20260423_120000/index.html">
    <h3>Alpha</h3>
  </a>
</div>

<h2 id="about">About</h2>
"""
    deduped = update_index.dedupe_card_grid(content, preferred_prefix=None)
    assert 'href="alpha/20260423_120000/index.html"' in deduped
    assert 'href="internal/alpha/20260422_120000/index.html"' not in deduped


def test_build_project_uses_internal_hub_relative_href(tmp_path):
    hub_index = tmp_path / "internal" / "index.html"
    hub_index.parent.mkdir(parents=True, exist_ok=True)
    index_path = tmp_path / "internal" / "alpha" / "20260421_120000" / "index.html"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        '<meta name="wiki-generated" content="2026-04-21"><title>Alpha - Internal</title>',
        encoding="utf-8",
    )

    project = update_index.build_project(index_path, hub_index=hub_index)

    assert project is not None
    assert project["href"] == "alpha/20260421_120000/index.html"


def test_update_stats_internal_updates_versioned_projects_count():
    content = """
<div class="stat-row">
  <div class="stat-box"><div class="num">0</div><div class="label">Projects</div></div>
  <div class="stat-box"><div class="num">0</div><div class="label">Wiki Pages</div></div>
  <div class="stat-box"><div class="num">0</div><div class="label">Versioned Projects</div></div>
</div>
<div class="card-grid">
  <a class="card" href="alpha/20260421_120000/index.html"><div class="meta"><span>&#128196; 10 pages</span></div></a>
  <a class="card" href="beta/index.html"><div class="meta"><span>&#128196; 7 pages</span></div></a>
</div>
"""
    updated = update_index.update_stats(content, stats_mode="internal")
    assert '<div class="num">2</div><div class="label">Projects</div>' in updated
    assert '<div class="num">17</div><div class="label">Wiki Pages</div>' in updated
    assert '<div class="num">1</div><div class="label">Versioned Projects</div>' in updated


def test_run_post_scripts_forwards_selected_root(tmp_path, monkeypatch):
    repo_root = tmp_path
    for script_name in ("generate_versions.py", "inject_version_switcher.py"):
        (repo_root / script_name).write_text("# stub\n", encoding="utf-8")

    monkeypatch.setattr(update_index, "REPO_ROOT", repo_root)
    commands = []

    def fake_run(cmd, cwd=None):
        commands.append((cmd, cwd))

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(update_index.subprocess, "run", fake_run)

    update_index._run_post_scripts(["alpha"], "internal")

    assert len(commands) == 2
    for cmd, cwd in commands:
        assert "--root" in cmd
        assert "internal" in cmd
        assert "alpha" in cmd
        assert cwd == str(repo_root)