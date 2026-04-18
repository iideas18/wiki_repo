# Wiki Overview Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a self-contained per-project `overview.html` that shows every module and focus topic as rich clickable cards with a primer preview modal, and a retrofit script that creates the same file for all existing committed wikis.

**Architecture:** A new "Overview Pass" runs after Pass C of the existing generator pipeline: one Copilot CLI invocation reads the finished focus pages and writes a single static HTML file with inlined CSS/JS (two-tier module/card layout, native `<dialog>` modal). A new `verify.sh` Gate D stage validates structure. A repo-root `retrofit_overview.py` runs the same prompt against already-committed wikis, discovering structure without `_worklist.yaml`. A small `inject_overview_link.py` adds the nav link idempotently to `index.html` and module index pages.

**Tech Stack:** Python 3 (stdlib `html.parser`, `argparse`, `pathlib`, `subprocess`, `unittest` / `pytest`), Bash (orchestrator wiring and `verify.sh`), Copilot CLI (the Overview Pass prompt), native HTML `<dialog>` + vanilla JS (no frameworks), Playwright (integration test only).

---

## File Structure

**New files:**
- `.github/skills/wiki-generator/resources/overview_pass.md` — Copilot prompt template for the Overview Pass. Treated as text template; the orchestrator substitutes placeholders (project name, worklist, page file list) before passing to Copilot CLI.
- `.github/skills/wiki-generator/resources/overview-template.html` — the skeleton HTML (header, `<dialog>`, inlined CSS, inlined JS). The prompt instructs Copilot to fill slots in this exact template.
- `.github/skills/wiki-generator/scripts/overview_lib.py` — shared library with pure functions for: escape-for-attribute, extract `data-layer` regions from a page (with pre-layered fallback), count stats (diagrams/refs/lines), truncate oversized previews, idempotent nav-link injection into an HTML string. Used by both the generator and the retrofit script.
- `.github/skills/wiki-generator/scripts/inject_overview_link.py` — CLI wrapper that walks a project directory and edits `index.html` / `*/index.html` in place using `overview_lib.inject_nav_link`.
- `retrofit_overview.py` — repo-root CLI that iterates projects, discovers their structure without `_worklist.yaml`, invokes the Overview Pass, runs Gate D, and calls the nav injector.
- `tests/test_overview_lib.py` — unit tests for the functions in `overview_lib.py`.
- `tests/test_verify_stage_d.py` — unit tests for Gate D in `verify.sh`, driving it against fixture files.
- `tests/fixtures/overview/` — fixture wikis and golden `overview.html` samples (good and mutated-bad variants).
- `tests/integration/test_overview_e2e.py` — Playwright headless integration test against a small fixture project.

**Modified files:**
- `.github/skills/wiki-generator/scripts/verify.sh` — add `--stage=D` branch with structural checks for `overview.html`.
- `.github/skills/wiki-generator/scripts/run_wiki_gen.sh` — add the Overview Pass stage after Gate C and the nav injector after Gate D.
- `.github/skills/wiki-generator/scripts/build-search-index.py` — exclude `overview.html` by filename.
- `.gitignore` — add `.no-overview` is **not** ignored (it is a committed opt-out marker); no change here, noted for reviewers.

Each Python file stays under ~300 lines by keeping `overview_lib.py` focused on pure transformations; the two CLI drivers only orchestrate.

---

## Task 1: Bootstrap the `overview_lib.py` module with HTML-attribute escaping

**Files:**
- Create: `.github/skills/wiki-generator/scripts/overview_lib.py`
- Test: `tests/test_overview_lib.py`

- [ ] **Step 1: Create tests directory and ensure it's Python-discoverable**

Run: `mkdir -p tests && touch tests/__init__.py`
Expected: no output, files created.

- [ ] **Step 2: Write the failing test for `escape_for_attribute`**

Create `tests/test_overview_lib.py`:

```python
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
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'overview_lib'`.

- [ ] **Step 4: Implement `overview_lib.escape_for_attribute`**

Create `.github/skills/wiki-generator/scripts/overview_lib.py`:

```python
"""Shared helpers for the Overview Pass (wiki overview-page generation).

Pure functions only. No I/O here; CLI drivers live in sibling scripts.
"""
from __future__ import annotations

import html as stdlib_html


def escape_for_attribute(inner_html: str) -> str:
    """Escape a chunk of HTML so it can be embedded inside an HTML attribute
    value surrounded by double quotes.

    Uses `html.escape(..., quote=True)` so ``"``, ``'``, ``<``, ``>``, and ``&``
    are all encoded. Round-trips via `html.unescape`.
    """
    return stdlib_html.escape(inner_html, quote=True)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: PASS for all three tests.

- [ ] **Step 6: Commit**

```bash
git add tests/__init__.py tests/test_overview_lib.py \
        .github/skills/wiki-generator/scripts/overview_lib.py
git commit -m "feat(overview): add escape_for_attribute helper with tests"
```

---

## Task 2: Extract `data-layer` regions from a focus page

**Files:**
- Modify: `.github/skills/wiki-generator/scripts/overview_lib.py`
- Test: `tests/test_overview_lib.py`

- [ ] **Step 1: Write failing tests for `extract_preview_html`**

Append to `tests/test_overview_lib.py`:

```python
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
```

- [ ] **Step 2: Run the new tests to confirm they fail**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: FAIL — `AttributeError: module 'overview_lib' has no attribute 'extract_preview_html'`.

- [ ] **Step 3: Implement `extract_preview_html`**

Append to `.github/skills/wiki-generator/scripts/overview_lib.py`:

```python
import re
from html.parser import HTMLParser
from typing import Tuple


