#!/usr/bin/env python3
"""Auto-detect wiki projects and append them to the hub index.html.

Scans directories for wiki projects (index.html with <meta name="wiki-source">
+ search-index.json), extracts metadata, and appends new cards to index.html.

Usage:
    python3 update_index.py                         # auto-detect & append ALL new projects
    python3 update_index.py claude-code minimind   # append only these specific dirs
    python3 update_index.py --list                 # list detected projects (dry run)
"""

import argparse
import glob
import html as html_mod
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from internal_wiki_paths import (
    HUB_INDEX,
    REPO_ROOT,
    get_hub_index,
    iter_project_dirs,
    relative_href,
    resolve_project_dir,
)

CARD_GRID_RE = re.compile(r'(<div class="card-grid">\n)(.*?)(</div>\n\n<h2 id="about">)', re.DOTALL)
CARD_RE = re.compile(r'<a class="card" href="[^"]+">.*?</a>', re.DOTALL)

# ── Icons: map keywords in title to emoji HTML entities ──────────────
ICON_MAP = [
    (r"hedge|fund|invest|stock|trading",  "&#128200;"),  # 📈
    (r"gpu|gpgpu|sim|cuda",               "&#128421;"),  # 🖥
    (r"debug|grind|analysis",             "&#128270;"),  # 🔎
    (r"claude|copilot|agent|code.*tool",  "&#129302;"),  # 🤖
    (r"mind|llm|train|model|language",    "&#129504;"),  # 🧠
    (r"atom|core|micro",                  "&#9883;"),    # ⚛
    (r"network|mesh|inter",               "&#128279;"),  # 🔗
    (r"gem5|gem",                          "&#128142;"),  # 💎
    (r"keiko|wiki|doc",                   "&#128214;"),  # 📖
    (r"copilot.*api|api",                 "&#128268;"),  # 🔌
    (r"indigo|color",                     "&#127912;"),  # 🎨
    (r"neutra|ip",                        "&#128737;"),  # 🔡
    (r"coho|fish",                        "&#128031;"),  # 🐟
]
DEFAULT_ICON = "&#128195;"  # 📃
ROOT_PREFIXES = {"wiki", "internal"}


def pick_icon(title: str) -> str:
    for pattern, icon in ICON_MAP:
        if re.search(pattern, title, re.I):
            return icon
    return DEFAULT_ICON


def extract_meta(index_path: Path) -> dict | None:
    """Parse wiki-* meta tags and <title> from an index.html."""
    try:
        text = index_path.read_text(encoding="utf-8", errors="ignore")[:4096]
    except OSError:
        return None

    source = re.search(r'<meta\s+name="wiki-source"\s+content="([^"]*)"', text)
    gen = re.search(r'<meta\s+name="wiki-generated"\s+content="([^"]*)"', text)
    title_m = re.search(r"<title>([^<]+)</title>", text)
    if not title_m:
        return None

    raw_title = html_mod.unescape(title_m.group(1))
    parts = re.split(r"\s*[—–\-]\s*", raw_title, maxsplit=1)
    name = parts[0].strip()
    subtitle = parts[1].strip() if len(parts) > 1 else ""

    return {
        "source": source.group(1) if source else "",
        "generated": gen.group(1) if gen else str(date.today()),
        "name": name,
        "subtitle": subtitle,
        "raw_title": raw_title,
    }


def detect_tags(index_path: Path) -> list[tuple[str, str]]:
    """Heuristic: scan index.html content for language/framework signals."""
    try:
        text = index_path.read_text(encoding="utf-8", errors="ignore")[:30000].lower()
    except OSError:
        return []

    tags = []
    for lang, pat in [
        ("Python",     r"python|\.py\b|pytorch|flask|fastapi|django"),
        ("TypeScript", r"typescript|\.ts\b|\.tsx\b"),
        ("JavaScript", r"javascript|\.js\b|node\.js"),
        ("C++",        r"\bc\+\+|\.cpp\b|\.cxx\b|\.cc\b"),
        ("Rust",       r"\brust\b|\.rs\b|cargo"),
        ("Go",         r"\bgolang\b|\.go\b"),
        ("Java",       r"\bjava\b|\.java\b|maven|gradle"),
    ]:
        if re.search(pat, text):
            tags.append((lang, "green"))
            break

    added = set()
    for name, pat, color in [
        ("PyTorch",   r"pytorch|torch\.", "blue"),
        ("LangGraph", r"langgraph", "blue"),
        ("FastAPI",   r"fastapi", "yellow"),
        ("React",     r"\breact\b", "blue"),
        ("CUDA",      r"\bcuda\b", "yellow"),
        ("OpenCL",    r"\bopencl\b", "blue"),
        ("LLVM",      r"\bllvm\b", "yellow"),
        ("CLI",       r"\bcli\b|command.line", "blue"),
        ("AI Agent",  r"ai.agent|agentic|agent.system", "yellow"),
        ("LLM",       r"\bllm\b|language.model", "yellow"),
    ]:
        if re.search(pat, text) and name not in added:
            tags.append((name, color))
            added.add(name)
            if len(tags) >= 4:
                break

    return tags[:4]


