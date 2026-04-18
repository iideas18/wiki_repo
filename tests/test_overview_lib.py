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


STATS_PAGE = """
<!doctype html><html><body>
  <main>
    <div class="mermaid">graph TD; A-->B;</div>
    <p>First.</p>
    <p>Second.</p>
    <ul><li>item one</li><li>item two</li></ul>
    <span data-file-ref="src/a.py:10">a.py</span>
    <span data-file-ref="src/b.py:20">b.py</span>
    <div class="mermaid">second diagram</div>
  </main>
</body></html>
"""


def test_count_stats_exact_counts():
    stats = overview_lib.count_stats(STATS_PAGE)
    assert stats == {"diagrams": 2, "refs": 2, "lines": 4}


def test_count_stats_zero_when_empty():
    assert overview_lib.count_stats("<html><body><main></main></body></html>") == {
        "diagrams": 0, "refs": 0, "lines": 0,
    }


TRUNCATION_NOTE = "<p><em>Preview truncated — see full page.</em></p>"


def test_truncate_preview_noop_below_limit():
    small = "<p>Small.</p>"
    assert overview_lib.truncate_preview(small, max_bytes=1024) == small


def test_truncate_preview_truncates_and_appends_notice():
    big = "<p>" + ("A" * 70000) + "</p>"
    out = overview_lib.truncate_preview(big, max_bytes=65536)
    assert out.endswith(TRUNCATION_NOTE)
    assert len(out.encode("utf-8")) <= 65536 + len(TRUNCATION_NOTE.encode("utf-8")) + 16


def test_truncate_preview_prefers_paragraph_boundary():
    p = "<p>" + ("B" * 40000) + "</p>"
    big = p + p  # two 40k paragraphs → >65536 total
    out = overview_lib.truncate_preview(big, max_bytes=65536)
    # We should keep one full <p>...</p> and drop the rest, then append notice.
    assert out.count("<p>") == 2  # one kept + notice <p>
    assert out.endswith(TRUNCATION_NOTE)


NAV_HTML_WITH = """<!doctype html><html><body>
<nav><a href="index.html">Home</a></nav>
<main>body</main></body></html>"""

NAV_HTML_WITHOUT_NAV = """<!doctype html><html><body>
<main>body</main></body></html>"""


def test_inject_nav_link_inserts_when_missing():
    out, changed = overview_lib.inject_nav_link(NAV_HTML_WITH, "overview.html", "Overview")
    assert changed is True
    assert 'href="overview.html"' in out
    assert ">Overview</a>" in out


def test_inject_nav_link_is_idempotent():
    once, _ = overview_lib.inject_nav_link(NAV_HTML_WITH, "overview.html", "Overview")
    twice, changed = overview_lib.inject_nav_link(once, "overview.html", "Overview")
    assert changed is False
    assert once == twice


def test_inject_nav_link_creates_nav_if_missing():
    out, changed = overview_lib.inject_nav_link(NAV_HTML_WITHOUT_NAV, "overview.html", "Overview")
    assert changed is True
    assert "<nav>" in out
    assert 'href="overview.html"' in out


def test_inject_nav_link_respects_relative_prefix():
    out, _ = overview_lib.inject_nav_link(NAV_HTML_WITH, "../overview.html", "Overview")
    assert 'href="../overview.html"' in out