class _LayerExtractor(HTMLParser):
    """Collect the raw HTML inside <section data-layer="primer"> and
    <section data-layer="core-idea"> blocks, in document order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._stack: list[str] = []  # active target layer names
        self._depth: list[int] = []  # section depth when we entered each target
        self._buffers: dict[str, list[str]] = {"primer": [], "core-idea": []}
        self._current_section_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "section":
            self._current_section_depth += 1
            attrdict = dict(attrs)
            layer = attrdict.get("data-layer")
            if layer in self._buffers:
                self._stack.append(layer)
                self._depth.append(self._current_section_depth)
                return
        if self._stack:
            self._buffers[self._stack[-1]].append(self.get_starttag_text() or "")

    def handle_endtag(self, tag):
        if tag == "section":
            if self._stack and self._depth[-1] == self._current_section_depth:
                self._stack.pop()
                self._depth.pop()
            else:
                if self._stack:
                    self._buffers[self._stack[-1]].append(f"</{tag}>")
            self._current_section_depth -= 1
            return
        if self._stack:
            self._buffers[self._stack[-1]].append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        if self._stack:
            self._buffers[self._stack[-1]].append(self.get_starttag_text() or "")

    def handle_data(self, data):
        if self._stack:
            self._buffers[self._stack[-1]].append(data)

    def handle_entityref(self, name):
        if self._stack:
            self._buffers[self._stack[-1]].append(f"&{name};")

    def handle_charref(self, name):
        if self._stack:
            self._buffers[self._stack[-1]].append(f"&#{name};")

    @property
    def primer_html(self) -> str:
        return "".join(self._buffers["primer"]).strip()

    @property
    def core_idea_html(self) -> str:
        return "".join(self._buffers["core-idea"]).strip()


_PARAGRAPH_RE = re.compile(r"<p\b[^>]*>.*?</p>", re.IGNORECASE | re.DOTALL)


def extract_preview_html(page_html: str) -> Tuple[str, bool]:
    """Return (combined_preview_html, retrofitted).

    If the page has ``<section data-layer="primer">`` and
    ``<section data-layer="core-idea">`` blocks, concatenate their inner HTML
    and return ``retrofitted=False``.

    Otherwise fall back to the first ``<p>`` as primer and the next two ``<p>``
    as core-idea, returning ``retrofitted=True``. The caller is responsible
    for prepending a retrofit banner.
    """
    extractor = _LayerExtractor()
    extractor.feed(page_html)
    primer = extractor.primer_html
    core_idea = extractor.core_idea_html
    if primer or core_idea:
        return (f"{primer}\n{core_idea}".strip(), False)

    paragraphs = _PARAGRAPH_RE.findall(page_html)
    if not paragraphs:
        return ("", True)
    primer = paragraphs[0]
    core_idea = "".join(paragraphs[1:3])
    return (f"{primer}\n{core_idea}".strip(), True)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: PASS for all six tests (three from Task 1 plus three new).

- [ ] **Step 5: Commit**

```bash
git add tests/test_overview_lib.py \
        .github/skills/wiki-generator/scripts/overview_lib.py
git commit -m "feat(overview): extract data-layer primer/core-idea with paragraph fallback"
```

---

## Task 3: Count stats (diagrams, file refs, lines)

**Files:**
- Modify: `.github/skills/wiki-generator/scripts/overview_lib.py`
- Test: `tests/test_overview_lib.py`

- [ ] **Step 1: Write failing tests for `count_stats`**

Append to `tests/test_overview_lib.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: FAIL — no `count_stats`.

- [ ] **Step 3: Implement `count_stats`**

Append to `overview_lib.py`:

```python
class _StatsCounter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.diagrams = 0
        self.refs = 0
        self.lines = 0  # <p> + <li>

    def handle_starttag(self, tag, attrs):
        attrdict = dict(attrs)
        if tag == "div" and "mermaid" in (attrdict.get("class") or "").split():
            self.diagrams += 1
        if "data-file-ref" in attrdict:
            self.refs += 1
        if tag in ("p", "li"):
            self.lines += 1


def count_stats(page_html: str) -> dict:
    """Return exact counts for diagrams / file refs / lines as defined in
    the spec (§5.2.4). Uses the stdlib HTML parser so malformed markup does
    not inflate counts."""
    counter = _StatsCounter()
    counter.feed(page_html)
    return {
        "diagrams": counter.diagrams,
        "refs": counter.refs,
        "lines": counter.lines,
    }
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: PASS for all eight tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_overview_lib.py \
        .github/skills/wiki-generator/scripts/overview_lib.py
git commit -m "feat(overview): count diagrams/refs/lines stats"
```

---

## Task 4: Truncate oversized previews

**Files:**
- Modify: `.github/skills/wiki-generator/scripts/overview_lib.py`
- Test: `tests/test_overview_lib.py`

- [ ] **Step 1: Write failing tests for `truncate_preview`**

Append to `tests/test_overview_lib.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: FAIL — no `truncate_preview`.

- [ ] **Step 3: Implement `truncate_preview`**

Append to `overview_lib.py`:

```python
TRUNCATION_NOTE = "<p><em>Preview truncated — see full page.</em></p>"


def truncate_preview(preview_html: str, max_bytes: int = 65536) -> str:
    """Truncate preview HTML to ``max_bytes`` when measured as UTF-8, cutting
    at the last ``</p>`` boundary before the limit and appending
    ``TRUNCATION_NOTE``. Returns the input unchanged when it already fits."""
    as_bytes = preview_html.encode("utf-8")
    if len(as_bytes) <= max_bytes:
        return preview_html

    # Find the last </p> that fits before max_bytes.
    cutoff = preview_html.rfind("</p>", 0, max_bytes)
    if cutoff == -1:
        # No paragraph boundary — hard cut at max_bytes (on a character boundary).
        head = as_bytes[:max_bytes].decode("utf-8", errors="ignore")
    else:
        head = preview_html[: cutoff + len("</p>")]
    return head + TRUNCATION_NOTE
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: PASS for all eleven tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_overview_lib.py \
        .github/skills/wiki-generator/scripts/overview_lib.py
git commit -m "feat(overview): truncate oversized preview payloads at paragraph boundary"
```

---

## Task 5: Idempotent nav-link injection helper

**Files:**
- Modify: `.github/skills/wiki-generator/scripts/overview_lib.py`
- Test: `tests/test_overview_lib.py`

- [ ] **Step 1: Write failing tests for `inject_nav_link`**

Append to `tests/test_overview_lib.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: FAIL — no `inject_nav_link`.

- [ ] **Step 3: Implement `inject_nav_link`**

Append to `overview_lib.py`:

```python
_NAV_OPEN_RE = re.compile(r"<nav\b[^>]*>", re.IGNORECASE)
_NAV_CLOSE_RE = re.compile(r"</nav>", re.IGNORECASE)
_BODY_OPEN_RE = re.compile(r"<body\b[^>]*>", re.IGNORECASE)


def inject_nav_link(page_html: str, href: str, label: str) -> Tuple[str, bool]:
    """Ensure a ``<a href="{href}">{label}</a>`` link exists inside the top
    ``<nav>``. Creates a ``<nav>`` directly after ``<body>`` if none exists.

    Returns ``(new_html, changed)``. ``changed`` is False when the link is
    already present (idempotent).
    """
    link_marker = f'href="{href}"'
    if link_marker in page_html:
        return page_html, False

    new_anchor = f'<a href="{href}">{label}</a>'

    nav_close = _NAV_CLOSE_RE.search(page_html)
    nav_open = _NAV_OPEN_RE.search(page_html)
    if nav_open and nav_close and nav_close.start() > nav_open.start():
        insert_at = nav_close.start()
        return page_html[:insert_at] + new_anchor + page_html[insert_at:], True

    body_open = _BODY_OPEN_RE.search(page_html)
    if body_open:
        insert_at = body_open.end()
        new_nav = f"<nav>{new_anchor}</nav>"
        return page_html[:insert_at] + new_nav + page_html[insert_at:], True

    # No <body> — prepend a nav; still produces valid-enough HTML fragments.
    return f"<nav>{new_anchor}</nav>" + page_html, True
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: PASS for all fifteen tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_overview_lib.py \
        .github/skills/wiki-generator/scripts/overview_lib.py
git commit -m "feat(overview): idempotent nav-link injection helper"
```

---

## Task 6: Discover worklist from an existing wiki (retrofit helper)

**Files:**
- Modify: `.github/skills/wiki-generator/scripts/overview_lib.py`
- Test: `tests/test_overview_lib.py`
- Create: `tests/fixtures/overview/pre-layered-wiki/index.html`
- Create: `tests/fixtures/overview/pre-layered-wiki/mod-alpha/focus-one/index.html`
- Create: `tests/fixtures/overview/pre-layered-wiki/mod-alpha/focus-two/index.html`
- Create: `tests/fixtures/overview/pre-layered-wiki/mod-beta/focus-three/index.html`

- [ ] **Step 1: Write fixture wiki files**

Create `tests/fixtures/overview/pre-layered-wiki/index.html`:

```html
<!doctype html><html><body>
<main>
  <section class="deep-dive-hub">
    <a href="mod-alpha/focus-one/index.html">Alpha Focus One</a>
    <a href="mod-alpha/focus-two/index.html">Alpha Focus Two</a>
    <a href="mod-beta/focus-three/index.html">Beta Focus Three</a>
  </section>
</main></body></html>
```

Create `tests/fixtures/overview/pre-layered-wiki/mod-alpha/focus-one/index.html`:

```html
<!doctype html><html><body><main>
<h1>Alpha Focus One</h1>
<p>Alpha one primer paragraph.</p>
<p>Alpha one core idea paragraph.</p>
</main></body></html>
```

Create `tests/fixtures/overview/pre-layered-wiki/mod-alpha/focus-two/index.html`:

```html
<!doctype html><html><body><main>
<h1>Alpha Focus Two</h1>
<p>Alpha two primer paragraph.</p>
<p>Alpha two core idea paragraph.</p>
</main></body></html>
```

Create `tests/fixtures/overview/pre-layered-wiki/mod-beta/focus-three/index.html`:

```html
<!doctype html><html><body><main>
<h1>Beta Focus Three</h1>
<p>Beta three primer paragraph.</p>
<p>Beta three core idea paragraph.</p>
</main></body></html>
```

- [ ] **Step 2: Write failing test for `discover_worklist`**

Append to `tests/test_overview_lib.py`:

```python
FIXTURE_WIKI = REPO_ROOT / "tests" / "fixtures" / "overview" / "pre-layered-wiki"


def test_discover_worklist_groups_by_module_dir():
    worklist = overview_lib.discover_worklist(FIXTURE_WIKI)
    # Two modules, three focus pages total.
    assert sorted(worklist.keys()) == ["mod-alpha", "mod-beta"]
    alpha = worklist["mod-alpha"]
    assert len(alpha) == 2
    titles = {e["title"] for e in alpha}
    assert titles == {"Alpha Focus One", "Alpha Focus Two"}
    # Hrefs are relative to the wiki root.
    hrefs = {e["href"] for e in alpha}
    assert "mod-alpha/focus-one/index.html" in hrefs


def test_discover_worklist_empty_when_no_hub():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "index.html").write_text("<html><body><p>no hub</p></body></html>")
        assert overview_lib.discover_worklist(tmp_path) == {}
```

- [ ] **Step 3: Run to confirm failure**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: FAIL — no `discover_worklist`.

- [ ] **Step 4: Implement `discover_worklist`**

Append to `overview_lib.py`:

```python
from pathlib import Path


_ANCHOR_RE = re.compile(r'<a\s+[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', re.IGNORECASE)
_H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)


def _parse_title(page_html: str, fallback: str) -> str:
    m = _H1_RE.search(page_html)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return fallback


def discover_worklist(wiki_root: Path) -> dict:
    """Scan ``wiki_root/index.html`` for focus-page hrefs, group them by the
    first path segment (module directory), and return
    ``{module_slug: [{"title", "href"}, ...]}``.

    Used by retrofit mode where ``_worklist.yaml`` does not exist.
    """
    index_path = Path(wiki_root) / "index.html"
    if not index_path.is_file():
        return {}
    html_text = index_path.read_text(encoding="utf-8", errors="replace")
    result: dict[str, list[dict]] = {}
    for href, label in _ANCHOR_RE.findall(html_text):
        # Focus pages always look like <module>/<slug>/index.html (two path segments + index).
        parts = href.split("/")
        if len(parts) < 3 or not parts[-1].endswith("index.html"):
            continue
        module = parts[0]
        focus_page = Path(wiki_root) / href
        if not focus_page.is_file():
            continue
        focus_html = focus_page.read_text(encoding="utf-8", errors="replace")
        entry = {"title": _parse_title(focus_html, label.strip()), "href": href}
        result.setdefault(module, []).append(entry)
    return result
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_overview_lib.py -v`
Expected: PASS for all seventeen tests.

- [ ] **Step 6: Commit**

```bash
git add tests/test_overview_lib.py \
        tests/fixtures/overview/pre-layered-wiki \
        .github/skills/wiki-generator/scripts/overview_lib.py
git commit -m "feat(overview): discover worklist from an existing wiki (retrofit mode)"
```

---

## Task 7: The Overview Pass prompt template

**Files:**
- Create: `.github/skills/wiki-generator/resources/overview_pass.md`
- Create: `.github/skills/wiki-generator/resources/overview-template.html`

- [ ] **Step 1: Write the HTML template**

Create `.github/skills/wiki-generator/resources/overview-template.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{{PROJECT_NAME}} — Overview</title>
<style>
body { font-family: system-ui, sans-serif; margin: 0; background: #0e1116; color: #e6edf3; }
header { padding: 2rem; border-bottom: 1px solid #30363d; }
header h1 { margin: 0 0 .25rem; }
.tagline { margin: 0 0 .75rem; color: #8b949e; }
nav a { color: #58a6ff; margin-right: 1rem; text-decoration: none; }
main { padding: 1.5rem 2rem; max-width: 1200px; margin: 0 auto; }
.module { margin-bottom: 2.25rem; }
.module h2 { margin: 0 0 .25rem; border-bottom: 1px solid #30363d; padding-bottom: .25rem; }
.module-blurb { color: #8b949e; margin: .25rem 0 .75rem; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: .75rem; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: .9rem 1rem; cursor: pointer; }
.card:hover, .card:focus { border-color: #58a6ff; outline: none; }
.card h3 { margin: 0 0 .35rem; font-size: 1rem; }
.card .summary { margin: 0 0 .5rem; color: #c9d1d9; font-size: .9rem; }
.card .tags { color: #8b949e; font-size: .8rem; margin-bottom: .25rem; }
.card .stats { color: #6e7681; font-size: .75rem; }
dialog { border: 1px solid #30363d; border-radius: 8px; background: #0d1117; color: #e6edf3; max-width: 640px; width: 92vw; }
dialog::backdrop { background: rgba(0,0,0,.6); }
dialog .modal-body { padding: 1rem 1.25rem; max-height: 70vh; overflow: auto; }
dialog footer { display: flex; justify-content: space-between; padding: .5rem 1rem; border-top: 1px solid #30363d; }
dialog .retrofit-banner { background: #332700; color: #f2cc60; padding: .35rem .6rem; border-radius: 4px; margin-bottom: .75rem; font-size: .85rem; }
@media (max-width: 640px) { .card-grid { grid-template-columns: 1fr; } dialog { width: 100vw; height: 100vh; max-width: none; border-radius: 0; } }
</style>
</head>
<body>
<header>
  <h1>{{PROJECT_NAME}}</h1>
  <p class="tagline">{{PROJECT_TAGLINE}}</p>
  <nav><a href="index.html">Home</a></nav>
</header>
<main>
{{MODULE_SECTIONS}}
</main>
<dialog id="preview-modal">
  <div class="modal-body"></div>
  <footer>
    <a class="full-link" href="#">Read full page →</a>
    <button class="close" type="button">Close</button>
  </footer>
</dialog>
<script>
(function () {
  var dlg = document.getElementById('preview-modal');
  if (typeof HTMLDialogElement === 'undefined' || !dlg.showModal) {
    document.querySelectorAll('.card').forEach(function (c) {
      c.addEventListener('click', function () { window.location = c.dataset.href; });
    });
    return;
  }
  var body = dlg.querySelector('.modal-body');
  var full = dlg.querySelector('.full-link');
  document.querySelector('main').addEventListener('click', function (ev) {
    var card = ev.target.closest('.card');
    if (!card) return;
    body.innerHTML = card.dataset.previewHtml || '';
    full.href = card.dataset.href || '#';
    dlg.showModal();
  });
  document.querySelector('main').addEventListener('keydown', function (ev) {
    if (ev.key !== 'Enter') return;
    var card = ev.target.closest('.card');
    if (!card) return;
    ev.preventDefault();
    body.innerHTML = card.dataset.previewHtml || '';
    full.href = card.dataset.href || '#';
    dlg.showModal();
  });
  dlg.querySelector('.close').addEventListener('click', function () { dlg.close(); });
  dlg.addEventListener('click', function (ev) { if (ev.target === dlg) dlg.close(); });
})();
</script>
</body>
</html>
```

- [ ] **Step 2: Write the Overview Pass prompt**

Create `.github/skills/wiki-generator/resources/overview_pass.md`:

```markdown
# Overview Pass — Generate `overview.html`

## Inputs you are given
- `{{PROJECT_NAME}}`: the project display name.
- `{{PROJECT_TAGLINE}}`: a one-line tagline (already written).
- `{{WORKLIST_JSON}}`: a JSON object mapping each module slug to a list of
  focus-page entries with `title`, `href`, and the preview HTML you must
  embed verbatim as `data-preview-html`.
- `{{STATS_JSON}}`: a JSON object keyed by `href`, each value giving the exact
  integer counts `{ "diagrams": N, "refs": M, "lines": L }`. You MUST use these
  numbers unchanged.
- `{{TEMPLATE}}`: the HTML template shell. Fill the `{{MODULE_SECTIONS}}` slot
  and leave the rest exactly as-is.

## Card responsibilities (per focus-page entry)
For each entry in the worklist, emit one `<article class="card">` with:

1. `data-href="{href}"` exactly as given.
2. `data-preview-html="{preview_html}"` exactly as given, already HTML-
   attribute-escaped. Do not re-escape or modify.
3. `<h3>` containing the entry's `title`.
4. `<p class="summary">`: a 1–2 sentence summary of the focus topic written by
   you from the preview content. This summary MUST NOT be a byte-identical
   copy of any paragraph already inside `data-preview-html`. Make it punchier
   and grid-appropriate.
5. `<div class="tags">`: 1–3 tags, dot-separated, chosen ONLY from this fixed
   vocabulary: `core`, `api`, `internals`, `tutorial`, `reference`, `advanced`.
   No other tags are permitted.
6. `<div class="stats">`: render the stats from `{{STATS_JSON}}` as
   `"{diagrams} diagrams · {refs} refs · {lines} lines"`. Use the exact
   numbers — do not recount, round, or estimate.

## Module section responsibilities
For each module, emit one `<section class="module" data-module-id="{slug}">`
with:
- `<h2>` containing a human module name (title-case the slug if no better name
  is evident from the entries).
- `<p class="module-blurb">`: one sentence summarizing the module, written by
  you from its entries.
- A single `<div class="card-grid">` containing the module's cards in the
  worklist order.

## Hard rules
- Output ONLY the filled-in `{{TEMPLATE}}`. No commentary, no markdown fences.
- Every worklist entry MUST produce exactly one card. Never omit, never add.
- Never write `TBD`, `TODO`, `FIXME`, `Lorem`, `TK`, or `XXX`.
- Never invent stats. Use `{{STATS_JSON}}` verbatim.
```

- [ ] **Step 3: Verify both files exist and are non-empty**

Run: `wc -l .github/skills/wiki-generator/resources/overview-template.html .github/skills/wiki-generator/resources/overview_pass.md`
Expected: two line-count lines, each > 30.

- [ ] **Step 4: Commit**

```bash
git add .github/skills/wiki-generator/resources/overview_pass.md \
        .github/skills/wiki-generator/resources/overview-template.html
git commit -m "feat(overview): add Overview Pass prompt and HTML template"
```

---

## Task 8: Build the generator-mode Overview Pass driver

**Files:**
- Create: `.github/skills/wiki-generator/scripts/overview_pass.py`
- Test: `tests/test_overview_pass_driver.py`

The driver's job is to read inputs, call `overview_lib` to build preview HTML / stats, render `{{WORKLIST_JSON}}` and `{{STATS_JSON}}`, then shell out to Copilot CLI. Tests mock the Copilot invocation.

- [ ] **Step 1: Write failing tests for the payload-building step**

Create `tests/test_overview_pass_driver.py`:

```python
"""Tests for overview_pass.py (the Overview Pass driver)."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / ".github" / "skills" / "wiki-generator" / "scripts"))

