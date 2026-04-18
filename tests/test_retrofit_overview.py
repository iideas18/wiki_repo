"""Tests for retrofit_overview.py. Copilot invocation is monkey-patched."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import retrofit_overview  # noqa: E402


def _make_project(tmp_path: Path, slug: str) -> Path:
    proj = tmp_path / slug
    proj.mkdir()
    (proj / "versions.json").write_text(
        json.dumps([{"timestamp": "v1", "latest": True}]), encoding="utf-8"
    )
    v1 = proj / "v1"
    v1.mkdir()
    (v1 / "index.html").write_text(
        '<html><body><nav></nav><main><section class="deep-dive-hub">'
        '<a href="mod-alpha/focus-one/index.html">Alpha Focus One</a>'
        '</section></main></body></html>',
        encoding="utf-8",
    )
    focus = v1 / "mod-alpha" / "focus-one"
    focus.mkdir(parents=True)
    (focus / "index.html").write_text(
        "<html><body><main><h1>Alpha Focus One</h1>"
        "<p>Primer para.</p><p>Core idea para.</p></main></body></html>",
        encoding="utf-8",
    )
    return proj


def test_retrofit_skips_when_overview_exists(tmp_path, monkeypatch):
    proj = _make_project(tmp_path, "proj-a")
    (proj / "v1" / "overview.html").write_text("pre-existing", encoding="utf-8")
    called = {"n": 0}
    monkeypatch.setattr(retrofit_overview, "run_overview_pass", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or 0)
    assert retrofit_overview.main(["retrofit_overview.py", str(proj)]) == 0
    assert called["n"] == 0


def test_retrofit_honors_no_overview_flag(tmp_path, monkeypatch):
    proj = _make_project(tmp_path, "proj-b")
    (proj / ".no-overview").touch()
    called = {"n": 0}
    monkeypatch.setattr(retrofit_overview, "run_overview_pass", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or 0)
    assert retrofit_overview.main(["retrofit_overview.py", str(proj)]) == 0
    assert called["n"] == 0


def test_retrofit_invokes_pass_once_per_project(tmp_path, monkeypatch):
    proj = _make_project(tmp_path, "proj-c")
    invoked = []

    def fake_run_pass(*, wiki_root, worklist, project_name, project_tagline):
        invoked.append((wiki_root, sorted(worklist.keys())))
        (wiki_root / "overview.html").write_text("stub", encoding="utf-8")
        return 0

    monkeypatch.setattr(retrofit_overview, "run_overview_pass", fake_run_pass)
    assert retrofit_overview.main(["retrofit_overview.py", str(proj), "--force"]) == 0
    assert len(invoked) == 1
    assert invoked[0][1] == ["mod-alpha"]
