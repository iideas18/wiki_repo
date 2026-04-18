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