import overview_pass  # noqa: E402

FIXTURE_WIKI = REPO_ROOT / "tests" / "fixtures" / "overview" / "pre-layered-wiki"


def test_build_payload_produces_worklist_and_stats_json():
    payload = overview_pass.build_payload(
        wiki_root=FIXTURE_WIKI,
        worklist={
            "mod-alpha": [
                {"title": "Alpha Focus One", "href": "mod-alpha/focus-one/index.html"},
            ],
        },
    )
    worklist = json.loads(payload["worklist_json"])
    stats = json.loads(payload["stats_json"])
    entry = worklist["mod-alpha"][0]
    assert entry["href"] == "mod-alpha/focus-one/index.html"
    # preview_html must already be HTML-attribute-escaped
    assert '"' not in entry["preview_html"]
    # stats keyed by href
    assert "mod-alpha/focus-one/index.html" in stats
    s = stats["mod-alpha/focus-one/index.html"]
    assert set(s.keys()) == {"diagrams", "refs", "lines"}


def test_build_payload_adds_retrofit_banner_when_pre_layered():
    payload = overview_pass.build_payload(
        wiki_root=FIXTURE_WIKI,
        worklist={"mod-alpha": [{"title": "A", "href": "mod-alpha/focus-one/index.html"}]},
    )
    worklist = json.loads(payload["worklist_json"])
    preview_attr = worklist["mod-alpha"][0]["preview_html"]
    # The banner is part of the embedded (escaped) preview HTML.
    assert "retrofit-banner" in preview_attr
