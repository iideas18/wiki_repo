#!/usr/bin/env python3
"""Auto-detect wiki projects and append them to the hub index.html.

Scans directories for wiki projects (index.html with <meta name="wiki-source">
+ search-index.json), extracts metadata, and appends new cards to index.html.

Usage:
    python3 update_index.py                       # auto-detect & append ALL new projects
    python3 update_index.py claude-code minimind   # append only these specific dirs
    python3 update_index.py --list                 # list detected projects (dry run)
"""

import re
import glob
import sys
import html as html_mod
import subprocess
from pathlib import Path
from datetime import date

WIKI_DIR = Path(__file__).resolve().parent

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


def build_project(index_path: Path) -> dict | None:
    """Build a project dict from a wiki index.html path."""
    meta = extract_meta(index_path)
    if not meta:
        return None

    rel = index_path.relative_to(WIKI_DIR).as_posix()
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


def get_existing_hrefs() -> set[str]:
    """Parse the current index.html and return the set of href values already present."""
    index_path = WIKI_DIR / "index.html"
    if not index_path.is_file():
        return set()
    content = index_path.read_text(encoding="utf-8")
    return set(re.findall(r'<a class="card" href="([^"]+)"', content))


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


def update_stats(content: str) -> str:
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
    content = re.sub(
        r'(<div class="label">Wiki Pages</div></div>.*?<div class="num">)\d+(</div><div class="label">Languages</div>)',
        rf'\g<1>{len(langs)}\2', content, flags=re.DOTALL)

    return content


def append_projects(new_projects: list[dict]):
    """Append new project cards to index.html and update stats."""
    index_path = WIKI_DIR / "index.html"
    content = index_path.read_text(encoding="utf-8")

    # Insert new cards just before the closing </div> of card-grid
    new_cards = "\n\n".join(render_card(p) for p in new_projects)
    # Find the last </a> inside card-grid, append after it
    content = re.sub(
        r'(  </a>\n)</div>\n\n<h2 id="about">',
        rf'\1\n{new_cards}\n</div>\n\n<h2 id="about">',
        content,
    )

    content = update_stats(content)
    index_path.write_text(content, encoding="utf-8")

    print(f"Updated {index_path}")
    for p in new_projects:
        print(f"  + {p['name']} ({p['pages']} pages) → {p['href']}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    list_only = "--list" in sys.argv

    existing_hrefs = get_existing_hrefs()
    new_projects = []

    if args:
        # Specific directories requested
        dirs = [WIKI_DIR / name for name in args]
    else:
        # Auto-detect all
        dirs = sorted(d for d in WIKI_DIR.iterdir()
                       if d.is_dir() and not d.name.startswith("."))

    for d in dirs:
        if not d.is_dir():
            print(f"  skip {d.name}: not a directory")
            continue

        idx = resolve_wiki_index(d)
        if idx is None:
            continue

        rel = idx.relative_to(WIKI_DIR).as_posix()
        if rel in existing_hrefs:
            continue  # already in index.html

        proj = build_project(idx)
        if proj:
            new_projects.append(proj)

    if list_only:
        if new_projects:
            print("New wiki projects detected (not yet in index.html):")
            for p in new_projects:
                print(f"  {p['name']:30s} {p['pages']:3d} pages  {p['href']}")
        else:
            print("No new projects to add.")
        return

    if not new_projects:
        print("No new projects to add — index.html is up to date.")
    else:
        append_projects(new_projects)

    # Regenerate versions.json and inject version switcher for all projects
    if not list_only:
        _run_post_scripts(args)


def _run_post_scripts(project_args: list[str]):
    """Run generate_versions.py and inject_version_switcher.py."""
    gen = WIKI_DIR / "generate_versions.py"
    inj = WIKI_DIR / "inject_version_switcher.py"
    for script in (gen, inj):
        if not script.is_file():
            continue
        cmd = [sys.executable, str(script)] + project_args
        print(f"\nRunning {script.name} ...")
        subprocess.run(cmd, cwd=str(WIKI_DIR))


if __name__ == "__main__":
    main()
