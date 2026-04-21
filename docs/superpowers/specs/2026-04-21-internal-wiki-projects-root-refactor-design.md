# Internal Wiki Projects Root Refactor

**Status:** Approved
**Date:** 2026-04-21
**Scope:** `/mnt/disk1/zy/internal_wiki` repository layout, wiki maintenance scripts, hub link generation, on-disk project location
**Audience:** Maintainers of the internal wiki hub and the wiki-generator maintenance tooling
**Relationship to prior work:** Preserves the current wiki output format and version-switcher behavior. Only the repository layout and project discovery model change.

## 1. Problem Statement

The repository root currently mixes three different concerns:

- hub assets and operational scripts such as `index.html`, `update_index.py`, `generate_versions.py`, `inject_version_switcher.py`, and `fix_wiki_html.py`
- generated wiki project directories such as `ai-hedge-fund/`, `gem5/`, `minimind/`, and `openclaw/`
- project-adjacent helper directories such as `claude-code_source/`

This flat layout makes the repository harder to reason about. A new maintainer cannot immediately tell which top-level directories are application/tooling concerns and which are content payloads. It also encourages every maintenance script to assume that project directories live directly under the repository root, which couples the codebase to one physical layout.

## 2. Goals

1. Introduce a single canonical content root: `wiki/`.
2. Move all project-related directories under `wiki/`, including project-adjacent helper/source siblings.
3. Keep the hub page and operational tooling at the repository root.
4. Update project discovery code so scripts scan `wiki/` instead of the repository root.
5. Update the generator pipeline so newly generated output is written under `wiki/<project>/<timestamp>/` while logs and clone scratch space remain repo-root concerns.
6. Update hub links so project cards point to `wiki/<project>/...`.
7. Preserve the internal structure of each project directory; this refactor is not a schema rewrite.

### Non-goals

- Introducing a second-level `site/` and `source/` split inside every project.
- Keeping backward-compatible hub links at `<project>/...`. The user explicitly accepted path changes.
- Rewriting generated wiki HTML content beyond what is needed to keep the hub and maintenance scripts functional.
- Moving repo-level operational folders such as `docs/`, `tests/`, `logs/`, `.github/`, or `.git-clones/` into `wiki/`.

## 3. Success Criteria

- The repository root contains a dedicated `wiki/` directory holding all project-related directories.
- `index.html` continues to render the hub and its cards navigate to `wiki/<project>/...` paths.
- `update_index.py`, `generate_versions.py`, `inject_version_switcher.py`, `fix_wiki_html.py`, and `retrofit_overview.py` all operate against the new content root without requiring callers to know the internal path layout.
- `run_wiki_gen.sh` generates new wiki snapshots under `wiki/<project>/<timestamp>/` and continues to keep logs under `logs/` and clone scratch data under `.git-clones/` at the repository root.
- Running the maintenance flow after the move regenerates `versions.json`, rewrites version-switcher payloads, and refreshes hub links successfully.
- Re-running `update_index.py` after migration does not create duplicate project cards and correctly refreshes existing `wiki/...` links.
- Existing generated project content remains usable after the move without per-project manual edits.

## 4. Target Layout

```text
internal_wiki/
  wiki/
    ai-hedge-fund/
    claude-code/
    claude-code_source/
    gem5/
    gpgpu-sim_distribution/
    hermes-agent/
    minimind/
    oclgrind/
    openclaw/
    ...
  index.html
  README.md
  LICENSE
  update_index.py
  generate_versions.py
  inject_version_switcher.py
  fix_wiki_html.py
  retrofit_overview.py
  launch_server.sh
  docs/
  tests/
  logs/
  .git-clones/
  .github/
```

### Classification rule

The `wiki/` directory contains:

- generated wiki projects
- helper/source directories that are coupled to a specific project and should travel with the content set

The repository root contains:

- hub and maintenance scripts
- tests, documentation, logs, scratch/clone directories, and repository metadata

## 5. Path Model

Every maintenance script should stop inferring meaning from the repository root alone and should instead use a shared path model:

```python
REPO_ROOT = Path(__file__).resolve().parent
PROJECTS_ROOT = REPO_ROOT / "wiki"
HUB_INDEX = REPO_ROOT / "index.html"
```

