"""Unit tests for overview_lib.py."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / ".github" / "skills" / "wiki-generator" / "scripts"))

import overview_lib  # noqa: E402


def test_escape_for_attribute_roundtrips_simple_html():
    html = "<p>Hello <em>world</em></p>"
    escaped = overview_lib.escape_for_attribute(html)
    # Must not contain raw quote chars that would break the attribute
    assert '"' not in escaped
    # Must be parseable back via html.unescape
    import html as stdlib_html
    assert stdlib_html.unescape(escaped) == html


def test_escape_for_attribute_handles_quotes_and_ampersands():
    html = '<p class="x">A & B said "hi"</p>'
    escaped = overview_lib.escape_for_attribute(html)
    assert '"' not in escaped
    assert '&amp;' in escaped
    import html as stdlib_html
    assert stdlib_html.unescape(escaped) == html


def test_escape_for_attribute_preserves_unicode():
    html = "<p>你好 — café</p>"
    escaped = overview_lib.escape_for_attribute(html)
    import html as stdlib_html
    assert stdlib_html.unescape(escaped) == html

LAYERED_PAGE = """
<!doctype html><html><body>
  <main>
    <section data-layer="primer"><p>Primer intro.</p></section>
    <section data-layer="core-idea"><p>Core idea body.</p></section>
    <section data-layer="in-depth"><p>Expert detail — excluded.</p></section>
  </main>
</body></html>
"""

UNLAYERED_PAGE = """
<!doctype html><html><body>
  <main>
    <p>First paragraph becomes primer.</p>
    <p>Second paragraph becomes core-idea.</p>
    <p>Third paragraph also core-idea.</p>
    <p>Fourth paragraph — excluded.</p>
  </main>
</body></html>
"""


def test_extract_preview_html_uses_layered_regions_when_present():
    preview, retrofit = overview_lib.extract_preview_html(LAYERED_PAGE)
    assert "Primer intro." in preview
    assert "Core idea body." in preview
    assert "Expert detail" not in preview
    assert retrofit is False


def test_extract_preview_html_falls_back_to_paragraphs():
    preview, retrofit = overview_lib.extract_preview_html(UNLAYERED_PAGE)
    assert "First paragraph becomes primer." in preview
    assert "Second paragraph becomes core-idea." in preview
    assert "Third paragraph also core-idea." in preview
    assert "Fourth paragraph" not in preview
    assert retrofit is True


def test_extract_preview_html_retrofit_banner_added_by_caller_not_extractor():
    # extract_preview_html returns raw HTML and a retrofit flag; the caller
    # (overview pass / retrofit) is responsible for prepending a banner.
    preview, retrofit = overview_lib.extract_preview_html(UNLAYERED_PAGE)
    assert "retrofit-banner" not in preview
    assert retrofit is True
