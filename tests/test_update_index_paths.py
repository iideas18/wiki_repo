"""Tests for update_index path normalization helpers."""

import update_index


def test_extract_project_slug_from_legacy_href():
    assert update_index.extract_project_slug_from_href("alpha/20260421_120000/index.html") == "alpha"


def test_extract_project_slug_from_wiki_href():
    assert update_index.extract_project_slug_from_href("wiki/alpha/20260421_120000/index.html") == "alpha"


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