To reduce drift, path discovery should be centralized in one small helper module that provides:

- repository root resolution
- projects root resolution
- enumeration of project directories
- resolution of explicit project names to the canonical project directory, using `wiki/<name>` when present and falling back to `<repo-root>/<name>` during migration
- repo-relative display helpers for logging and diagnostics

During the migration window, discovery must be dual-root aware:

- prefer `wiki/<project>` when it exists
- still detect legacy repo-root project directories until the physical move is complete
- avoid returning duplicate projects when the same project is visible in both locations
- resolve explicit CLI project-name arguments with the same precedence rules so direct one-project flows continue to work during migration

Mixed-layout support is intended for different project slugs being moved at different times, not for one project being split across both roots. Each per-project move must be atomic at the directory level. If the same slug is accidentally visible in both roots, scripts prefer `wiki/<slug>` and treat the repo-root copy as stale conflict state rather than merging snapshots across roots.

## 6. Script Impact

### 6.1 `update_index.py`

- Keep reading and writing the hub at the repository root.
- Enumerate candidate project directories from the dual-root helper during migration, then from `PROJECTS_ROOT` alone after cutover.
- For a project that still exists only at the repo root, keep its legacy `<slug>/...` hub href until that project is physically moved.
- For a project that exists under `wiki/`, build card `href` values relative to the repository root so cards resolve to `wiki/<project>/<timestamp>/index.html`.
- Refresh logic must normalize every card to a project slug and converge the hub to exactly one card per slug. If both legacy and new href forms exist, keep the `wiki/...` form and repair or remove the legacy duplicate.

### 6.2 `generate_versions.py`

- Enumerate projects from the dual-root helper during migration, then from `PROJECTS_ROOT` alone after cutover.
- During migration, write `versions.json` beside the helper-resolved project directory, whether that slug still lives at the repo root or has already moved under `wiki/`.
- After cutover, all manifests live at `wiki/<project>/versions.json`.
- Continue to support explicit project-name CLI args, resolving names through the shared mixed-layout helper during migration.

### 6.3 `inject_version_switcher.py`

- Enumerate projects from the dual-root helper during migration, then from `PROJECTS_ROOT` alone after cutover.
- Read `versions.json` from the helper-resolved project directory during migration, then from `wiki/<project>/versions.json` after cutover.
- Inject into versioned `index.html` pages under the helper-resolved project directory during migration, then under `wiki/<project>/<timestamp>/` after cutover.
- Print repo-relative paths in logs so output reflects the new location.

### 6.4 `fix_wiki_html.py`

- Enumerate targets from the dual-root helper during migration, then from `PROJECTS_ROOT` alone after cutover.
- Resolve explicit args through the shared mixed-layout helper during migration.
- Report file paths relative to the repository root so diagnostics show `wiki/...`.

### 6.5 `retrofit_overview.py`

- Discover projects through the dual-root helper during migration, then from `PROJECTS_ROOT` alone after cutover.
- Preserve the existing behavior for `versions.json` lookup and active-version resolution.

### 6.6 `.github/skills/wiki-generator/scripts/run_wiki_gen.sh`

- Split the repository root from the projects root.
- Continue to default logs to `REPO_ROOT/logs`.
- Continue to default git clones to `REPO_ROOT/.git-clones`.
- Default project output to `REPO_ROOT/wiki` so new snapshots land under `wiki/<project>/<timestamp>/`.
- Continue to find repo-root tooling such as `generate_versions.py`, `inject_version_switcher.py`, and `update_index.py` at the repository root, not under the output base.
- During the temporary mixed-layout migration window, a canonical publish for slug `<project>` must refuse to run if a legacy repo-root `<project>/` directory still exists. This prevents the generator from creating a forbidden split-root state for a single slug.
- If `-o/--output` is explicitly set to a custom directory that is not the canonical `PROJECTS_ROOT`, treat that run as an ad-hoc export: generate into the custom tree, skip repo-root post-generation maintenance (`generate_versions.py`, `inject_version_switcher.py`, `update_index.py`), and print a clear notice that custom outputs are intentionally not integrated into the repo hub or repo-managed version manifests. This prevents a custom output run from mutating the repository hub while making the altered semantics explicit.
- If `--cache-only` is set and the caller did not explicitly override `-o/--output`, write the research-only output under a dedicated staging root such as `REPO_ROOT/.wiki-cache/<project>/<timestamp>/` instead of the canonical published wiki tree. Cache-only runs are non-publishable artifacts: they do not trigger snapshot pruning, version-manifest generation, version-switcher injection, or hub refresh.
- Normal non-cache-only runs should search both the dedicated cache staging root and the latest published project snapshots for warm research before deciding whether a reusable cache exists.