def extract_project_slug_from_href(href: str) -> str | None:
    """Extract the project slug from either legacy or wiki-prefixed hub hrefs."""
    parts = [part for part in href.split("/") if part]
    if not parts:
        return None
    if parts[0] in ROOT_PREFIXES:
        return parts[1] if len(parts) > 1 else None
    return parts[0]


def extract_existing_project_slugs(content: str) -> set[str]:
    slugs = set()
    hrefs = re.findall(r'<a class="card" href="([^"]+)"', content)
    for href in hrefs:
        slug = extract_project_slug_from_href(href)
        if slug:
            slugs.add(slug)
    return slugs


def _card_href(card_html: str) -> str:
    match = re.search(r'<a class="card" href="([^"]+)"', card_html)
    return match.group(1) if match else ""


def _prefer_card(existing_card: str, candidate_card: str, preferred_prefix: str | None = "wiki/") -> str:
    existing_href = _card_href(existing_card)
    candidate_href = _card_href(candidate_card)
    if preferred_prefix:
        if candidate_href.startswith(preferred_prefix) and not existing_href.startswith(preferred_prefix):
            return candidate_card
        return existing_card

    existing_prefixed = existing_href.startswith("wiki/") or existing_href.startswith("internal/")
    candidate_prefixed = candidate_href.startswith("wiki/") or candidate_href.startswith("internal/")
    if not candidate_prefixed and existing_prefixed:
        return candidate_card
    return existing_card


def dedupe_card_grid(content: str, preferred_prefix: str | None = "wiki/") -> str:
    """Collapse duplicate cards so each project slug appears once in the grid."""
    match = CARD_GRID_RE.search(content)
    if not match:
        return content

    prefix, body, suffix = match.groups()
    cards = CARD_RE.findall(body)
    if not cards:
        return content

    chosen_cards: dict[str, str] = {}
    order: list[str] = []
    for card in cards:
        slug = extract_project_slug_from_href(_card_href(card))
        if not slug:
            continue
        if slug not in chosen_cards:
            chosen_cards[slug] = card
            order.append(slug)
            continue
        chosen_cards[slug] = _prefer_card(chosen_cards[slug], card, preferred_prefix=preferred_prefix)

    rebuilt_body = "\n\n".join(chosen_cards[slug] for slug in order)
    rebuilt = prefix + rebuilt_body + "\n" + suffix
    return content[:match.start()] + rebuilt + content[match.end():]


def resolve_wiki_index(entry: Path) -> Path | None:
    """Given a top-level directory, find its wiki index.html.

    Checks two patterns:
      1. <dir>/index.html  (+ search-index.json)
      2. <dir>/<YYYYMMDD_HHMMSS>/index.html  (latest timestamp)
    """
    # Pattern 1: direct
    idx = entry / "index.html"
    if idx.is_file() and (entry / "search-index.json").is_file():
        meta = extract_meta(idx)
        if meta:
            return idx

    # Pattern 2: timestamped subfolders (pick latest)
    for sub in sorted(entry.iterdir(), reverse=True):
        if sub.is_dir() and re.match(r"\d{8}_\d{6}$", sub.name):
            sub_idx = sub / "index.html"
            if sub_idx.is_file() and (sub / "search-index.json").is_file():
                meta = extract_meta(sub_idx)
                if meta:
                    return sub_idx

    return None


