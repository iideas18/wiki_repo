# Copilot Instructions — Internal Wiki

## Project Overview

This is a self-hosted wiki hub that auto-generates HTML documentation from source code repositories. The **wiki-generator** Copilot skill (`.github/skills/wiki-generator/`) analyzes source repos and produces self-contained HTML wiki pages with Mermaid diagrams, full-text search, and dark/light theme support.

The repo contains:
- A hub landing page (`index.html`) with cards linking to each project's wiki
- Generated wiki directories (one per documented project), each with its own `index.html` and `search-index.json`
- Python tooling for post-generation fixes and index management
- The wiki-generator skill itself (prompt template + shell/Python scripts)

## Key Commands

```bash
# Generate a wiki from a local source directory or git URL
bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh -s /path/to/source
bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh -s https://github.com/user/repo.git

# Fix common HTML issues in generated wikis
python3 fix_wiki_html.py              # all projects
python3 fix_wiki_html.py project-name # specific project
python3 fix_wiki_html.py --check      # dry-run report only

# Update hub index.html with newly generated wikis
# (also regenerates versions.json and re-injects version switcher)
python3 update_index.py               # auto-detect new projects
python3 update_index.py project-name  # specific project
python3 update_index.py --list        # dry-run list only

# Generate versions.json manifests (standalone)
python3 generate_versions.py               # all projects
python3 generate_versions.py project-name  # specific project
python3 generate_versions.py --list        # dry-run list

# Inject version switcher into wiki pages (standalone)
python3 inject_version_switcher.py               # all projects
python3 inject_version_switcher.py project-name  # specific project
python3 inject_version_switcher.py --check       # dry-run report only

# Preview the site locally
python -m http.server 8080
```

## Architecture

### Wiki Generation Pipeline

1. **Phase 1 (Research):** `run_wiki_gen.sh` invokes Copilot to analyze source code. Results are cached so subsequent runs can skip this phase (`--no-cache` to force re-research, `--cache-only` to stop after research).
2. **Phase 2 (HTML Generation):** Copilot generates wiki HTML pages using templates from `resources/` (`l0-template.html`, `l1-template.html`, `l2-template.html`, `focus-template.html`, `search-template.html`).
3. **Post-processing scripts** in `scripts/` build search indexes, navigation trees, cross-references, and stats.
4. **`fix_wiki_html.py`** patches common generator bugs (outerHTML→cloneNode, theme key consistency, mermaid error handling, overlay null guards).
5. **`update_index.py`** detects new wiki directories and appends project cards to the hub `index.html`, updating stats. It also calls `generate_versions.py` and `inject_version_switcher.py` automatically.

### Version Switcher Pipeline

After wiki generation, three scripts maintain per-project version switching:

1. **`generate_versions.py`** — scans each project dir for timestamped subdirs, extracts metadata (date, source rev, page count), writes `<project>/versions.json`.
2. **`inject_version_switcher.py`** — reads `versions.json` and injects a `<select>` dropdown + inline-fetch JS into each version's `index.html` hero section. Idempotent (safe to re-run).
3. The injected JS fetches `../versions.json` at page load; on selection change, it fetches the other version's `index.html` and swaps `<main>` content inline (no page reload). The dropdown is only shown when 2+ versions exist.

### Adaptive Depth

The wiki generator auto-detects project structure depth:
- **1-level:** Flat module → single page
- **2-level:** Module with sub-modules → overview + deep-dive pages
- **3-level:** Multi-module project → hub + module overviews + sub-module deep-dives

### Wiki Directory Layouts

Projects use one of two layouts:
- **Flat:** `<project>/index.html` + `search-index.json` at project root
- **Timestamped:** `<project>/<YYYYMMDD_HHMMSS>/index.html` — allows snapshot history; `update_index.py` picks the latest

### Detection Convention

A directory is recognized as a wiki project when it contains both `index.html` (with a `<meta name="wiki-source">` tag) and `search-index.json`.

## Conventions

- **Theme key:** All wiki pages must use `localStorage` key `neutra-ip-theme` for dark/light theme persistence. `fix_wiki_html.py` enforces this.
- **Shared CSS:** Wiki pages follow the design tokens in `resources/_shared-css.txt` and `resources/_style-spec.md`. The hub `index.html` uses the same CSS variable names (`--bg`, `--surface`, `--border`, `--accent`, etc.).
- **Python scripts** are standalone (no `requirements.txt`); they use only the standard library.
- **Generated content** (the wiki HTML directories) is committed to the repo — this is intentional; the site is served directly from the repo.
- **All wiki projects use timestamped subdirectories** (`<project>/<YYYYMMDD_HHMMSS>/`). Each timestamp is a full snapshot. The latest is linked from the hub.
- **`versions.json`** sits at each project root and lists all available snapshots. It is consumed by the in-page version switcher (injected JS in each project's `index.html`).
- **`.git-clones/`** is gitignored — used as scratch space when cloning remote repos for wiki generation.