## 7. Migration Strategy

### Phase 1: Make code layout-aware

1. Add a small shared helper module for repository paths.
2. Update maintenance scripts and the generator pipeline to use `PROJECTS_ROOT`.
3. Keep the first code change tolerant: discovery must accept both `wiki/` and legacy repo-root projects during cutover. This keeps the branch runnable while `wiki/` exists but the move is still in progress.

### Phase 2: Move content

1. Create `wiki/`.
2. Move all project-related directories into `wiki/`.
3. Leave hub/tooling/docs/tests/logs at the repository root.

The move is only considered complete once no project-related directories remain at the repository root.

### Phase 3: Refresh derived artifacts

1. Run `python3 update_index.py` to rewrite hub cards to `wiki/...`.
2. Run `python3 generate_versions.py`.
3. Run `python3 inject_version_switcher.py`.
4. Run `python3 fix_wiki_html.py --check`.
5. Confirm a no-op or refresh-only rerun of `python3 update_index.py` does not append duplicate cards.

The hub-refresh identity key is the normalized project slug, derived from the directory name. `update_index.py` must accept both legacy `<slug>/...` and new `wiki/<slug>/...` hrefs, normalize them to the same slug, prefer the `wiki/...` form, and repair or collapse duplicates if both forms already exist in `index.html`.

During mixed-layout cutover, refresh behavior is per-project rather than global:

- projects not yet moved remain discoverable from the repo root and keep legacy hub links
- projects already moved switch to `wiki/...` links
- reruns must still converge to exactly one hub card per project slug

### Phase 4: Verify manually

1. Serve the repo with `python -m http.server 8080`.
2. Open the hub page.
3. Click several cards and confirm they navigate correctly into `wiki/...`.
4. Open at least one project with a version switcher and confirm it still works.

## 8. Risks and Mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Missed root-level project enumeration | A single unpatched script silently ignores moved projects | Centralize path discovery in a helper module and use it everywhere |
| Broken hub links | Cards would still point to `<project>/...` after the move | Regenerate hub links with `update_index.py` after migration |
| New generations still land at the repo root | The repo would drift back into a mixed layout immediately after the refactor | Update `run_wiki_gen.sh` to target `REPO_ROOT/wiki` for project output while keeping repo-root logs and clone scratch directories |
| Log and diagnostic confusion | Relative-path printing may become inconsistent | Standardize repo-relative path rendering |
| Partial migration leaves branch broken | Moving directories before updating scripts would strand tooling | Update code first, then move directories |
| Duplicate hub cards on rerun | Existing card detection assumes the first href segment is the project name | Normalize both legacy `<project>/...` and new `wiki/<project>/...` hrefs in `update_index.py` |
| Hidden assumptions in future scripts | New tooling may repeat the old flat-root assumption | Document `PROJECTS_ROOT` as the canonical contract in this spec and the helper module |

## 9. Verification Plan

Automated verification for this refactor should cover:

- explicit project-name resolution under `wiki/`
- mixed-layout discovery while both repo-root and `wiki/` project directories may coexist during migration
- hub `href` generation relative to the repository root
- idempotent `update_index.py` behavior for both legacy and new-style hub hrefs
- generator output under `wiki/<project>/<timestamp>/`

Manual verification should cover:

- hub card navigation
- version-switcher navigation
- `fix_wiki_html.py --check` operating across moved content
- `retrofit_overview.py --dry-run` still listing projects correctly

## 10. Decision Summary

The repository will adopt `wiki/` as its only canonical content root. Project directories move under `wiki/`, while hub files and operational tooling stay at the repository root. This produces a cleaner repository structure without changing the internal schema of each project.