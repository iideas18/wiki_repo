# Wiki-Generator Redesign: Deeper, Layered, Gated

**Status:** Draft
**Date:** 2026-04-17
**Scope:** `.github/skills/wiki-generator/` and repo-level post-processing tools
**Audience:** Maintainers of the internal-wiki skill + reviewers

## 1. Problem Statement

The `wiki-generator` skill produces HTML wikis from source repositories. Users (most recently on the `hermes-agent` wiki) report that generated output is:

- **Shallow.** Pages stop at overview depth. Focus deep-dive sub-pages — the most valuable content according to the skill itself — are routinely not generated at all. L2 sub-module pages are skipped even on 3-level projects.
- **Abstract.** Pages hit minimum line counts but content reads like a template fill-in. Narrated walkthroughs describe generic "Step 1 → Step 2" flows instead of tracing real functions with real file:line references. Alternatives-comparison tables and annotated code walkthroughs — both required by the skill — are frequently absent or reduced to placeholders.
- **One-size-fits-all for the reader.** A newcomer and a senior engineer read the same dense prose. There is no structural distinction between onboarding content (analogy, primer, glossary) and expert content (invariants, call graph, file:line index).

### Root cause

The skill runs as a **single prompt invocation** that asks an agent to execute Phase 1 research, Phases 2–10 generation, and all post-processing. Because the required-elements list is long and nothing enforces completion of later phases, agents satisfice: they hit the L1 overview minimum and stop. Required focus-page and L2 phases are described in prose but not enforced by any executable gate.

Additionally, the existing templates list "intro box" and "analogy" as required elements, but without dedicated structural regions those elements compete with a dozen other required sections and get minimized or inlined. Layered content for different reader skill levels is aspirational, not structural.

## 2. Goals

1. **Force depth.** Focus deep-dive pages and L2 sub-module pages must be generated whenever the depth-detection logic calls for them. Completion is verified by an executable check, not prose rule.
2. **Force concreteness.** Generated pages must cite real file:line references, contain real code in annotated walkthroughs, and include real alternatives with tradeoff tables. Verified mechanically.
3. **Support layered reading.** Every non-hub page must have four clearly separated content regions: newcomer primer, 60-second core idea, in-depth analysis, expert appendix. A per-visitor reading-level toggle shows or hides regions.
4. **Cross-link terminology.** A per-project glossary, auto-built from page primers, powers hover-tooltips across the project.
5. **Backward compatibility.** Existing committed wikis continue to render with no visual or functional change until their authors choose to regenerate.

### Non-goals

- Changing the hub `index.html` landing page.
- Changing `update_index.py`, `generate_versions.py`, `inject_version_switcher.py`.
- Cross-project glossary merging.
- Manual glossary-editing UI.
- Per-user preferences beyond level + theme.
- Replacing Copilot CLI as the generation engine.

## 3. Success Criteria

- Regenerating `hermes-agent` with the new skill produces a wiki with:
  - ≥ 3 focus deep-dive pages per L1 module
  - Every focus page ≥ 500 lines with ≥ 2 Mermaid diagrams, ≥ 3 file:line refs, Alternatives Comparison table, 8+-step Mechanism Trace
  - Every L1/L2/focus page containing all four `data-layer` regions
  - A working reading-level toggle persisted via `localStorage`
  - A populated `glossary.json` with ≥ 10 terms and tooltips active on body prose
- All gates in `verify.sh` pass (non-zero exit on any violation).
- Existing wikis (claude-code, gem5, oclgrind, openclaw, minimind, ai-hedge-fund, gpgpu-sim_distribution, claude-code_source) open and render correctly without regeneration, no JavaScript errors in console.

## 4. Architecture

### 4.1 Three-Pass Generation Pipeline

The single-pass prompt is replaced with an orchestrator (`run_wiki_gen.sh`) that invokes Copilot three times, with a verification gate between each pass.

