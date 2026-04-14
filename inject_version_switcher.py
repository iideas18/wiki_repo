#!/usr/bin/env python3
"""Inject a version-switcher dropdown into wiki project index pages.

Reads versions.json for each project and injects a <select> dropdown into the
hero section of every version's index.html. Switching versions fetches the
selected version's content inline (no full page reload).

Usage:
    python3 inject_version_switcher.py                # all projects
    python3 inject_version_switcher.py oclgrind gem5  # specific projects
    python3 inject_version_switcher.py --check        # dry-run: report only
"""

import json
import re
import sys
from pathlib import Path

WIKI_DIR = Path(__file__).resolve().parent
TIMESTAMP_RE = re.compile(r"^\d{8}_\d{6}$")

MARKER_START = "<!-- VERSION_SWITCHER_START -->"
MARKER_END = "<!-- VERSION_SWITCHER_END -->"

SWITCHER_CSS = """\
.version-switcher{display:inline-flex;align-items:center;gap:8px;margin-top:1rem;\
background:var(--surface,#161b22);border:1px solid var(--border,#30363d);\
border-radius:8px;padding:6px 14px}
.version-label{color:var(--text-muted,#8b949e);font-size:.85rem}
.version-select{background:var(--bg,#0d1117);color:var(--accent,#58a6ff);\
border:1px solid var(--border,#30363d);border-radius:4px;padding:4px 8px;\
font-size:.85rem;cursor:pointer;font-family:inherit}
.version-select:focus{outline:2px solid var(--accent,#58a6ff);outline-offset:1px}
@media print{.version-switcher{display:none!important}}"""

SWITCHER_JS_TEMPLATE = (
    "(function(){\n"
    "  var versions=/*VERSIONS_JSON*/;\n"
    "  if(!versions||versions.length<2)return;\n"
    "  var dirPath=location.pathname.replace(/[^/]*$/,'');\n"
    r"  var tsMatch=dirPath.match(/\/(\d{8}_\d{6})\/$/);"+"\n"
    r"  var projectBase=tsMatch?dirPath.replace(/\d{8}_\d{6}\/$/,''):dirPath;"+"\n"
    "  var curTs=tsMatch?tsMatch[1]:((versions.find(function(v){return v.latest;})||versions[0]).timestamp);\n"
    "  var wrap=document.createElement('div');\n"
    "  wrap.className='version-switcher';\n"
    "  var lbl=document.createElement('span');\n"
    "  lbl.className='version-label';\n"
    "  lbl.textContent='Version:';\n"
    "  var sel=document.createElement('select');\n"
    "  sel.className='version-select';\n"
    "  sel.setAttribute('aria-label','Switch wiki version');\n"
    "  versions.forEach(function(v){\n"
    "    var o=document.createElement('option');\n"
    "    o.value=v.timestamp;\n"
    "    var rev=v.rev?' ('+v.rev.substring(0,7)+')':'';\n"
    "    o.textContent=v.date+rev+(v.latest?' (latest)':'');\n"
    "    if(v.timestamp===curTs)o.selected=true;\n"
    "    sel.appendChild(o);\n"
    "  });\n"
    "  wrap.appendChild(lbl);\n"
    "  wrap.appendChild(sel);\n"
    "  var hero=document.querySelector('.hero');\n"
    "  if(hero)hero.appendChild(wrap);\n"
    "  sel.addEventListener('change',function(){\n"
    "    var newTs=this.value;\n"
    "    if(newTs===curTs)return;\n"
    "    location.href=projectBase+newTs+'/index.html';\n"
    "  });\n"
    "})();"
)


def build_snippet(versions_json: str) -> str:
    js = SWITCHER_JS_TEMPLATE.replace("/*VERSIONS_JSON*/", versions_json)
    return (
        f"\n{MARKER_START}\n"
        f"<style>{SWITCHER_CSS}</style>\n"
        f"<script>{js}</script>\n"
        f"{MARKER_END}\n"
    )


def strip_old_snippet(html: str) -> str:
    """Remove any previously injected version-switcher block."""
    return re.sub(
        rf"\n?{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}\n?",
        "",
        html,
        flags=re.DOTALL,
    )


def inject_into_file(index_path: Path, versions_json: str, dry_run: bool = False) -> bool:
    """Inject the version switcher into an index.html. Returns True if changed."""
    text = index_path.read_text(encoding="utf-8", errors="ignore")
    clean = strip_old_snippet(text)

    # Inject just before </body>
    if "</body>" not in clean:
        return False

    snippet = build_snippet(versions_json)
    new_text = clean.replace("</body>", snippet + "</body>")

    if new_text == text:
        return False

    if not dry_run:
        index_path.write_text(new_text, encoding="utf-8")
    return True


def process_project(project_dir: Path, dry_run: bool = False) -> int:
    """Inject version switcher into all versions of a project. Returns count."""
    vj = project_dir / "versions.json"
    if not vj.is_file():
        return 0

    versions = json.loads(vj.read_text(encoding="utf-8"))
    if len(versions) < 1:
        return 0

    versions_json = json.dumps(versions, separators=(",", ":"))

    count = 0
    for v in versions:
        ts = v["timestamp"]
        idx = project_dir / ts / "index.html"
        if not idx.is_file():
            continue
        changed = inject_into_file(idx, versions_json, dry_run=dry_run)
        if changed:
            count += 1
            tag = " (dry-run)" if dry_run else ""
            print(f"  {idx.relative_to(WIKI_DIR)}{tag}")

    return count


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry_run = "--check" in sys.argv

    if args:
        dirs = [WIKI_DIR / name for name in args]
    else:
        dirs = sorted(
            d for d in WIKI_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    total = 0
    for d in dirs:
        if not d.is_dir():
            continue
        n = process_project(d, dry_run=dry_run)
        total += n

    action = "Would inject into" if dry_run else "Injected version switcher into"
    print(f"{action} {total} file(s).")


if __name__ == "__main__":
    main()
