# Wiki Project Overview Page (Click-to-Preview Hub)

**Status:** Draft
**Date:** 2026-04-17
**Scope:** `.github/skills/wiki-generator/` (new Overview Pass), repo-root retrofit script, nav injection helper
**Audience:** Maintainers of the internal-wiki skill and reviewers of the per-project wiki output
**Relationship to prior work:** Builds on `2026-04-17-wiki-generator-deeper-layered-redesign.md`. Consumes the `data-layer="primer"` and `data-layer="core-idea"` regions that redesign introduced, and the `_worklist.yaml` it produces. Adds no new requirements to those documents.

## 1. Problem Statement

Generated wikis today present content as a tree of pages: an L1 landing page with a deep-dive hub section, module sub-pages, and focus deep-dive pages. A visitor who wants a bird's-eye sense of "everything this project covers, and a quick explanation of each thing" must either:

- read the L1 landing page (high-level but omits focus-topic detail), or
- click through the deep-dive hub one focus page at a time (breaks flow, costs a navigation on every lookup).

There is no single page where the whole project's clarifying content is visible at once, with the ability to peek at any item's primer without leaving the page.

## 2. Goals

1. **Single-page bird's-eye view.** Per project, produce one page (`overview.html`) that shows every module and every focus topic as rich cards in a two-tier layout.
2. **Click-to-preview.** Clicking a card opens a modal containing that focus page's newcomer primer + 60-second core idea, with a link to the full page.
3. **Self-contained output.** `overview.html` is one static HTML file per project, with inlined CSS/JS, no JSON fetches, no external assets. Works offline and via `file://`.
4. **Retrofit coverage.** A one-shot Python script produces `overview.html` for every existing committed wiki, even those that predate the layered-redesign.
5. **Opt-out support.** Projects can skip overview generation via a `.no-overview` flag file.

### Non-goals

- Cross-project overview on the repo-top `index.html`. Out of scope; each project's overview stands alone.
- A separate JSON data layer consumable by other tools. Explicitly rejected in favor of one self-contained HTML file.
- Replacing the existing L1 landing `index.html`. The overview page is additive and linked from the top nav.
- Editorial hand-tuning UI for card summaries or tags. Summaries come from Copilot; corrections are made by re-running generation.
- Indexing `overview.html` in `search-index.json`. It is navigational, not source content.

## 3. Success Criteria

- Regenerating any project (`hermes-agent` is the smoke-test target) with the new pipeline produces a valid `overview.html` that passes Gate D.
- Modal opens on card click, closes on Esc / backdrop click, and "Read full page →" link navigates to the correct focus page.
- Retrofit script produces `overview.html` for all existing committed wikis (claude-code, claude-code_source, gem5, oclgrind, openclaw, minimind, ai-hedge-fund, gpgpu-sim_distribution, hermes-agent) without regenerating those wikis.
- The Overview top-nav link appears on `index.html` and every module `index.html` after injection, and is idempotent across reruns.
- Keyboard navigation (Tab / Enter / Esc) works. Mobile layout collapses to single column below 640px.

## 4. Architecture

### 4.1 Pipeline position

`overview.html` generation is a new stage that runs *after* the three-pass generation pipeline from the prior redesign:

```
Pass A (L0+L1 skeletons)   → Gate A
Pass B (focus pages)       → Gate B
Pass C (L2 sub-modules)    → Gate C
Overview Pass (this spec)  → Gate D
Nav-link injection         → (idempotent helper)
Existing post-processing (Phases 7–10)
```

Gate D is blocking for the generator; non-blocking (warn-and-continue) for the retrofit script.

### 4.2 Components

| Component | Location | Responsibility |
|---|---|---|
| Overview Pass prompt | `.github/skills/wiki-generator/overview_pass.md` | Copilot CLI prompt that reads finished focus pages and writes `overview.html`. |
| Orchestrator wiring | `.github/skills/wiki-generator/run_wiki_gen.sh` | Invokes Overview Pass after Gate C; runs Gate D; invokes nav injection. |
| Gate D | `.github/skills/wiki-generator/verify.sh --stage=D` | Structural checks on `overview.html`. |
| Retrofit script | `retrofit_overview.py` (repo root) | Runs the Overview Pass against already-committed wikis; discovers structure without `_worklist.yaml`. |
| Nav-link injector | `inject_overview_link.py` (repo root) | Idempotently adds `<a href="overview.html">Overview</a>` to the top nav of `index.html` and each module `index.html`. Reuses the pattern from `inject_version_switcher.py`. |
| Runtime artifact | `<project>/<version>/overview.html` | One self-contained file per project version. |

### 4.3 `overview.html` structure