```
Phase 1 — Research (tightened contract)
   • Phase 1A broad survey   → docs/_research/01-survey.md
   • Phase 1B per-module deep→ docs/_research/<module>_deep.md
   • Phase 1C synthesis      → docs/_research/_synthesis.md
   • Worklist (NEW)          → docs/_research/_worklist.yaml
         (3–5 focus topics per module, machine-readable)
   ↓
Pass A — L0 + L1 skeletons
   • Hero, architecture diagram, narrated walkthrough
   • Deep-dive hub = card-grid PLACEHOLDER built from _worklist.yaml
   • Every card href points at <slug>/index.html (file not yet created)
   ↓ GATE A (verify.sh --stage=A) — blocking
   ↓
Pass B — Focus pages (mandatory, one per worklist entry)
   • For each (module, topic) in _worklist.yaml → one focus page
   • Each page must cite ≥ 3 file:line references from research
   ↓ GATE B (verify.sh --stage=B) — blocking
   ↓
Pass C — L2 sub-module pages (3-level projects only)
   • Each L2 has its own focus children
   ↓ GATE C (verify.sh --stage=C) — blocking
   ↓
Phase 7–10 — Post-processing (unchanged + new glossary build)
   • search-index.json, nav-tree, auto-crosslinks, tooltips
   • build-glossary.py (NEW)  → glossary.json
   • fix_wiki_html.py, update_index.py
   ↓ FINAL GATE (verify.sh — full)
```

#### Why this shape

- **Gates bite between passes.** Gate failures stop the pipeline. Skipped work becomes impossible to ignore. This directly addresses the "agent skipped Phase 6" failure.
- **Small focused prompts outperform one large prompt.** Pass A has one job (L1 skeletons). Pass B has one job (focus pages from worklist). Pass C has one job (L2s). Agents do each better than they do "all of it at once".
- **Worklist is the contract between research and generation.** Phase 1B previously produced prose; now it produces prose *plus* a YAML worklist. Pass B iterates the worklist deterministically — one focus page per entry. No judgment calls about which topics to include.
- **Idempotency.** Re-running Pass B only regenerates focus pages that are missing or below threshold, enabling targeted retry.
- **`--legacy` single-pass mode preserved** for users who want the old behavior on tiny projects.

### 4.2 Layered Template Structure

Every non-L0 template (`l1-template.html`, `l2-template.html`, `focus-template.html`) is restructured around four required `<section>` regions. The L0 hub template gets a lighter primer but keeps its existing shape.

```html
<main>
  <section data-layer="primer" class="layer-primer" aria-label="Newcomer primer">
    <h2 id="primer">In Plain English</h2>
    <div class="primer-grid">
      <div class="primer-analogy">
        <!-- One vivid, concrete analogy. 80-150 words. Required. -->
      </div>
      <div class="primer-diagram">
        <!-- Minimalist mermaid: 3-5 nodes, no subgraphs. Required. -->
      </div>
    </div>
    <dl class="primer-glossary">
      <!-- 3-5 key terms, inline definitions. Required. -->
    </dl>
    <aside class="primer-prereq">
      <!-- Optional: "Before reading further" links. -->
    </aside>
  </section>

  <section data-layer="core" class="layer-core">
    <h2 id="core">The Core Idea</h2>
    <!-- One paragraph (100-200 words) + one architecture diagram.
         Answers: what, why, key insight. Required. -->
  </section>

  <section data-layer="deep" class="layer-deep">
    <!-- Existing required sections: Why This Exists, Design Decisions,
         Narrated Walkthrough, Algorithm Spotlight, Deep-Dive card grid,
         What Could Go Wrong, Performance Profile, etc. -->
  </section>

  <details data-layer="expert" class="layer-expert">
    <summary>Expert Appendix — invariants, call graph, file:line index</summary>
    <section>
      <h3>Invariants</h3>
      <h3>Call Graph</h3>       <!-- mermaid -->
      <h3>File:Line Index</h3>  <!-- 15-30 row table -->
      <h3>Performance Numbers</h3>
    </section>
  </details>
</main>
```

#### Layer semantics

| Layer | Audience | Default visibility (Engineer mode) | Content |
|---|---|---|---|
| `primer` | Newcomer | Visible | Analogy, 3-5 node mini-diagram, 3-5 term glossary |
| `core` | Everyone | Visible | One-paragraph explanation + one architecture diagram |
| `deep` | Engineer | Visible | All current required content (80%+ of the page) |
| `expert` | Senior | Folded `<details>` | Invariants, call graph, file:line table, perf numbers |

#### Verification

`verify.sh` greps for `data-layer="primer"`, `"core"`, `"deep"`, `"expert"` on every L1/L2/focus page. All four required. Primer sub-elements (`.primer-analogy`, `.primer-diagram`, `.primer-glossary` with ≥ 3 `<dt>`) are independently checked.

### 4.3 Reading-Level Toggle

A persistent control next to the existing theme toggle, with three levels.

- **localStorage key:** `neutra-ip-level` (mirrors `neutra-ip-theme` naming)
- **Values:** `newcomer` | `engineer` (default) | `expert`
- **Applied as** `<html data-level="…">` via synchronous inline script in `<head>` (avoids flash)

CSS controls region visibility via attribute selectors:

