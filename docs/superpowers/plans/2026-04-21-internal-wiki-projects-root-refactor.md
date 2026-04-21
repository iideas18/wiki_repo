# Internal Wiki Projects Root Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all project-related directories under `wiki/` while keeping the hub and maintenance tooling at the repository root, and update every maintenance and generation script to use the new projects root.

**Architecture:** Add one shared path helper that defines the repository root, the canonical projects root, mixed-layout migration discovery, and repo-relative logging helpers. Update every project-enumerating script plus the generator pipeline to use that shared model, then move the directories on disk, regenerate derived hub metadata, and verify the repo through script checks and a local static-server smoke test.

**Tech Stack:** Python 3 stdlib (`pathlib`, `typing`, `unittest`/`pytest`), existing wiki maintenance scripts, shell `mv`, and `python -m http.server`.

---

## Chunk 1: Path Model and Safety Net

### Task 1: Add a shared paths helper

**Files:**
- Create: `/mnt/disk1/zy/internal_wiki/internal_wiki_paths.py`
- Create: `/mnt/disk1/zy/internal_wiki/tests/test_internal_wiki_paths.py`

- [ ] **Step 1: Write the failing tests for repository-root and projects-root resolution**
- [ ] **Step 2: Run `pytest /mnt/disk1/zy/internal_wiki/tests/test_internal_wiki_paths.py -v` and confirm failure**
- [ ] **Step 3: Implement `REPO_ROOT`, `PROJECTS_ROOT`, `get_projects_root()`, `resolve_project_dirs()`, and `repo_relative()` in `internal_wiki_paths.py`**
- [ ] **Step 4: Re-run `pytest /mnt/disk1/zy/internal_wiki/tests/test_internal_wiki_paths.py -v` and confirm pass**

### Task 2: Make project discovery tolerant during the migration window

**Files:**
- Modify: `/mnt/disk1/zy/internal_wiki/internal_wiki_paths.py`
- Test: `/mnt/disk1/zy/internal_wiki/tests/test_internal_wiki_paths.py`

- [ ] **Step 1: Add failing tests proving discovery supports three states: root-only, wiki-only, and mixed-layout with `wiki/` taking precedence per project**
- [ ] **Step 1: Add failing tests proving discovery supports three states: root-only, wiki-only, and mixed-layout with `wiki/` taking precedence per project, including explicit single-project resolution during cutover**
- [ ] **Step 2: Run the targeted test and confirm failure**
- [ ] **Step 3: Implement the mixed-layout fallback behavior without duplicate project resolution**
- [ ] **Step 4: Re-run the targeted test and confirm pass**

## Chunk 2: Script Refactor

### Task 3: Update `update_index.py` to scan the projects root and emit `wiki/...` hrefs

**Files:**
- Modify: `/mnt/disk1/zy/internal_wiki/update_index.py`
- Test: `/mnt/disk1/zy/internal_wiki/tests/test_update_index_paths.py`

- [ ] **Step 1: Write failing tests for candidate discovery, href generation under `wiki/`, normalized slug matching, per-project legacy-vs-new link selection during cutover, and repair of pre-existing legacy/new duplicate cards**
- [ ] **Step 2: Run `pytest /mnt/disk1/zy/internal_wiki/tests/test_update_index_paths.py -v` and confirm failure**
- [ ] **Step 3: Import the shared paths helper and replace direct `WIKI_DIR.iterdir()` / `WIKI_DIR / name` usage**
- [ ] **Step 4: Ensure hub reads and writes still target repo-root `index.html`**
- [ ] **Step 5: Re-run the targeted tests and confirm pass**

### Task 4: Update the generator pipeline to write new snapshots under `wiki/`

**Files:**
- Modify: `/mnt/disk1/zy/internal_wiki/.github/skills/wiki-generator/scripts/run_wiki_gen.sh`

- [ ] **Step 1: Add a dry-run-oriented check that captures the current output, log, and clone paths**
- [ ] **Step 2: Update the script so project output defaults to `/mnt/disk1/zy/internal_wiki/wiki` while logs remain under `/mnt/disk1/zy/internal_wiki/logs` and clone scratch data remains under `/mnt/disk1/zy/internal_wiki/.git-clones`**
- [ ] **Step 3: Ensure repo-root tooling discovery for `generate_versions.py`, `inject_version_switcher.py`, and `update_index.py` no longer depends on the output base**
- [ ] **Step 4: When `-o/--output` targets a non-canonical custom directory, skip repo-root maintenance and print a clear notice that the result is an ad-hoc export not integrated into repo-managed versions or the hub**
- [ ] **Step 5: When `--cache-only` is used without an explicit custom output, route output to a dedicated staging root and skip prune/integration behavior**
- [ ] **Step 6: Add a guard that refuses canonical publish when a same-slug legacy root project still exists, so one slug cannot be split across both roots**
- [ ] **Step 7: Make normal cache discovery consult the dedicated cache staging root in addition to published snapshots**
- [ ] **Step 8: Re-run dry-runs for canonical, custom-output, and cache-only cases and confirm the new behavior is correct**

### Task 5: Update `generate_versions.py`, `inject_version_switcher.py`, `fix_wiki_html.py`, and `retrofit_overview.py`