```html
<!DOCTYPE html>
<html>
<head>
  <title>{project} — Overview</title>
  <style>/* inlined, ~100 lines */</style>
</head>
<body>
  <header>
    <h1>{project}</h1>
    <p class="tagline">{one-line project tagline}</p>
    <nav><a href="index.html">Home</a></nav>
  </header>
  <main>
    <section class="module" data-module-id="{slug}">
      <h2>{Module name}</h2>
      <p class="module-blurb">{one sentence}</p>
      <div class="card-grid">
        <article class="card"
                 tabindex="0"
                 role="button"
                 aria-haspopup="dialog"
                 data-href="{module}/{focus-slug}/index.html"
                 data-preview-html="{escaped primer+core-idea HTML}">
          <h3>{Focus topic title}</h3>
          <p class="summary">{1–2 sentence card summary}</p>
          <div class="tags">{tag1} · {tag2}</div>
          <div class="stats">{N} diagrams · {M} refs · {L} lines</div>
        </article>
        <!-- more cards -->
      </div>
    </section>
    <!-- more module sections -->
  </main>
  <dialog id="preview-modal">
    <div class="modal-body"></div>
    <footer>
      <a class="full-link" href="#">Read full page →</a>
      <button class="close">Close</button>
    </footer>
  </dialog>
  <script>/* ~40 lines, described in §4.4 */</script>
</body>
</html>
```

### 4.4 Runtime behavior (inlined JS)

- On DOMContentLoaded, attach a single delegated click handler on `<main>`.
- On click of `.card` (or Enter when focused): read `data-preview-html` and `data-href`, populate `#preview-modal .modal-body` via `innerHTML`, set `.full-link` href, call `dialog.showModal()`.
- On click outside `.modal-body` (backdrop), on Esc (native), or on `.close` button: `dialog.close()`.
- Fallback: if `typeof HTMLDialogElement === 'undefined'`, click handler navigates directly to `data-href`.

No external scripts. No fetch calls. Total inlined JS under 60 lines.

## 5. Overview Pass contract

### 5.1 Inputs

The orchestrator hands Copilot:

- `docs/_research/_worklist.yaml` (generator mode) OR a script-built equivalent structure (retrofit mode) enumerating `(module, focus-topic, href)` tuples.
- The HTML files for each focus page, to read their primer, core-idea, diagrams, and file refs.
- A **strict output template** matching §4.3 verbatim — Copilot fills slots, does not reshape structure.
- A **fixed tag vocabulary:** `core`, `api`, `internals`, `tutorial`, `reference`, `advanced`. No free-form tags permitted.

### 5.2 Per-card responsibilities

For each `(module, focus-topic)` pair, Copilot must:

1. Read the target focus page's HTML.
2. Write a **card summary** of 1–2 sentences. This is distinct from the primer — punchier, grid-appropriate. Not a verbatim copy of any primer paragraph.
3. Select 1–3 **tags** from the fixed vocabulary.
4. Report **stats** by counting exactly, not estimating:
   - `diagrams` = count of `<div class="mermaid">` occurrences.
   - `refs` = count of elements with `data-file-ref` attribute.
   - `lines` = count of top-level `<p>` and `<li>` elements in the main content region.
   The prompt explicitly instructs: *report the exact numbers you count; do not round or estimate*.
5. Copy the target page's `data-layer="primer"` and `data-layer="core-idea"` block HTML verbatim, concatenate, HTML-attribute-escape, and emit as `data-preview-html`.

### 5.3 Output

One file, written to the project wiki root: `overview.html`. No other side effects.

### 5.4 Fallback for pre-layered wikis (retrofit only)

When a focus page has no `data-layer="primer"` or `data-layer="core-idea"` regions:

- Use the first `<p>` under the page's `<main>` (or body if no main) as primer content.
- Use the next two `<p>` elements as core-idea content.
- Prepend a banner `<div class="retrofit-banner">This overview was retrofitted from a pre-layered wiki; previews may be abbreviated.</div>` inside the `data-preview-html` payload.
- Card summary, tags, and stats are produced normally by Copilot from whatever content is present.

## 6. Gate D (verify.sh)

New stage in `verify.sh`:

```
verify.sh --stage=D [--project=<path>]
```

Checks (all must pass; non-zero exit on any failure):

1. `overview.html` exists at the project wiki root.
2. It parses as well-formed HTML.
3. Exactly one `<section class="module">` per module listed in `_worklist.yaml` (generator mode) or per discovered module (retrofit mode).
4. Exactly one `<article class="card">` per `(module, focus-topic)` pair.
5. Each card has non-empty `data-href`, `data-preview-html`, `<h3>`, `.summary`, `.tags`, `.stats`.
6. Every `data-href` resolves to an existing file on disk.
7. `<dialog id="preview-modal">` and the inlined `<script>` block are present.
8. No placeholder strings: `TBD`, `TODO`, `FIXME`, `Lorem`, `TK`, `XXX`.
9. Card summaries are not byte-identical copies of the corresponding primer's first paragraph (enforces §5.2.2).

## 7. Retrofit script (`retrofit_overview.py`)

### 7.1 CLI

```
python retrofit_overview.py                 # all projects
python retrofit_overview.py <project>       # just one
python retrofit_overview.py --force         # regenerate even if overview.html exists
python retrofit_overview.py --dry-run       # list intended actions, do nothing
python retrofit_overview.py --confirm-each  # prompt before each Copilot call
```

### 7.2 Per-project flow