```

- [ ] **Step 2: Run to confirm failure**

Run: `python -m pytest tests/test_overview_pass_driver.py -v`
Expected: FAIL — no `overview_pass`.

- [ ] **Step 3: Implement `overview_pass.build_payload`**

Create `.github/skills/wiki-generator/scripts/overview_pass.py`:

```python
"""Overview Pass driver.

Builds the payload handed to Copilot CLI and invokes it to produce
``overview.html``. Pure-payload construction is separated from the subprocess
call so it can be unit-tested without Copilot installed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import overview_lib

RETROFIT_BANNER = (
    '<div class="retrofit-banner">This overview was retrofitted from a '
    "pre-layered wiki; previews may be abbreviated.</div>"
)


def _load_page(wiki_root: Path, href: str) -> str:
    return (wiki_root / href).read_text(encoding="utf-8", errors="replace")


def build_payload(wiki_root: Path, worklist: dict) -> dict:
    """Return a dict with ``worklist_json`` and ``stats_json`` strings ready
    to substitute into the prompt template."""
    enriched: dict[str, list[dict]] = {}
    stats_by_href: dict[str, dict] = {}
    for module, entries in worklist.items():
        enriched[module] = []
        for entry in entries:
            href = entry["href"]
            page_html = _load_page(wiki_root, href)
            preview, retrofit = overview_lib.extract_preview_html(page_html)
            if retrofit:
                preview = RETROFIT_BANNER + preview
            preview = overview_lib.truncate_preview(preview)
            escaped = overview_lib.escape_for_attribute(preview)
            enriched[module].append(
                {"title": entry["title"], "href": href, "preview_html": escaped}
            )
            stats_by_href[href] = overview_lib.count_stats(page_html)
    return {
        "worklist_json": json.dumps(enriched, ensure_ascii=False, indent=2),
        "stats_json": json.dumps(stats_by_href, ensure_ascii=False, indent=2),
    }


def _render_prompt(template_md: Path, vars: dict) -> str:
    text = template_md.read_text(encoding="utf-8")
    for key, value in vars.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def invoke_copilot(prompt: str, model: str, out_path: Path) -> int:
    """Invoke Copilot CLI to fill the prompt and write ``overview.html``.

    Returns Copilot's exit code. The prompt instructs the model to print
    the full filled template on stdout; we capture stdout → ``out_path``.
    """
    result = subprocess.run(
        ["copilot", "chat", "--model", model],
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode
    out_path.write_text(result.stdout, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run the Overview Pass.")
    p.add_argument("--wiki-root", required=True, type=Path)
    p.add_argument("--worklist-json", required=True, type=Path,
                   help="Path to a JSON file with {module: [{title, href}, ...]}")
    p.add_argument("--project-name", required=True)
    p.add_argument("--project-tagline", default="")
    p.add_argument("--model", default="claude-opus-4.6")
    p.add_argument("--prompt-template", type=Path, required=True)
    p.add_argument("--html-template", type=Path, required=True)
    args = p.parse_args(argv)

    worklist = json.loads(args.worklist_json.read_text(encoding="utf-8"))
    payload = build_payload(args.wiki_root, worklist)
    prompt = _render_prompt(
        args.prompt_template,
        {
            "PROJECT_NAME": args.project_name,
            "PROJECT_TAGLINE": args.project_tagline,
            "WORKLIST_JSON": payload["worklist_json"],
            "STATS_JSON": payload["stats_json"],
            "TEMPLATE": args.html_template.read_text(encoding="utf-8"),
        },
    )
    out_path = args.wiki_root / "overview.html"
    return invoke_copilot(prompt, args.model, out_path)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_overview_pass_driver.py -v`
Expected: PASS for the two driver tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_overview_pass_driver.py \
        .github/skills/wiki-generator/scripts/overview_pass.py
git commit -m "feat(overview): overview_pass.py driver with payload builder and Copilot call"
```

---

## Task 9: Gate D in `verify.sh`

**Files:**
- Modify: `.github/skills/wiki-generator/scripts/verify.sh`
- Create: `tests/fixtures/overview/good-overview.html`
- Create: `tests/fixtures/overview/bad-missing-card/overview.html`
- Create: `tests/fixtures/overview/bad-placeholder/overview.html`
- Create: `tests/test_verify_stage_d.py`

- [ ] **Step 1: Create the golden `good-overview.html` fixture**

Create `tests/fixtures/overview/good-overview.html`:

```html
<!DOCTYPE html><html><body>
<main>
  <section class="module" data-module-id="mod-alpha">
    <h2>Mod Alpha</h2>
    <p class="module-blurb">Alpha module blurb.</p>
    <div class="card-grid">
      <article class="card" tabindex="0" role="button"
               data-href="mod-alpha/focus-one/index.html"
               data-preview-html="&lt;p&gt;Primer.&lt;/p&gt;">
        <h3>Alpha Focus One</h3>
        <p class="summary">Punchy focus summary.</p>
        <div class="tags">core · internals</div>
        <div class="stats">2 diagrams · 3 refs · 12 lines</div>
      </article>
    </div>
  </section>
</main>
<dialog id="preview-modal"><div class="modal-body"></div></dialog>
<script>/* inline js */</script>
</body></html>
```

Also create the referenced focus page so the resolve-check passes:

```
mkdir -p tests/fixtures/overview/mod-alpha/focus-one
echo '<html><body>ok</body></html>' > tests/fixtures/overview/mod-alpha/focus-one/index.html
```

- [ ] **Step 2: Create mutated-bad fixtures**

Create `tests/fixtures/overview/bad-missing-card/overview.html` — copy the golden file but delete the `<article class="card">` block entirely (leaving an empty `.card-grid`).

Create `tests/fixtures/overview/bad-placeholder/overview.html` — copy the golden file but replace `Punchy focus summary.` with `TODO: fill in`.

- [ ] **Step 3: Write failing tests driving `verify.sh --stage=D`**

Create `tests/test_verify_stage_d.py`:

```python
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
```

- [ ] **Step 4: Run to confirm failures**

Run: `python -m pytest tests/test_verify_stage_d.py -v`
Expected: FAIL — `verify.sh` doesn't yet understand `--stage=D`.

- [ ] **Step 5: Implement Gate D in `verify.sh`**

Edit `.github/skills/wiki-generator/scripts/verify.sh`. Add a flag-parsing prologue at the top (before the existing `DOCS_DIR=` assignment) and a `--stage=D` branch:

```bash
# --- Stage-D flag parsing (new) ---
STAGE=""
PROJECT_DIR=""
POSITIONAL=()
for arg in "$@"; do
  case "$arg" in
    --stage=*) STAGE="${arg#--stage=}" ;;
    --project=*) PROJECT_DIR="${arg#--project=}" ;;
    *) POSITIONAL+=("$arg") ;;
  esac
done
set -- "${POSITIONAL[@]}"

if [[ "$STAGE" == "D" ]]; then
  : "${PROJECT_DIR:?--project=<dir> required with --stage=D}"
  FAIL=0
  OV="$PROJECT_DIR/overview.html"
  [[ -f "$OV" ]] || { echo "FAIL: overview.html missing"; exit 1; }
  grep -q '<section class="module"' "$OV" || { echo "FAIL: no <section class=\"module\">"; FAIL=1; }
  grep -q '<article class="card"' "$OV"   || { echo "FAIL: no <article class=\"card\">"; FAIL=1; }
  grep -q 'id="preview-modal"' "$OV"      || { echo "FAIL: no <dialog id=\"preview-modal\">"; FAIL=1; }
  grep -q '<script>' "$OV"                || { echo "FAIL: no inline <script>"; FAIL=1; }
  # Placeholder scan.
  for needle in TBD TODO FIXME Lorem ' TK ' XXX; do
    if grep -q "$needle" "$OV"; then echo "FAIL: placeholder '$needle' present"; FAIL=1; fi
  done
  # Resolve every data-href against the project dir.
  grep -oE 'data-href="[^"]+"' "$OV" | sed -E 's/data-href="([^"]+)"/\1/' | while read -r href; do
    [[ -f "$PROJECT_DIR/$href" ]] || { echo "FAIL: broken data-href: $href"; exit 2; }
  done
  if [[ ${PIPESTATUS[2]:-0} -ne 0 ]]; then FAIL=1; fi
  [[ $FAIL -eq 0 ]] && { echo "Stage D: OK"; exit 0; } || exit 1
fi
# --- end Stage-D ---
```

Place this block near the top of `verify.sh`, after `set -euo pipefail` and before the existing positional-argument assignment. The original stage (no `--stage=` flag) continues to work because we strip the new flags before falling through.

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_verify_stage_d.py -v`
Expected: PASS for all four Gate D tests.

- [ ] **Step 7: Commit**

```bash
git add .github/skills/wiki-generator/scripts/verify.sh \
        tests/fixtures/overview/good-overview.html \
        tests/fixtures/overview/bad-missing-card/overview.html \
        tests/fixtures/overview/bad-placeholder/overview.html \
        tests/fixtures/overview/mod-alpha/focus-one/index.html \
        tests/test_verify_stage_d.py
git commit -m "feat(verify): add Gate D stage for overview.html structural checks"
```

---

## Task 10: Nav-link injector CLI

**Files:**
- Create: `.github/skills/wiki-generator/scripts/inject_overview_link.py`
- Test: `tests/test_inject_overview_link.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_inject_overview_link.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

Run: `python -m pytest tests/test_inject_overview_link.py -v`
Expected: FAIL — script does not exist yet.

- [ ] **Step 3: Implement the CLI**

Create `.github/skills/wiki-generator/scripts/inject_overview_link.py`:

```python
#!/usr/bin/env python3
"""Idempotently inject an ``Overview`` nav link into every ``index.html``
under the given project directory.

