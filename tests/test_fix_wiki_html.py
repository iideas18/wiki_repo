"""Regression tests for fix_wiki_html overlay click handling."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import fix_wiki_html  # noqa: E402


def _make_html_file(tmp_path: Path, body: str) -> Path:
    html_path = tmp_path / "sample" / "index.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(f"<html><body><script>{body}</script></body></html>", encoding="utf-8")
    return html_path


def test_scan_issues_ignores_close_button_handlers(monkeypatch, tmp_path):
    html_path = _make_html_file(
        tmp_path,
        "closeBtn.addEventListener('click', function () { overlay.classList.remove('active'); });"
        "overlay.addEventListener('click', function (e) { if (e.target === overlay) overlay.classList.remove('active'); });",
    )
    monkeypatch.setattr(fix_wiki_html, "WIKI_DIR", tmp_path)

    issues = fix_wiki_html.scan_issues(html_path, html_path.read_text(encoding="utf-8"))

    assert not any("overlay click handler missing e.target check" in issue for issue in issues)


def test_scan_issues_flags_unguarded_overlay_handler(monkeypatch, tmp_path):
    html_path = _make_html_file(
        tmp_path,
        "overlay.addEventListener('click', function() { overlay.classList.remove('active'); overlay.innerHTML = ''; });",
    )
    monkeypatch.setattr(fix_wiki_html, "WIKI_DIR", tmp_path)

    issues = fix_wiki_html.scan_issues(html_path, html_path.read_text(encoding="utf-8"))

    assert any("overlay click handler missing e.target check" in issue for issue in issues)


def test_file_fixer_adds_target_guard_to_overlay_handler(monkeypatch, tmp_path):
    html_path = _make_html_file(
        tmp_path,
        "overlay.addEventListener('click', function() { overlay.classList.remove('active'); overlay.innerHTML = ''; });",
    )
    monkeypatch.setattr(fix_wiki_html, "WIKI_DIR", tmp_path)

    fixer = fix_wiki_html.FileFixer(html_path)
    fixer.fix_overlay_click_propagation()

    assert "if (e.target === overlay)" in fixer.text
    assert "overlay.innerHTML = '';" in fixer.text
