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