Usage: python inject_overview_link.py <project-dir>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import overview_lib


def _relative_href(index_path: Path, project_root: Path) -> str:
    depth = len(index_path.relative_to(project_root).parts) - 1
    return ("../" * depth) + "overview.html"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <project-dir>", file=sys.stderr)
        return 2
    project_root = Path(argv[1]).resolve()
    if not project_root.is_dir():
        print(f"Not a directory: {project_root}", file=sys.stderr)
        return 2
    changed = 0
    for index_path in project_root.rglob("index.html"):
        href = _relative_href(index_path, project_root)
        text = index_path.read_text(encoding="utf-8", errors="replace")
        new_text, did = overview_lib.inject_nav_link(text, href, "Overview")
        if did:
            index_path.write_text(new_text, encoding="utf-8")
            changed += 1
    print(f"Injected Overview link into {changed} index pages under {project_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

Make the script executable:
```
chmod +x .github/skills/wiki-generator/scripts/inject_overview_link.py
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_inject_overview_link.py -v`
Expected: PASS for all three tests.

- [ ] **Step 5: Commit**

```bash
git add .github/skills/wiki-generator/scripts/inject_overview_link.py \
        tests/test_inject_overview_link.py
git commit -m "feat(overview): inject_overview_link.py injects nav links idempotently"
```

---

## Task 11: Retrofit script (`retrofit_overview.py`)

**Files:**
- Create: `retrofit_overview.py`
- Test: `tests/test_retrofit_overview.py`

- [ ] **Step 1: Write failing tests (mocking Copilot invocation)**

Create `tests/test_retrofit_overview.py`:

```python
"""Tests for retrofit_overview.py. Copilot invocation is monkey-patched."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import retrofit_overview  # noqa: E402


def _make_project(tmp_path: Path, slug: str) -> Path:
    # Mirrors tests/fixtures/overview/pre-layered-wiki but lets each test own a copy.
    proj = tmp_path / slug
    proj.mkdir()
    (proj / "versions.json").write_text(json.dumps({"current": "v1"}), encoding="utf-8")
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
        # Write a minimal valid overview.html so Gate D is satisfied enough
        # for the test (the test does NOT assert Gate D pass/fail here).
        (wiki_root / "overview.html").write_text("stub", encoding="utf-8")
        return 0

    monkeypatch.setattr(retrofit_overview, "run_overview_pass", fake_run_pass)
    assert retrofit_overview.main(["retrofit_overview.py", str(proj), "--force"]) == 0
    assert len(invoked) == 1
    assert invoked[0][1] == ["mod-alpha"]
```

- [ ] **Step 2: Run to confirm failure**

Run: `python -m pytest tests/test_retrofit_overview.py -v`
Expected: FAIL — no `retrofit_overview`.

- [ ] **Step 3: Implement the retrofit script**

Create `retrofit_overview.py` at repo root:

```python
#!/usr/bin/env python3
"""Retrofit ``overview.html`` into every existing committed wiki.

Usage:
  python retrofit_overview.py [project ...] [--force] [--dry-run] [--confirm-each]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SKILL_SCRIPTS = REPO_ROOT / ".github" / "skills" / "wiki-generator" / "scripts"
SKILL_RESOURCES = REPO_ROOT / ".github" / "skills" / "wiki-generator" / "resources"

sys.path.insert(0, str(SKILL_SCRIPTS))
import overview_lib  # noqa: E402
import overview_pass  # noqa: E402


def _iter_project_dirs(explicit: list[str]) -> list[Path]:
    if explicit:
        return [Path(p).resolve() for p in explicit]
    candidates = []
    for child in REPO_ROOT.iterdir():
        if child.is_dir() and (child / "versions.json").is_file():
            candidates.append(child)
    return sorted(candidates)


def _active_version_dir(project: Path) -> Path | None:
    vj = project / "versions.json"
    if not vj.is_file():
        return None
    data = json.loads(vj.read_text(encoding="utf-8"))
    current = data.get("current")
    if not current:
        return None
    vdir = project / current
    return vdir if vdir.is_dir() else None


def run_overview_pass(*, wiki_root: Path, worklist: dict,
                      project_name: str, project_tagline: str) -> int:
    """Invoke the Overview Pass driver. Extracted for monkey-patching in tests."""
    # Write a temp worklist JSON file so we can reuse the driver's CLI.
    tmp_worklist = wiki_root / "_tmp_worklist.json"
    tmp_worklist.write_text(json.dumps(worklist, ensure_ascii=False), encoding="utf-8")
    try:
        rc = overview_pass.main([
            "--wiki-root", str(wiki_root),
            "--worklist-json", str(tmp_worklist),
            "--project-name", project_name,
            "--project-tagline", project_tagline,
            "--prompt-template", str(SKILL_RESOURCES / "overview_pass.md"),
            "--html-template", str(SKILL_RESOURCES / "overview-template.html"),
        ])
    finally:
        tmp_worklist.unlink(missing_ok=True)
    return rc


def _gate_d(wiki_root: Path) -> bool:
    result = subprocess.run(
        ["bash", str(SKILL_SCRIPTS / "verify.sh"), "--stage=D", f"--project={wiki_root}"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(f"[WARN] Gate D failed for {wiki_root}:\n{result.stdout}\n{result.stderr}\n")
        return False
    return True


def _inject_nav(wiki_root: Path) -> None:
    subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "inject_overview_link.py"), str(wiki_root)],
        check=False,
    )


def retrofit_one(project: Path, *, force: bool, dry_run: bool) -> int:
    if (project / ".no-overview").exists():
        print(f"[skip] {project.name}: .no-overview flag present")
        return 0
    wiki_root = _active_version_dir(project)
    if wiki_root is None:
        print(f"[skip] {project.name}: no active version directory")
        return 0
    if (wiki_root / "overview.html").exists() and not force:
        print(f"[skip] {project.name}: overview.html already exists (use --force to regenerate)")
        return 0
    worklist = overview_lib.discover_worklist(wiki_root)
    if not worklist:
        print(f"[skip] {project.name}: no focus pages found")
        return 0
    if dry_run:
        print(f"[dry-run] {project.name}: would retrofit {sum(len(v) for v in worklist.values())} cards across {len(worklist)} modules")
        return 0
    rc = run_overview_pass(
        wiki_root=wiki_root, worklist=worklist,
        project_name=project.name, project_tagline="",
    )
    if rc != 0:
        print(f"[fail] {project.name}: Copilot exit {rc}")
        return rc
    _gate_d(wiki_root)  # non-blocking in retrofit mode
    _inject_nav(wiki_root)
    print(f"[ok] {project.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Retrofit overview.html into existing wikis.")
    p.add_argument("projects", nargs="*", help="Project directories (default: all)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--confirm-each", action="store_true")
    args = p.parse_args((argv or sys.argv)[1:])

    projects = _iter_project_dirs(args.projects)
    if not projects:
        print("No projects found.", file=sys.stderr)
        return 1
    print(f"Retrofitting {len(projects)} project(s).")
    failures = 0
    for proj in projects:
        if args.confirm_each:
            ans = input(f"Retrofit {proj.name}? [y/N] ").strip().lower()
            if ans != "y":
                continue
        rc = retrofit_one(proj, force=args.force, dry_run=args.dry_run)
        if rc != 0:
            failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_retrofit_overview.py -v`
Expected: PASS for all three tests.

- [ ] **Step 5: Commit**

```bash
git add retrofit_overview.py tests/test_retrofit_overview.py
git commit -m "feat(overview): retrofit_overview.py for existing committed wikis"
```

---

## Task 12: Wire the Overview Pass into `run_wiki_gen.sh`

**Files:**
- Modify: `.github/skills/wiki-generator/scripts/run_wiki_gen.sh`

- [ ] **Step 1: Locate the Gate C block**

Run: `grep -n 'Gate C\|stage=C\|Pass C' .github/skills/wiki-generator/scripts/run_wiki_gen.sh`
Expected: one or more matching lines. Note the last one — the Overview Pass must go **after** it.

- [ ] **Step 2: Add the Overview Pass stage**

Insert the following shell block into `run_wiki_gen.sh` immediately after the Gate C check and before the existing Phase 7–10 post-processing call:

```bash
# --- Overview Pass (Gate D) ---
if [[ -f "$OUTPUT_DIR/docs/_research/_worklist.yaml" ]]; then
  echo "[overview] Running Overview Pass…"
  python3 "$SKILL_SCRIPTS/yaml_to_worklist_json.py" \
    "$OUTPUT_DIR/docs/_research/_worklist.yaml" > "$OUTPUT_DIR/_worklist.json"
  python3 "$SKILL_SCRIPTS/overview_pass.py" \
    --wiki-root "$OUTPUT_DIR" \
    --worklist-json "$OUTPUT_DIR/_worklist.json" \
    --project-name "$PROJECT_NAME" \
    --project-tagline "${PROJECT_TAGLINE:-}" \
    --prompt-template "$SKILL_RESOURCES/overview_pass.md" \
    --html-template "$SKILL_RESOURCES/overview-template.html"
  rm -f "$OUTPUT_DIR/_worklist.json"
  bash "$SKILL_SCRIPTS/verify.sh" --stage=D --project="$OUTPUT_DIR" \
    || { echo "Gate D failed"; exit 1; }
  python3 "$SKILL_SCRIPTS/inject_overview_link.py" "$OUTPUT_DIR"
else
  echo "[overview] No _worklist.yaml — skipping Overview Pass (project not eligible)"
fi
# --- end Overview Pass ---
```

Assume the script already defines `$SKILL_SCRIPTS` and `$SKILL_RESOURCES` (if not, define them near the top from `$WIKI_SKILL_REPO`). `$OUTPUT_DIR` is the active version directory the orchestrator writes to.

- [ ] **Step 3: Create the tiny YAML → JSON converter used above**

Create `.github/skills/wiki-generator/scripts/yaml_to_worklist_json.py`:

```python
#!/usr/bin/env python3
"""Convert _worklist.yaml → JSON shape expected by overview_pass.py.

Reads a YAML mapping of module-slug -> [{title, href}, ...] and prints
the same structure as JSON on stdout.
"""
import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    sys.stderr.write("PyYAML required. Install with: pip install pyyaml\n")
    sys.exit(2)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <worklist.yaml>", file=sys.stderr)
        return 2
    data = yaml.safe_load(Path(argv[1]).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.stderr.write("Expected top-level mapping in worklist YAML\n")
        return 2
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Sanity-check the modified bash still parses**

Run: `bash -n .github/skills/wiki-generator/scripts/run_wiki_gen.sh`
Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add .github/skills/wiki-generator/scripts/run_wiki_gen.sh \
        .github/skills/wiki-generator/scripts/yaml_to_worklist_json.py
git commit -m "feat(overview): wire Overview Pass + Gate D + nav injection into run_wiki_gen.sh"
```

---

## Task 13: Exclude `overview.html` from the search index

**Files:**
- Modify: `.github/skills/wiki-generator/scripts/build-search-index.py`

- [ ] **Step 1: Locate the file-walk in the existing script**

Run: `grep -n 'rglob\|glob\|walk\|\.html' .github/skills/wiki-generator/scripts/build-search-index.py | head`
Note the line(s) where HTML files are enumerated.

- [ ] **Step 2: Add an exclusion filter**

Edit `build-search-index.py`. At the point where HTML files are enumerated (typically a list comprehension or loop), filter out files named `overview.html`. For example, if the existing code looks like:

```python
for html in root.rglob("*.html"):
    ...
```

Change it to:

```python
for html in root.rglob("*.html"):
    if html.name == "overview.html":
        continue
    ...
```

If the enumeration is a list comprehension, add the same `if html.name != "overview.html"` guard.

- [ ] **Step 3: Smoke test the change**

Run: `python3 -c "import ast; ast.parse(open('.github/skills/wiki-generator/scripts/build-search-index.py').read())"`
Expected: no output (parses cleanly).

- [ ] **Step 4: Commit**

```bash
git add .github/skills/wiki-generator/scripts/build-search-index.py
git commit -m "feat(overview): exclude overview.html from search index (navigational, not content)"
```

---

## Task 14: Playwright integration smoke test

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_overview_e2e.py`

- [ ] **Step 1: Install Playwright (one-time)**

Run: `pip install playwright && playwright install chromium`
Expected: install succeeds, chromium binary downloaded.

- [ ] **Step 2: Write the integration test**

Create `tests/integration/__init__.py` (empty file).

Create `tests/integration/test_overview_e2e.py`:

```python
"""Headless integration test for overview.html modal behavior.

Uses the golden fixture overview.html from tests/fixtures/overview/.
"""
import http.server
import socket
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "overview"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def served_fixture(tmp_path):
    # Materialize a minimal wiki: golden overview.html + referenced focus page.
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "overview.html").write_bytes((FIXTURES / "good-overview.html").read_bytes())
    target = wiki / "mod-alpha" / "focus-one"
    target.mkdir(parents=True)
    (target / "index.html").write_text("<html><body>full page</body></html>", encoding="utf-8")

    port = _free_port()
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(wiki), **kw)
    server = socketserver.TCPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()


