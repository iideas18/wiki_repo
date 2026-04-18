# Overview Pass — Generate `overview.html`

## Inputs you are given
- `{{PROJECT_NAME}}`: the project display name.
- `{{PROJECT_TAGLINE}}`: a one-line tagline (already written).
- `{{WORKLIST_JSON}}`: a JSON object mapping each module slug to a list of
  focus-page entries with `title`, `href`, and the preview HTML you must
  embed verbatim as `data-preview-html`.
- `{{STATS_JSON}}`: a JSON object keyed by `href`, each value giving the exact
  integer counts `{ "diagrams": N, "refs": M, "lines": L }`. You MUST use these
  numbers unchanged.
- `{{TEMPLATE}}`: the HTML template shell. Fill the `{{MODULE_SECTIONS}}` slot
  and leave the rest exactly as-is.

## Card responsibilities (per focus-page entry)
For each entry in the worklist, emit one `<article class="card">` with:

1. `data-href="{href}"` exactly as given.
2. `data-preview-html="{preview_html}"` exactly as given, already HTML-
   attribute-escaped. Do not re-escape or modify.
3. `<h3>` containing the entry's `title`.
4. `<p class="summary">`: a 1–2 sentence summary of the focus topic written by
   you from the preview content. This summary MUST NOT be a byte-identical
   copy of any paragraph already inside `data-preview-html`. Make it punchier
   and grid-appropriate.
5. `<div class="tags">`: 1–3 tags, dot-separated, chosen ONLY from this fixed
   vocabulary: `core`, `api`, `internals`, `tutorial`, `reference`, `advanced`.
   No other tags are permitted.
6. `<div class="stats">`: render the stats from `{{STATS_JSON}}` as
   `"{diagrams} diagrams · {refs} refs · {lines} lines"`. Use the exact
   numbers — do not recount, round, or estimate.

## Module section responsibilities
For each module, emit one `<section class="module" data-module-id="{slug}">`
with:
- `<h2>` containing a human module name (title-case the slug if no better name
  is evident from the entries).
- `<p class="module-blurb">`: one sentence summarizing the module, written by
  you from its entries.
- A single `<div class="card-grid">` containing the module's cards in the
  worklist order.

## Hard rules
- Output ONLY the filled-in `{{TEMPLATE}}`. No commentary, no markdown fences.
- Every worklist entry MUST produce exactly one card. Never omit, never add.
- Never write `TBD`, `TODO`, `FIXME`, `Lorem`, `TK`, or `XXX`.
- Never invent stats. Use `{{STATS_JSON}}` verbatim.
