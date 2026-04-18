"""Tests for verify.sh --stage=D structural checks on overview.html."""
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFY_SH = REPO_ROOT / ".github" / "skills" / "wiki-generator" / "scripts" / "verify.sh"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "overview"


def _run_gate_d(project_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(VERIFY_SH), "--stage=D", f"--project={project_dir}"],
        capture_output=True, text=True, check=False,
    )


def test_gate_d_passes_on_golden_fixture(tmp_path):
    # Materialize a project layout with good overview.html + referenced focus page.
    shutil.copytree(FIXTURES, tmp_path / "wiki", ignore=shutil.ignore_patterns("bad-*"))
    (tmp_path / "wiki" / "overview.html").write_bytes(
        (FIXTURES / "good-overview.html").read_bytes()
    )
    result = _run_gate_d(tmp_path / "wiki")
    assert result.returncode == 0, result.stderr


def test_gate_d_fails_when_no_overview(tmp_path):
    (tmp_path / "wiki").mkdir()
    result = _run_gate_d(tmp_path / "wiki")
    assert result.returncode != 0


def test_gate_d_fails_on_placeholder(tmp_path):
    shutil.copytree(FIXTURES, tmp_path / "wiki", ignore=shutil.ignore_patterns("bad-*"))
    (tmp_path / "wiki" / "overview.html").write_bytes(
        (FIXTURES / "bad-placeholder" / "overview.html").read_bytes()
    )
    result = _run_gate_d(tmp_path / "wiki")
    assert result.returncode != 0


def test_gate_d_fails_on_broken_href(tmp_path):
    shutil.copytree(FIXTURES, tmp_path / "wiki", ignore=shutil.ignore_patterns("bad-*"))
    (tmp_path / "wiki" / "overview.html").write_bytes(
        (FIXTURES / "good-overview.html").read_bytes()
    )
    # Delete the referenced focus page so the href cannot resolve.
    target = tmp_path / "wiki" / "mod-alpha" / "focus-one" / "index.html"
    target.unlink()
    result = _run_gate_d(tmp_path / "wiki")
    assert result.returncode != 0
