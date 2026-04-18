"""Tests for inject_overview_link.py CLI."""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".github" / "skills" / "wiki-generator" / "scripts" / "inject_overview_link.py"


def _run(project_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(project_dir)],
        capture_output=True, text=True, check=False,
    )


def test_injects_link_in_top_level_index(tmp_path):
    (tmp_path / "index.html").write_text(
        '<html><body><nav><a href="index.html">Home</a></nav></body></html>',
        encoding="utf-8",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert 'href="overview.html"' in (tmp_path / "index.html").read_text()


def test_injects_relative_link_in_module_index(tmp_path):
    (tmp_path / "index.html").write_text(
        '<html><body><nav></nav></body></html>', encoding="utf-8",
    )
    mod = tmp_path / "mod-alpha"
    mod.mkdir()
    (mod / "index.html").write_text(
        '<html><body><nav></nav></body></html>', encoding="utf-8",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert 'href="overview.html"' in (tmp_path / "index.html").read_text()
    assert 'href="../overview.html"' in (mod / "index.html").read_text()


def test_is_idempotent(tmp_path):
    (tmp_path / "index.html").write_text(
        '<html><body><nav></nav></body></html>', encoding="utf-8",
    )
    _run(tmp_path)
    before = (tmp_path / "index.html").read_text()
    _run(tmp_path)
    after = (tmp_path / "index.html").read_text()
    assert before == after