**Files:**
- Modify: `/mnt/disk1/zy/internal_wiki/generate_versions.py`
- Modify: `/mnt/disk1/zy/internal_wiki/inject_version_switcher.py`
- Modify: `/mnt/disk1/zy/internal_wiki/fix_wiki_html.py`
- Modify: `/mnt/disk1/zy/internal_wiki/retrofit_overview.py`
- Modify: `/mnt/disk1/zy/internal_wiki/tests/test_retrofit_overview.py`

- [ ] **Step 1: Add or update tests for explicit project-name resolution, mixed-layout discovery, helper-resolved manifest/version-switcher IO, and repo-relative logging where practical**
- [ ] **Step 2: Run the affected test subset and confirm failures capture the old root-level assumption**
- [ ] **Step 3: Replace direct root enumeration with shared helper calls in all four scripts**
- [ ] **Step 4: Make `generate_versions.py` and `inject_version_switcher.py` operate on the helper-resolved project directory during migration instead of assuming `wiki/<slug>` already exists**
- [ ] **Step 5: Keep diagnostics repo-relative so moved files print as `wiki/...` and unmoved files still print legacy paths accurately during cutover**
- [ ] **Step 6: Re-run the affected tests and confirm pass**
## Chunk 3: Physical Migration and Derived Artifacts

### Task 6: Create `wiki/` and move project-related directories

**Files:**
- Move: `/mnt/disk1/zy/internal_wiki/ai-hedge-fund`
- Move: `/mnt/disk1/zy/internal_wiki/claude-code`
- Move: `/mnt/disk1/zy/internal_wiki/claude-code_source`
- Move: `/mnt/disk1/zy/internal_wiki/gem5`
- Move: `/mnt/disk1/zy/internal_wiki/gpgpu-sim_distribution`
- Move: `/mnt/disk1/zy/internal_wiki/hermes-agent`
- Move: `/mnt/disk1/zy/internal_wiki/minimind`
- Move: `/mnt/disk1/zy/internal_wiki/oclgrind`
- Move: `/mnt/disk1/zy/internal_wiki/openclaw`

- [ ] **Step 1: Create `/mnt/disk1/zy/internal_wiki/wiki`**
- [ ] **Step 2: Move each approved project-related directory into `/mnt/disk1/zy/internal_wiki/wiki/` atomically, never leaving one project slug split across both roots**
- [ ] **Step 3: List `/mnt/disk1/zy/internal_wiki` and `/mnt/disk1/zy/internal_wiki/wiki` to confirm the new layout and absence of leftover project directories at the root**

### Task 7: Regenerate hub and per-project derived files

**Files:**
- Modify: `/mnt/disk1/zy/internal_wiki/index.html`
- Modify: `/mnt/disk1/zy/internal_wiki/wiki/*/versions.json`
- Modify: `/mnt/disk1/zy/internal_wiki/wiki/*/<timestamp>/index.html`

- [ ] **Step 1: Run `python3 /mnt/disk1/zy/internal_wiki/update_index.py`**
- [ ] **Step 2: Run `python3 /mnt/disk1/zy/internal_wiki/generate_versions.py`**
- [ ] **Step 3: Run `python3 /mnt/disk1/zy/internal_wiki/inject_version_switcher.py`**
- [ ] **Step 4: Run `python3 /mnt/disk1/zy/internal_wiki/fix_wiki_html.py --check`**
- [ ] **Step 5: Re-run `python3 /mnt/disk1/zy/internal_wiki/update_index.py` and confirm it refreshes cleanly without duplicate card insertion**

## Chunk 4: Verification

### Task 8: Run repository verification

**Files:**
- Review only: `/mnt/disk1/zy/internal_wiki/index.html`
- Review only: `/mnt/disk1/zy/internal_wiki/wiki/`

- [ ] **Step 1: Run the relevant test suite for touched Python files**
- [ ] **Step 2: Run `python3 /mnt/disk1/zy/internal_wiki/retrofit_overview.py --dry-run` to verify project discovery still works**
- [ ] **Step 3: Run `bash /mnt/disk1/zy/internal_wiki/.github/skills/wiki-generator/scripts/run_wiki_gen.sh --dry-run ...` against a small source and confirm output targets `wiki/...`, logs target `logs/`, and clones target `.git-clones/`**
- [ ] **Step 4: Start `python -m http.server 8080` from `/mnt/disk1/zy/internal_wiki` and open the hub**
- [ ] **Step 5: Click several cards and verify navigation lands under `wiki/...`**
- [ ] **Step 6: Open one versioned project page and verify the version switcher still changes versions correctly**

### Task 9: Final cleanup review

**Files:**
- Review only: `/mnt/disk1/zy/internal_wiki`

- [ ] **Step 1: Run `git status --short` and inspect the move set and script changes**
- [ ] **Step 2: Confirm no non-project operational directories were moved accidentally**
- [ ] **Step 3: Document any residual follow-up work if a second-pass naming cleanup is still desired**

Plan complete and saved to `/mnt/disk1/zy/internal_wiki/docs/superpowers/plans/2026-04-21-internal-wiki-projects-root-refactor.md`. Ready to execute.