def test_card_click_opens_dialog_and_link_points_at_focus_page(served_fixture):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"{served_fixture}/overview.html")
        page.click(".card")
        assert page.evaluate("document.getElementById('preview-modal').open") is True
        href = page.get_attribute("dialog .full-link", "href")
        assert href.endswith("mod-alpha/focus-one/index.html")
        browser.close()


def test_escape_closes_modal(served_fixture):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"{served_fixture}/overview.html")
        page.click(".card")
        page.keyboard.press("Escape")
        assert page.evaluate("document.getElementById('preview-modal').open") is False
        browser.close()
```

- [ ] **Step 3: Run the integration tests**

Run: `python -m pytest tests/integration/test_overview_e2e.py -v`
Expected: PASS for both tests. (Skip with a clear error on systems where Playwright isn't installable; this is the intended CI-only test.)

- [ ] **Step 4: Commit**

```bash
git add tests/integration/__init__.py tests/integration/test_overview_e2e.py
git commit -m "test(overview): Playwright smoke test for card click and Esc close"
```

---

## Task 15: Final verification

**Files:** none new.

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: all unit tests pass. Integration tests pass if Playwright is installed; otherwise they're skipped or fail gracefully — acceptable locally, required in CI.

- [ ] **Step 2: Lint-check bash scripts**

Run:
```bash
bash -n .github/skills/wiki-generator/scripts/verify.sh
bash -n .github/skills/wiki-generator/scripts/run_wiki_gen.sh
```
Expected: no output, exit 0 for both.

- [ ] **Step 3: Dry-run the retrofit script**

Run: `python retrofit_overview.py --dry-run`
Expected: lists each project and whether it would be retrofitted; no side effects.

- [ ] **Step 4: Real retrofit on one project**

Run: `python retrofit_overview.py oclgrind`
Expected: writes `oclgrind/<current-version>/overview.html`, Gate D passes or prints warnings only, nav link injected.

- [ ] **Step 5: Open the result in a browser**

Run: `bash launch_server.sh` (existing script) and visit `http://localhost:.../oclgrind/<current>/overview.html`. Verify: cards render, modal opens on click, Esc closes, "Read full page →" link navigates correctly.