```css
html[data-level="newcomer"] [data-layer="expert"] { display: none; }
html[data-level="newcomer"] [data-layer="deep"] > :not(h2) { display: none; }
html[data-level="newcomer"] [data-layer="deep"]::after {
  content: "▶ Switch to Engineer mode for in-depth analysis";
}

html[data-level="engineer"] [data-layer="expert"] > summary { /* collapsed */ }

html[data-level="expert"] [data-layer="primer"] { /* collapsed into <details> */ }
html[data-level="expert"] [data-layer="expert"] { /* auto-expanded */ }
```

On toggle, a small JS snippet updates `<html data-level>` and rewrites open/closed state of layer `<details>` elements. No page reload.

**Progressive enhancement:** JS disabled → defaults to Engineer view, all regions visible. The `<details>` elements still work without JS.

### 4.4 Project-Wide Glossary

One `glossary.json` per project, co-located with `versions.json` and `search-index.json`.

Schema:

```json
{
  "terms": {
    "shadow-memory": {
      "term": "Shadow Memory",
      "short": "Parallel memory region tracking metadata about the primary address space.",
      "long": "Longer explanation, 2-3 sentences…",
      "see_also": ["memcheck", "race-detection"],
      "defined_in": "oclgrind_doc/memcheck/index.html#shadow-memory"
    }
  }
}
```

**Build:** `scripts/build-glossary.py` runs in Phase 7. Scrapes all `<dt>` inside `.primer-glossary` on every generated page, deduplicates by slug (lowercased, hyphenated), emits JSON.

**Consume:** Each page loads `../glossary.json` (or `../../glossary.json` for L2/focus) via inline script. Terms appearing in body prose get wrapped as `<span class="gloss" data-term="…">term</span>` on first occurrence per `<section>`. Hover/tap → tooltip with `short`. Click → jump to `defined_in`.

**Exclusions:** Linker skips `<code>`, `<pre>`, `<h1>-<h6>`, `<a>`, and anything inside `[data-no-gloss]`. Disabled in Expert mode (assumed audience knows terms).

### 4.5 Verification as Contract

`verify.sh` is the executable contract for everything above.

- Rewritten as thin shell wrapper. Real checks live in `scripts/verify/` as Python modules, one per gate.
- Each check emits `Violation{gate, check_id, file, message, fix_hint}`.
- Modes: `verify.sh <project>` (full), `--stage=A|B|C`, `--worklist`, `--json`.

Gate checks enumerated in §5.3.

## 5. Components

### 5.1 Files Added

| Path | Purpose |
|---|---|
| `.github/skills/wiki-generator/prompts/phase-1-research.md` | Research prompt with YAML worklist output contract |
| `.github/skills/wiki-generator/prompts/pass-a.md` | L0 + L1 skeleton prompt |
| `.github/skills/wiki-generator/prompts/pass-b.md` | Focus page prompt (reads worklist) |
| `.github/skills/wiki-generator/prompts/pass-c.md` | L2 page prompt |
| `.github/skills/wiki-generator/resources/_reading-level.js` | Inline-included toggle logic |
| `.github/skills/wiki-generator/resources/_glossary-linker.js` | Inline-included term-wrapping logic |
| `.github/skills/wiki-generator/scripts/build-glossary.py` | Scrape primer `<dt>` → `glossary.json` |
| `.github/skills/wiki-generator/scripts/worklist-validate.py` | Validate `_worklist.yaml` vs. schema |
| `.github/skills/wiki-generator/scripts/verify/violation.py` | `Violation` dataclass |
| `.github/skills/wiki-generator/scripts/verify/check_gate_a.py` | Gate A checks |
| `.github/skills/wiki-generator/scripts/verify/check_gate_b.py` | Gate B checks |
| `.github/skills/wiki-generator/scripts/verify/check_gate_c.py` | Gate C checks |
| `.github/skills/wiki-generator/scripts/verify/check_final.py` | Final gate checks |
| `.github/skills/wiki-generator/scripts/verify/check_worklist.py` | Worklist schema check |
| `.github/skills/wiki-generator/scripts/verify/schema_worklist.json` | JSON schema for worklist |

### 5.2 Files Modified