def build_project(index_path: Path, hub_index: Path = HUB_INDEX) -> dict | None:
    """Build a project dict from a wiki index.html path."""
    meta = extract_meta(index_path)
    if not meta:
        return None

    rel = relative_href(hub_index, index_path)
    page_count = len(glob.glob(str(index_path.parent / "**/*.html"), recursive=True))
    tags = detect_tags(index_path)

    return {
        "href": rel,
        "name": meta["name"],
        "subtitle": meta["subtitle"],
        "date": meta["generated"],
        "pages": page_count,
        "tags": tags,
        "icon": pick_icon(meta["raw_title"]),
    }


def get_existing_project_slugs(hub_index: Path = HUB_INDEX) -> set[str]:
    """Parse the current hub and return the set of project slugs already present."""
    if not hub_index.is_file():
        return set()
    content = hub_index.read_text(encoding="utf-8")
    return extract_existing_project_slugs(content)


def render_card(p: dict) -> str:
    esc = html_mod.escape
    tag_html = "\n      ".join(
        f'<span class="badge {color}">{esc(name)}</span>'
        for name, color in p["tags"]
    )
    desc = esc(p["subtitle"]) if p["subtitle"] else esc(p["name"])
    return f"""  <a class="card" href="{esc(p['href'])}">
    <h3>{p['icon']} {esc(p['name'])}</h3>
    <p>{desc}</p>
    <div class="tag-list">
      {tag_html}
    </div>
    <div class="meta">
      <span>&#128196; {p['pages']} pages</span>
      <span>&#128197; {esc(p['date'])}</span>
    </div>
  </a>"""


def update_stats(content: str, stats_mode: str = "public") -> str:
    """Recount cards in the HTML and update the stat-row numbers."""
    hrefs = re.findall(r'<a class="card" href="([^"]+)"', content)
    n_projects = len(hrefs)

    # Count total pages by summing the per-card page counts
    page_counts = re.findall(r'&#128196; (\d+) pages', content)
    total_pages = sum(int(x) for x in page_counts)

    # Count unique primary languages (green badges)
    langs = set(re.findall(r'<span class="badge green">([^<]+)</span>', content))

    content = re.sub(
        r'(<div class="stat-row">.*?<div class="num">)\d+(</div><div class="label">Projects</div>)',
        rf'\g<1>{n_projects}\2', content, flags=re.DOTALL)
    content = re.sub(
        r'(<div class="label">Projects</div></div>.*?<div class="num">)\d+(</div><div class="label">Wiki Pages</div>)',
        rf'\g<1>{total_pages}\2', content, flags=re.DOTALL)

    if stats_mode == "internal":
        versioned_projects = sum(
            1 for href in hrefs if re.search(r'/\d{8}_\d{6}/index\.html$', href)
        )
        content = re.sub(
            r'(<div class="label">Wiki Pages</div></div>.*?<div class="num">)\d+(</div><div class="label">Versioned Projects</div>)',
            rf'\g<1>{versioned_projects}\2', content, flags=re.DOTALL)
    else:
        content = re.sub(
            r'(<div class="label">Wiki Pages</div></div>.*?<div class="num">)\d+(</div><div class="label">Languages</div>)',
            rf'\g<1>{len(langs)}\2', content, flags=re.DOTALL)

    return content


def append_projects(
    new_projects: list[dict],
    hub_index: Path = HUB_INDEX,
    stats_mode: str = "public",
    preferred_prefix: str | None = "wiki/",
):
    """Append new project cards to index.html and update stats."""
    content = hub_index.read_text(encoding="utf-8")

    # Insert new cards just before the closing </div> of card-grid
    new_cards = "\n\n".join(render_card(p) for p in new_projects)
    # Find the last </a> inside card-grid, append after it
    content = re.sub(
        r'(  </a>\n)</div>\n\n<h2 id="about">',
        rf'\1\n{new_cards}\n</div>\n\n<h2 id="about">',
        content,
    )

    content = dedupe_card_grid(content, preferred_prefix=preferred_prefix)
    content = update_stats(content, stats_mode=stats_mode)
    hub_index.write_text(content, encoding="utf-8")

    print(f"Updated {hub_index}")
    for p in new_projects:
        print(f"  + {p['name']} ({p['pages']} pages) → {p['href']}")


