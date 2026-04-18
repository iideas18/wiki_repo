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