| Path | Change |
|---|---|
| `.github/skills/wiki-generator/SKILL.md` | Procedure rewritten for 3-pass gate flow; layered regions documented; gate reference table |
| `.github/skills/wiki-generator/README.md` | Updated quickstart |
| `.github/skills/wiki-generator/resources/l0-template.html` | Lighter primer; reading-level toggle header |
| `.github/skills/wiki-generator/resources/l1-template.html` | Four layer regions; toggle; glossary linker |
| `.github/skills/wiki-generator/resources/l2-template.html` | Same as L1 |
| `.github/skills/wiki-generator/resources/focus-template.html` | Same as L1; primer especially important |
| `.github/skills/wiki-generator/resources/_shared-css.txt` | Layer visibility CSS; `.gloss`, `.reading-level-toggle`, `.primer-*` classes |
| `.github/skills/wiki-generator/scripts/run_wiki_gen.sh` | Orchestrator: research → Pass A → Gate A → Pass B → Gate B → Pass C → Gate C → Phase 7–10 → Final |
| `.github/skills/wiki-generator/scripts/verify.sh` | Thin dispatcher to `scripts/verify/*.py` |
| `fix_wiki_html.py` | New rules: warn if any `data-layer` region missing, warn if toggle HTML or init scripts missing |

### 5.3 Gate Checks

**Gate A — after L1 skeletons**

| # | Check |
|---|---|
| A1 | Every module in worklist has L1 `index.html` (file exists) |
| A2 | Every L1 ≥ minimum line count (400 for 3-level L1, 350 for flat) |
| A3 | Every L1 has all four `data-layer` regions |
| A4 | Every L1 has `.primer-analogy`, `.primer-diagram` (mermaid block), `.primer-glossary` with ≥ 3 `<dt>` |
| A5 | Every L1 deep-dive card-grid has exactly N cards matching worklist entries |
| A6 | Every L1 has reading-level toggle HTML + inline init script |
| A7 | No placeholder text (`\bTODO\b|\bFIXME\b|\blorem ipsum\b|to be filled`) |

**Gate B — after focus pages**

| # | Check |
|---|---|
| B1 | Every card-grid href resolves to a real file |
| B2 | Every focus page ≥ 500 lines |
| B3 | Every focus page has all four `data-layer` regions |
| B4 | Every focus page has ≥ 2 Mermaid diagrams |
| B5 | Every focus page cites ≥ 3 file:line refs (regex `[\w./]+\.(c|cpp|h|py|ts|js|go|rs):\d+`) |
| B6 | Every focus page has **Alternatives Comparison** table (≥ 2 alternatives) |
| B7 | Every focus page has **Step-by-Step Mechanism Trace** with ≥ 8 `.code-walk .step` elements |
| B8 | Every focus page has **Failure Recovery** section (id `failure-recovery`) |
| B9 | No placeholder text |
| B10 | `<meta name="wiki-focus-parent">` points at real file |

**Gate C — after L2 pages (3-level only)**

| # | Check |
|---|---|
| C1 | Every L2 has its own card-grid with ≥ 3 focus children |
| C2 | Every L2 has Annotated Code Walkthrough with real code (not pseudocode; grep for `language-` class on `<code>` inside `.code-walk`) |
| C3 | Breadcrumbs resolve up to L1 and L0 |
| C4 | L2 checks A2–A7 and B1 scoped to `<module>/<submod>/` tree |

**Final gate — after Phase 7–10**

| # | Check |
|---|---|
| F1 | `search-index.json` exists and indexes every page |
| F2 | `glossary.json` exists with ≥ 10 terms |
| F3 | Every page loads `glossary.json` (script tag present) |
| F4 | `versions.json` exists and lists current snapshot |
| F5 | Version-switcher injected on every `index.html` |
| F6 | No broken internal links across entire tree |
| F7 | All Mermaid blocks save `data-source` before first `mermaid.run()` |
| F8 | Every page references both `neutra-ip-theme` and `neutra-ip-level` |

All gates fail hard (non-zero exit). No "soft warnings" — if a check is worth having, it's worth enforcing.

## 6. Data Flow

### 6.1 Worklist Schema

`docs/_research/_worklist.yaml`:

```yaml
version: 1
project: hermes-agent
depth: 3                     # 1 | 2 | 3
modules:
  - slug: tools_doc
    path: docs/tools_doc/
    focus_topics:
      - slug: terminal-execution
        title: "Terminal Command Execution"
        problem: "How tool calls are dispatched to shell subprocess with safety guards."
        files:
          - src/tools/terminal.ts:45-120
          - src/tools/terminal.ts:180-210
        alternatives:
          - "Direct exec() without sandbox"
          - "Docker container isolation"
      - slug: file-operations
        title: "File Read/Write Safety"
        problem: "…"
        files: [...]
        alternatives: [...]
```

Schema enforced by `scripts/verify/schema_worklist.json`. `worklist-validate.py` runs between Phase 1 and Pass A.

### 6.2 Page → Glossary → Page