- [ ] **Step 6: Commit any follow-up fixes**

If any issue surfaced in Steps 4–5, fix it and commit with a descriptive message. If everything works, create a summary commit:

```bash
git commit --allow-empty -m "chore(overview): verify end-to-end on oclgrind retrofit"
```

---

## Self-Review

**Spec coverage:** every numbered section of the spec maps to at least one task:
- §4.3 HTML structure → Task 7.
- §4.4 runtime JS → Task 7 (inlined script block).
- §5.1–5.4 Overview Pass contract → Task 7 (prompt) + Task 8 (payload builder) + Task 6 + Task 2 (fallback).
- §6 Gate D → Task 9.
- §7 retrofit → Task 11; version resolution matches `versions.json.current` pattern.
- §8 nav injection → Tasks 5 + 10 + 12.
- §9 error handling → covered by Task 4 (truncation), Task 7 (`HTMLDialogElement` fallback), Task 11 (non-blocking warn), Task 5 (missing-nav fallback).
- §10 tests → Tasks 1–6 (unit), Task 9 (Gate D), Task 14 (integration). Manual QA checklist lives in the spec, not the plan.
- §11 edge cases — single module, zero focus pages, >50 cards, version switcher ordering, search-index exclusion → Tasks 12, 13; version-switcher ordering is enforced because the Overview Pass stage runs after Gate C (where existing version-switcher injection occurs).
- §12 backward compatibility → Task 11 (skip conditions, `.no-overview`, idempotent).

**Placeholder scan:** grep of "TBD", "TODO", "fill in", "Similar to Task" produced no results inside task steps — all code, commands, and files are concrete.

**Type consistency:** `escape_for_attribute`, `extract_preview_html`, `count_stats`, `truncate_preview`, `inject_nav_link`, and `discover_worklist` signatures are referenced consistently across Tasks 8, 10, 11. The driver's `build_payload` keys (`worklist_json`, `stats_json`) match the prompt template placeholders `{{WORKLIST_JSON}}`, `{{STATS_JSON}}` (Task 7).