1. Resolve the project's **active version directory** by reading `<project>/versions.json` and selecting `current` (consistent with `launch_server.sh` and `update_index.py`).
2. **Skip conditions** (print reason, continue to next project):
   - `overview.html` exists in the active version directory and `--force` not set.
   - `.no-overview` flag file exists in the project root.
   - No focus pages discoverable (pre-focus-page wikis; retrofit has nothing to preview).
3. **Discover structure** (substitute for missing `_worklist.yaml`):
   - Parse the L1 `index.html` for the deep-dive hub grid; enumerate focus-page `href`s.
   - Group by parent directory to recover modules.
   - For each focus page, read `<h1>` as title and attempt `data-layer` extraction (fall back per §5.4).
4. Build an in-memory worklist equivalent and invoke the **same Overview Pass prompt** as the generator.
5. Run `verify.sh --stage=D`. On failure: log, keep the file on disk for inspection, increment failure counter, continue.
6. Invoke `inject_overview_link.py` against `index.html` and each module `index.html` in the project.

### 7.3 Cost control

- Before the first Copilot call, print estimated project count and prompt for confirmation.
- Subsequent projects proceed without prompting unless `--confirm-each`.
- Per-project stderr line with elapsed time and a running total.

### 7.4 Idempotency

- Re-running without `--force` is a no-op (skip condition 2a).
- Nav-link injection checks for an existing `overview.html` link before inserting.

## 8. Nav-link injection (`inject_overview_link.py`)

- Walks `index.html` and each `*/index.html` within the project.
- Locates the top `<nav>` (same target as `inject_version_switcher.py`).
- If a link with `href="overview.html"` (or `href="../overview.html"`, etc., adjusted per depth) already exists, skip.
- Otherwise, insert `<a href="{relative}/overview.html">Overview</a>` at the end of the nav.
- Run **after** `inject_version_switcher.py` to avoid ordering bugs.

## 9. Error handling

| Failure | Generator mode | Retrofit mode |
|---|---|---|
| Copilot timeout / non-zero exit | Abort pipeline, preserve partials. | Log, skip project, continue batch. |
| Gate D failure | Blocking. | Warn, keep `overview.html` for inspection, continue batch. |
| `data-preview-html` attribute exceeds 64KB | Truncate at the primer/core-idea boundary; append `<p><em>Preview truncated — see full page.</em></p>`. Log warning. Does not fail Gate D. |
| `<dialog>` unsupported in browser | JS feature-detects and falls back to direct navigation to `data-href`. |
| Malformed source HTML breaks primer extraction | Generator: Gate D fails (source must be clean by this stage). Retrofit: falls back per §5.4. |
| Nav target missing `<nav>` element | Insert a minimal `<nav>` at the top of `<body>`. |

## 10. Testing

### 10.1 Unit tests (`tests/test_overview.py`)

- HTML-attribute escaping round-trips realistic primer content (code blocks, embedded Mermaid source, nested quotes, Unicode).
- `verify.sh --stage=D` fixtures: one golden `overview.html` that passes, plus minimally-mutated copies that must each fail (missing card, empty `data-href`, placeholder text, summary identical to primer).
- Retrofit structure discovery against a fixture wiki with no `_worklist.yaml`.
- Truncation logic for oversized `data-preview-html`.

### 10.2 Integration test

Smoke-regenerate the smallest project (`oclgrind` or equivalent) end-to-end in CI. Assertions:
- `overview.html` exists at expected path.
- Headless Playwright: opens page, clicks first card, asserts `<dialog>` is open with non-empty body, asserts "Read full page →" href matches the card's `data-href`.

### 10.3 Manual QA checklist (ships in spec)

- [ ] Tab moves focus through cards in document order.
- [ ] Enter on focused card opens modal.
- [ ] Esc closes modal.
- [ ] Click on backdrop closes modal.
- [ ] Mobile (≤640px): grid collapses to single column; modal fills viewport.
- [ ] Screen reader announces card as button and modal as dialog.
- [ ] "Read full page →" navigates correctly.

## 11. Edge cases

- **Single-module projects:** render as one `<section class="module">`; no special case.
- **Zero focus pages:** retrofit skips; generator-side Gate D fails (existing spec already requires focus pages for eligible projects).
- **>50 focus pages:** two-tier grid handles naturally; future-safe for lazy-loading thumbnails if added later.
- **Version switcher interaction:** `overview.html` lives inside a versioned directory and is treated like any other versioned page by the existing switcher. Nav injection runs strictly after `inject_version_switcher.py`.
- **`search-index.json`:** `overview.html` is explicitly excluded from indexing — it is navigational, not source content. Post-processing step must skip it by filename.

## 12. Backward compatibility

- Existing committed wikis render unchanged until `retrofit_overview.py` is run against them.
- `retrofit_overview.py` modifies only: adds `overview.html`, edits `index.html` nav (idempotent insert).
- A `.no-overview` flag file in a project root permanently opts it out of both generator-mode and retrofit-mode overview creation.

## 13. Open questions

None at spec-finalization time. All choices from brainstorming are reflected above.