1. Authors write primer glossaries inline as `<dl class="primer-glossary"><dt>Term</dt><dd>Definition</dd></dl>` on each page.
2. `build-glossary.py` scrapes all primer `<dt>`/`<dd>` pairs post-generation, deduplicates by slug, records first-defining page.
3. Each page loads `glossary.json` at runtime; linker wraps matching terms in body prose.
4. Clicking a wrapped term jumps to the first-defining page's primer anchor.

### 6.3 Toggle State

Single key `neutra-ip-level` in `localStorage`. Applied synchronously in `<head>`:

```html
<script>(function(){
  var l = localStorage.getItem('neutra-ip-level') || 'engineer';
  document.documentElement.setAttribute('data-level', l);
})();</script>
```

User clicks toggle → update `localStorage` + `data-level` attribute → CSS handles the rest. No re-render.

## 7. Error Handling

- **Pass fails a gate:** `run_wiki_gen.sh` exits non-zero, prints violations grouped by file with fix hints. User/agent addresses violations and re-runs the failed pass. Targeted retry with `verify.sh --stage=B --json` output can re-scope the prompt to only failing files.
- **`glossary.json` 404:** Glossary linker fetches, catches, silently skips wrapping. Page remains fully functional.
- **JS disabled:** Reading-level toggle is unreachable; all regions visible (Engineer default). `<details>` elements still work as folded/unfolded via browser's native behavior.
- **Invalid worklist:** `worklist-validate.py` fails loud before Pass A. User fixes Phase 1 output or re-runs research.
- **Mermaid render failure on toggle:** Unchanged from current behavior — source restored from `data-source`, re-initialized with new theme.

## 8. Testing Plan

| Component | Test |
|---|---|
| Worklist schema | `worklist-validate.py` on pilot-generated worklist |
| Gate A | Delete `data-layer="primer"` from an L1, verify Gate A fails with `A3` violation pointing at the file |
| Gate B | Point a card-grid href at a non-existent file, verify `B1` catches it; remove a focus page's Alternatives section, verify `B6` catches it |
| Gate C | Remove an L2's card-grid, verify `C1` catches it |
| Final | Empty `glossary.json`, verify `F2` catches it |
| Reading-level toggle | Manual: click each mode, verify regions show/hide; reload, verify persistence; test with JS disabled |
| Glossary linker | Manual: hover wrapped terms, verify tooltip + click-through; verify `<code>`/`<pre>`/`<h*>` exclusion |
| Backward compat | Open `claude-code/`, `gem5/`, etc. unregenerated, verify no JS errors, correct rendering |
| Theme × level interaction | Toggle both in both orders, verify no visual conflicts |

Pilot validation: regenerate `minimind` (smallest repo, fastest feedback) end-to-end. If satisfactory, regenerate `hermes-agent` as the primary validation.

## 9. Rollout

1. Implement skill changes. Do not regenerate any existing wiki yet.
2. Run pilot: `bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh -s /mnt/disk1/zy/internal_wiki/minimind/.source`. Verify all gates pass, manual review of output quality. Iterate on prompts/gates if needed.
3. Regenerate `hermes-agent` into a fresh timestamp snapshot under `hermes-agent/<new_timestamp>/`. Preserve the existing `20260415_111700/` snapshot. Use the version switcher to A/B compare.
4. Document migration in SKILL.md. Do not auto-migrate other wikis.

## 10. YAGNI / Out of Scope

- Cross-project glossary (scoped to per-project only).
- Manual glossary curation UI (auto-generated only).
- Font-size / code-theme per-user preferences.
- Changes to `update_index.py`, `generate_versions.py`, `inject_version_switcher.py`, or the hub `index.html`.
- Replacing Copilot CLI as the generation engine.
- Soft-gate variants — all gates are hard fails.

## 11. Open Questions

None blocking implementation. Design choices confirmed with user:
- Pipeline shape (3 passes + gates): approved
- Four-layer template structure: approved
- Reading-level toggle (3 modes, engineer default) + per-project glossary: approved
- Hard gates throughout: approved
- Pilot on minimind, then hermes-agent: approved

## 12. References

- Existing skill: `.github/skills/wiki-generator/SKILL.md` (1200 lines, the current single-pass procedure)
- Existing templates: `.github/skills/wiki-generator/resources/{l0,l1,l2,focus}-template.html`
- Existing verifier: `.github/skills/wiki-generator/scripts/verify.sh`
- Example deficient output: `hermes-agent/20260415_111700/` (triggered this redesign)
- Post-processing tools: `fix_wiki_html.py`, `update_index.py`, `generate_versions.py`, `inject_version_switcher.py` at repo root
