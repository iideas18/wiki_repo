# Internal Wiki Hub

This repository hosts a self-contained HTML wiki hub for multiple source code projects. Public published wiki content lives under `wiki/`, while private local-only content can live under `internal/`. Repo-root scripts maintain the landing pages, version manifests, overview pages, and post-generation fixes.

The repo has two distinct responsibilities:

- publish generated project documentation snapshots under `wiki/<project>/...`
- keep private local-only snapshots under `internal/<project>/...` without routing them to the public site
- maintain the hub and supporting artifacts that make those snapshots browsable

## Quick Start

Preview the existing site locally:

```bash
cd /mnt/disk1/zy/internal_wiki
python -m http.server 8080
```

Useful maintenance checks:

```bash
python3 update_index.py --list
python3 fix_wiki_html.py --check
python3 generate_versions.py --list
```

## Generate A Wiki

Generate a wiki from a local checkout or a git URL:

```bash
bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh -s /path/to/source
bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh -s https://github.com/user/repo.git
```

The generator pipeline works in four stages:

1. Research the source repository and cache the analysis.
2. Generate self-contained HTML wiki pages from the templates in `.github/skills/wiki-generator/resources/`.
3. Build derived artifacts such as search indexes, navigation trees, and cross-links.
4. Refresh repo-managed outputs such as `versions.json`, the in-page version switcher, and the hub landing page.

## Common Commands

Refresh the hub after adding or moving projects:

```bash
python3 update_index.py
python3 update_index.py project-name
python3 update_index.py --list
python3 update_internal_index.py
```

Rebuild per-project version manifests:

```bash
python3 generate_versions.py
python3 generate_versions.py project-name
python3 generate_versions.py --list
python3 generate_versions.py --root internal
```

Inject or verify the in-page version switcher:

```bash
python3 inject_version_switcher.py
python3 inject_version_switcher.py project-name
python3 inject_version_switcher.py --check
python3 inject_version_switcher.py --root internal
```

Fix common generated-HTML issues:

```bash
python3 fix_wiki_html.py
python3 fix_wiki_html.py project-name
python3 fix_wiki_html.py --check
python3 fix_wiki_html.py --root internal
```

Retrofit `overview.html` into existing committed projects:

```bash
python3 retrofit_overview.py
python3 retrofit_overview.py project-name --force
python3 retrofit_overview.py --dry-run
```

## Repository Layout

```text
internal_wiki/
	index.html                    # Hub landing page
	wiki/                         # Canonical root for published wiki projects
		<project>/
			versions.json             # Version manifest for the project
			<YYYYMMDD_HHMMSS>/        # Snapshot directory
				index.html              # Project landing page for that snapshot
				search-index.json       # Full-text search index for that snapshot
				...
	internal/                     # Local-only internal wiki content root
		index.html                  # Private internal hub
		<project>/
			versions.json             # Version manifest when the project is timestamped
			<YYYYMMDD_HHMMSS>/
				index.html
				search-index.json
			...
	update_index.py               # Hub refresh and card generation
	update_internal_index.py      # Internal-only hub refresh wrapper
	generate_versions.py          # versions.json generator
	inject_version_switcher.py    # In-page version switcher injector
	fix_wiki_html.py              # Post-generation HTML fixer
	retrofit_overview.py          # overview.html retrofitter
	internal_wiki_paths.py        # Shared path/discovery helpers
	docs/                         # Design notes and implementation docs
	tests/                        # Script regression tests
	logs/                         # Generator logs
	.git-clones/                  # Scratch clones for remote sources
```

## Content Model

Projects live under the canonical `wiki/` content root and use one of two published layouts:

- Flat: `wiki/<project>/index.html` with `search-index.json` at the project root.
- Timestamped: `wiki/<project>/<YYYYMMDD_HHMMSS>/index.html` for snapshot history.

The repository currently prefers timestamped snapshots for published content. Each project keeps its manifest at `wiki/<project>/versions.json`, and `update_index.py` links the hub to the latest available snapshot.

Private local-only content can be kept under `internal/` using the same flat or timestamped project layout. That tree is intentionally separated from the public hub and should be refreshed through `update_internal_index.py` or explicit `--root internal` maintenance commands.

A directory is treated as a valid published wiki version when it contains:

- `index.html` with a `<meta name="wiki-source">` tag
- `search-index.json`

## Maintenance Model

`internal_wiki_paths.py` is the shared source of truth for repository path resolution. Scripts should resolve project directories through that helper instead of assuming project folders live directly at the repo root.

`update_index.py` is the main repo-level maintenance entrypoint. It refreshes project cards in `index.html`, then runs:

- `generate_versions.py`
- `inject_version_switcher.py`

Use the lower-level scripts directly when you only need one maintenance step.

## Conventions

- Published project content lives under `wiki/<project>/...`.
- Private local-only content lives under `internal/<project>/...` and should never be routed to the public site by default.
- Generated HTML is committed intentionally; the repo serves as the published site.
- `internal/` is gitignored intentionally.
- The theme preference key is `neutra-ip-theme` across hub and project pages.
- The maintenance scripts use Python standard library only.
- `.git-clones/` is scratch space for remote source generation and should remain uncommitted.

## Related Files

- `.github/copilot-instructions.md` documents repository conventions for agent-assisted maintenance.
- `.github/skills/wiki-generator/` contains the generator prompt, templates, and helper scripts.
- `docs/superpowers/` stores design and implementation notes for major maintenance changes.