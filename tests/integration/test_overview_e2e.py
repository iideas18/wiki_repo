"""Headless integration test for overview.html modal behavior.

Renders the real overview-template.html with a minimal module/card
substituted into {{MODULE_SECTIONS}} so the inlined modal JS is
exercised end-to-end via a local HTTP server.
"""
import http.server
import socket
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE = (
    REPO_ROOT
    / ".github"
    / "skills"
    / "wiki-generator"
    / "resources"
    / "overview-template.html"
)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


CARD_HTML = """
<section class="module" data-module-id="mod-alpha">
  <h2>Mod Alpha</h2>
  <p class="module-blurb">Alpha module blurb.</p>
  <div class="card-grid">
    <article class="card" tabindex="0" role="button"
             data-href="mod-alpha/focus-one/index.html"
             data-preview-html="&lt;p&gt;Primer paragraph.&lt;/p&gt;">
      <h3>Alpha Focus One</h3>
      <p class="summary">Punchy focus summary.</p>
      <div class="tags">core</div>
      <div class="stats">2 diagrams &middot; 3 refs &middot; 12 lines</div>
    </article>
  </div>
</section>
"""


@pytest.fixture()
def served_fixture(tmp_path):
    template = TEMPLATE.read_text(encoding="utf-8")
    rendered = (
        template
        .replace("{{PROJECT_NAME}}", "Test Project")
        .replace("{{PROJECT_TAGLINE}}", "Tagline")
        .replace("{{MODULE_SECTIONS}}", CARD_HTML)
    )
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "overview.html").write_text(rendered, encoding="utf-8")
    target = wiki / "mod-alpha" / "focus-one"
    target.mkdir(parents=True)
    (target / "index.html").write_text(
        "<html><body>full page</body></html>", encoding="utf-8"
    )

    port = _free_port()
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(
        *a, directory=str(wiki), **kw
    )
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
        href = page.get_attribute("#preview-modal .full-link", "href")
        assert href is not None and href.endswith("mod-alpha/focus-one/index.html")
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