def refresh_existing_cards(
    dirs: list[Path],
    hub_index: Path = HUB_INDEX,
    stats_mode: str = "public",
    preferred_prefix: str | None = "wiki/",
):
    """Update href, page count, and date for cards whose latest version changed."""
    if not hub_index.is_file():
        return
    content = hub_index.read_text(encoding="utf-8")
    original = content
    updated = []

    for d in dirs:
        if not d.is_dir():
            continue
        idx = resolve_wiki_index(d)
        if idx is None:
            continue

        rel = relative_href(hub_index, idx)
        proj = build_project(idx, hub_index=hub_index)
        if not proj:
            continue

        # Find existing card for this project directory in either legacy or new form.
        pattern = rf'<a class="card" href="((?:(?:wiki|internal)/)?{re.escape(d.name)}/[^"]*)"'
        match = re.search(pattern, content)
        if not match:
            continue

        old_href = match.group(1)
        if old_href == rel:
            continue  # already pointing to latest

        # Update href
        content = content.replace(f'href="{old_href}"', f'href="{rel}"')

        # Update page count and date in this card
        card_start = content.find(f'href="{rel}"')
        if card_start == -1:
            continue
        card_end = content.find("</a>", card_start)
        if card_end == -1:
            continue
        card_section = content[card_start:card_end]

        new_section = re.sub(
            r'&#128196; \d+ pages',
            f'&#128196; {proj["pages"]} pages',
            card_section,
        )
        new_section = re.sub(
            r'&#128197; [^<]+',
            f'&#128197; {html_mod.escape(proj["date"])}',
            new_section,
        )
        content = content[:card_start] + new_section + content[card_end:]
        updated.append(f"  ↻ {proj['name']}: {old_href} → {rel} ({proj['pages']} pages)")

    content = dedupe_card_grid(content, preferred_prefix=preferred_prefix)
    if content != original:
        content = update_stats(content, stats_mode=stats_mode)
        hub_index.write_text(content, encoding="utf-8")
        for line in updated:
            print(line)
    else:
        print("All existing cards already point to the latest versions.")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the wiki hub index.")
    parser.add_argument("projects", nargs="*", help="Specific project slugs or paths")
    parser.add_argument("--list", action="store_true", help="List detected projects without updating the hub")
    parser.add_argument("--root", choices=("public", "internal"), default="public", help="Select which content root to scan")
    parser.add_argument("--index", help="Override the hub index.html path")
    parser.add_argument("--no-post-scripts", action="store_true", help="Skip follow-on versions and switcher updates")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    opts = _parse_args(sys.argv[1:] if argv is None else argv)
    hub_index = Path(opts.index).resolve() if opts.index else get_hub_index(opts.root)
    stats_mode = "internal" if opts.root == "internal" else "public"
    preferred_prefix = "wiki/" if opts.root == "public" else None

    existing_dirs = get_existing_project_slugs(hub_index=hub_index)
    new_projects = []

    if opts.projects:
        # Specific directories requested
        dirs = [resolve_project_dir(name, root_name=opts.root) for name in opts.projects]
    else:
        # Auto-detect all
        dirs = iter_project_dirs(root_name=opts.root)

    for d in dirs:
        if not d.is_dir():
            print(f"  skip {d.name}: not a directory")
            continue

        idx = resolve_wiki_index(d)
        if idx is None:
            continue

        if d.name in existing_dirs:
            continue  # already in index.html (will be refreshed below)

        proj = build_project(idx, hub_index=hub_index)
        if proj:
            new_projects.append(proj)

    if opts.list:
        if new_projects:
            print("New wiki projects detected (not yet in index.html):")
            for p in new_projects:
                print(f"  {p['name']:30s} {p['pages']:3d} pages  {p['href']}")
        else:
            print("No new projects to add.")
        return 0

    if not new_projects:
        print("No new projects to add.")
    else:
        append_projects(
            new_projects,
            hub_index=hub_index,
            stats_mode=stats_mode,
            preferred_prefix=preferred_prefix,
        )

    # Refresh existing cards to point to latest versions
    refresh_existing_cards(
        dirs,
        hub_index=hub_index,
        stats_mode=stats_mode,
        preferred_prefix=preferred_prefix,
    )
    if not opts.no_post_scripts:
        _run_post_scripts(opts.projects, opts.root)
    return 0


def _run_post_scripts(project_args: list[str], root_name: str):
    """Run generate_versions.py and inject_version_switcher.py."""
    gen = REPO_ROOT / "generate_versions.py"
    inj = REPO_ROOT / "inject_version_switcher.py"
    for script in (gen, inj):
        if not script.is_file():
            continue
        cmd = [sys.executable, str(script), "--root", root_name] + project_args
        print(f"\nRunning {script.name} ...")
        subprocess.run(cmd, cwd=str(REPO_ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
