---
name: wiki-generator
description: "Generate self-contained HTML wiki pages with Mermaid diagrams for a source code project or module. Use when asked to 'create a wiki', 'generate wiki for this project', 'document this module', 'create HTML docs for this folder', 'wiki this codebase', or 'generate developer guide'. Automatically detects 1–3 level depth: a single page for flat modules, a two-level overview + deep-dives for modules with sub-directories, or a three-level project hub + module overviews + sub-module deep-dives for entire projects. Produces deep, narrative-style documentation that explains WHY code is designed the way it is — not just WHAT it does. Includes design rationale analysis, algorithm deep-dives, alternatives comparison, annotated code walkthroughs, cross-module connection diagrams, and learning aids. Supports dark/light theme toggle, syntax highlighting, and Mermaid diagrams."
argument-hint: "Path and optional language (e.g., 'src/core C++', './ Python', 'backend/')"
---

# Wiki Generator

Generate self-contained HTML wiki pages for any source code project or module, with adaptive 1–3 level depth. Each wiki reads like **a senior engineer explaining the codebase to a new team member** — not just cataloging files and classes, but explaining **why** the code is designed the way it is, what alternatives existed, and what tradeoffs were made.

## When to Use

- Create a wiki for an entire project or a single module
- Clarify project structure with multi-level navigation (project hub → module overview → sub-module deep-dive)
- Create visual architecture pages with Mermaid diagrams
- Produce browsable HTML wiki that works offline (file:// protocol)
- Deeply understand WHY code is designed a certain way — design rationale, alternatives analysis, algorithm deep-dives
- Onboard developers or learners with analogies, walkthroughs, and annotated code

## Adaptive Depth — 1, 2, or 3 Levels

The number of wiki levels depends on the project's structure. **Detect this automatically in Phase 1**, don't assume a fixed depth.

### How to Detect Depth

```bash
# Count sub-directories with source files
find <target>/ -mindepth 1 -maxdepth 1 -type d | while read d; do
  count=$(find "$d" -name '*.h' -o -name '*.cc' -o -name '*.cpp' -o -name '*.py' | head -1)
  [ -n "$count" ] && echo "$d"
done
```

Then check if those sub-directories themselves have meaningful sub-sub-directories:

```bash
# Check if any sub-modules have their own sub-modules
for d in <target>/*/; do
  subs=$(find "$d" -mindepth 1 -maxdepth 1 -type d | while read sd; do
    count=$(find "$sd" -name '*.h' -o -name '*.cc' -o -name '*.cpp' -o -name '*.py' | head -1)
    [ -n "$count" ] && echo "$sd"
  done | wc -l)
  echo "$subs sub-dirs in $(basename $d)"
done
```

### Depth Decision Matrix

| Condition | Depth | Structure |
|-----------|-------|-----------|
| Target dir has source files but NO sub-module dirs (or only 1-2 trivial ones) | **1-level** | Single page with everything |
| Target dir has 3+ sub-module dirs, each with source files, but sub-modules have NO further sub-dirs | **2-level** | L1 overview + L2 per sub-module |
| Target dir has 3+ sub-module dirs AND those sub-modules have their own sub-dirs with source files | **3-level** | L0 project hub + L1 per module + L2 per sub-module |

### Output Structure — by Depth

**1-Level** (flat module):
```
docs/
  <module>/index.html        ← Single comprehensive page (combines L1+L2 content)
```

**2-Level** (standard module):
```
docs/
  <module>_doc/
    index.html               ← L1: overview + sub-module cards
    <submod1>/index.html     ← L2: deep-dive page
    <submod1>/<topic>/index.html  ← Focus: topic deep-dive
    <submod2>/index.html
    ...
```

**3-Level** (multi-module project):
```
docs/
  search.html                ← Global search page
  search-index.json          ← Search index
  index.html                 ← L0: project hub + module cards
  <moduleA>_doc/
    index.html               ← L1: module overview + sub-module cards
    <submod1>/index.html     ← L2: deep-dive page
    <submod1>/<topic>/index.html  ← Focus: topic deep-dive
    ...
  <moduleB>_doc/
    index.html               ← L1: module overview
    ...
  <moduleC>/index.html       ← L1: flat module (no sub-modules)
```

**Rule**: Maximum 3 structural levels (L0 → L1 → L2). If a topic on a page deserves deeper exploration, create a **focus page** (not a structural L3) — a dedicated deep-dive page linked from the parent.

### Template Selection by Level

| Level | Template | Used When |
|-------|----------|-----------|
| L0 | [l0-template.html](./resources/l0-template.html) | 3-level only: project root hub |
| L1 | [l1-template.html](./resources/l1-template.html) | 2-level and 3-level: module overview with sub-module cards |
| L2 | [l2-template.html](./resources/l2-template.html) | 2-level and 3-level: sub-module deep-dive |
| L1-flat | [l1-template.html](./resources/l1-template.html) (expanded) | 1-level only: single page combining overview + deep-dive |
| Search | [search-template.html](./resources/search-template.html) | All depths: global full-text search page |
| Focus | [focus-template.html](./resources/focus-template.html) | Deep-dives: dedicated analysis of a specific topic |

---

## Procedure

## Hard Rules

- **Copilot CLI shell safety** — The Copilot CLI sandbox blocks commands with nested command substitution, indirect expansion, or process substitution. These patterns will be rejected:
  - `$(command_inside_string)` inside an `echo` argument is BLOCKED
  - `-exec sh -c '...' _ {} \;` compound exec patterns are BLOCKED
  - `$(...)` nested inside `$(...)` is BLOCKED
  
  **Safe alternatives:**
  - Split into separate commands: `COUNT=$(wc -l < file)` then `echo "count: $COUNT"`
  - Use `find ... -exec wc -l {} +` (no nested `sh -c`)
  - Use `xargs` instead of `-exec sh -c`
  - Use Python one-liners: `python3 -c "import os; ..."`
  - Pipe chains are fine: `cat file | sed ... | wc -l`

- Never compress or minify generated HTML. Keep readable multi-line formatting.
- For focus pages, always start from the full [focus-template.html](./resources/focus-template.html) scaffold.
- **All deep-dives must be sub-pages.** Never leave deep-dive content inline on parent pages. Extract each topic into its own focus sub-page. Parent shows only card-grid hub.
- **Mermaid light-theme compatibility** — Do NOT use hardcoded dark-palette colors in Mermaid `style` directives.
- **Unified localStorage theme key** — ALL wiki pages MUST use `neutra-ip-theme`. No variants.
- **Mermaid data-source saving is mandatory** — Before the first `mermaid.run()`, save original source text to `data-source` attribute.
- **Mermaid theme toggle must restore source** — On theme change: (1) restore from `data-source`, (2) remove `data-processed`, (3) `mermaid.initialize()` with new theme, (4) `mermaid.run()`.
- **Mermaid syntax hygiene** — Avoid bare double quotes in sequenceDiagram. Use `<br/>` for line breaks in notes. Avoid `===` in note text. Use ASCII `->` not Unicode arrows.

## Writing Voice & Depth Philosophy

**CRITICAL: This is the most important section.** Every page generated by this skill must follow these depth and voice guidelines. Shallow, catalog-style documentation is the #1 failure mode.

### Narrative Voice

The wiki reads like a **senior engineer writing a technical blog post** for a new team member joining the project. It is:

- **Conversational but precise** — uses "you" and "we", but never vague about technical details
- **Opinionated with evidence** — states design quality judgments backed by code evidence: *"This is a well-designed abstraction because X"* rather than just *"This does X"*
- **Proactive about WHY** — every section must answer WHY, not just WHAT or HOW. If the code doesn't comment on why, **infer design intent** from patterns, naming conventions, code structure, and domain knowledge.

### Inference Markers

When inferring intent not explicitly stated in code or comments, use phrasing like:
- *"Based on the code structure, this was likely designed to..."*
- *"The choice of X over Y suggests the authors prioritized..."*
- *"Reading between the lines of the inheritance hierarchy, this separation exists because..."*
- *"The naming pattern here implies..."*

This distinguishes fact from analysis while still providing depth.

### Depth Requirements — Every Section Must Answer "WHY"

| Section Type | WHAT (catalog) ❌ | WHY (depth) ✅ |
|---|---|---|
| Module purpose | "The MemCheck plugin checks for memory access violations" | "Why shadow memory? MemCheck maintains a parallel shadow of every allocated region. When your kernel accesses address X, it jumps straight to the shadow slot in O(1). The authors could have used a sorted interval tree (O(log n)) or a hash map, but shadow memory trades 2x memory for guaranteed constant-time checks with zero allocation jitter — the right call for a tool that instruments every single memory operation." |
| Architecture | "Module A depends on Module B" | "Module A depends on Module B because A needs real-time access to B's routing tables. A direct dependency was likely chosen because the lookup is on the critical path — adding a message hop would add ~2 cycles of latency per access." |
| Algorithm | "Uses binary search for lookup" | "Uses binary search rather than hash lookup because the keys are naturally ordered and range queries are common. The O(log n) worst case is acceptable since n is bounded by the config table size (typically < 256 entries)." |
| Error handling | "Returns error code on failure" | "Returns an error code rather than throwing because this is called from the interrupt handler path where exceptions would corrupt the stack. The error propagates up through return values, allowing the caller to decide between retry and abort." |

### Quality Litmus Test

Before finalizing any page, apply this test: **"Could a reader unfamiliar with this codebase explain the design philosophy to a colleague after reading this wiki?"** If the answer is no, the page needs more WHY content.

### What "Deep" Means in Practice

For each major component on a page, content should cover:

1. **Problem it solves** — What challenge does this component address? Why is it non-trivial?
2. **Design rationale** — Why was this approach chosen? What alternatives exist?
3. **Mechanism walkthrough** — How does it actually work, step by step, with code references?
4. **Tradeoffs acknowledged** — What does this design sacrifice? What would change if constraints were different?
5. **Connections explained** — Why does it interact with component X this way? What would break if you changed the interface?

---

## Research Phase — 3-Pass Deep Analysis

### Phase 1A — Broad Survey (Explore & Detect Depth)

Before writing any HTML, gather deep understanding of the codebase and determine the wiki depth.

#### Cache Check (skip Phase 1 if cache is fresh)

If `docs/_research/_manifest.json` exists, check whether the cache is still valid:

```bash
current_sha=$(git -C <target> rev-parse HEAD 2>/dev/null || echo "no-git")
current_count=$(find <target>/ -type f \( -name '*.h' -o -name '*.cc' -o -name '*.cpp' -o -name '*.py' -o -name '*.ts' -o -name '*.java' -o -name '*.rs' -o -name '*.go' \) | wc -l)
```

Read `docs/_research/_manifest.json` and compare `source_sha` and `source_file_count`. If **both match**, skip Phase 1 entirely — load cached research and proceed to Phase 2.

**When to force a fresh run:**
- User explicitly asks to "regenerate research" or "re-analyze"
- The wiki output directory doesn't exist yet (first run)
- More than 30 days since `cache_date` in the manifest

1. **Identify structure** — list the target directory
2. **Gauge scope** — count source files and lines
3. **Detect depth** — use depth detection commands and decision matrix
4. **Classify modules** — L1+L2 (has 3+ meaningful sub-dirs) or L1-flat (< 50 files or no functional sub-dirs)
5. **Discover cross-module dependencies** — find actual `#include` / `import` relationships
6. **Auto-detect language** — determine from file extensions
7. **Broad research** — read key source files. For each module, produce a structured report:

   | Section | Required Content |
   |---------|------------------|
   | Purpose | 2-3 sentence role description |
   | Key Classes | Class name, file, one-line role (**10-15 entries**) |
   | Representative Snippets | **3-5** key code blocks per module (copy verbatim) |
   | Data Flow | How data moves, including hit/miss/error paths |
   | Config/Knobs | Parameter name, default, what it controls (**12+ entries**) |
   | Interactions | Which other modules, via what interface, what data exchanged |
   | Terminology | Domain-specific terms (**15+ per module**) |
   | Architectural Patterns | Patterns used (plugin, observer, factory, pipeline, etc.) and **WHY** |
   | Algorithms & Mechanisms | **2-4 key algorithms** — name, purpose, **4-8 sentence explanation** covering how the algorithm works, its data structures, and complexity |
   | State Machines | FSM state names, transitions, conditions |
   | Error/Edge Cases | Fallback paths, corner cases with **concrete code references** |
   | **Design Decisions Visible in Code** | **3-5 design choices** observable from code structure — for each, note what the choice IS and what it suggests about design priorities |

8. **Save research cache** — persist to `docs/_research/`:
   - Per-module: `docs/_research/<module_name>.md`
   - Project metadata: `docs/_research/_project.md`
   - Manifest: `docs/_research/_manifest.json`

### Phase 1B — Per-Module Deep Analysis (NEW)

After the broad survey, perform a **deep analysis pass** on each major module. This pass asks the "WHY" questions that transform documentation into understanding.

For each module, produce `docs/_research/<module_name>_deep.md` answering:

1. **Existence Rationale** — Why does this module exist as a separate unit? What problem does it solve that couldn't be solved by extending another module? What would the codebase look like without it? (3-5 sentences)

2. **Design Decisions Analysis** — For each key design choice:

   | Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
   |----------|------------|----------------------|-------------------|
   | Memory model | Shadow memory arrays | Hash map, interval tree | O(1) guaranteed, no allocation jitter on hot path |
   | Error strategy | Return codes | Exceptions, Result types | Called from interrupt context |

   List **5-8 design decisions per module**.

3. **Algorithm Deep-Dives** — For each key algorithm (2-4 per module):
   - **Problem statement**: What does this algorithm solve? (2-3 sentences)
   - **Step-by-step trace**: Walk through with actual variable names and data structures (6-10 steps)
   - **Complexity**: Time and space, including amortized analysis
   - **Why this algorithm**: What alternatives exist? Why this one? (3-5 sentences)
   - **Edge cases**: Boundaries, empty input, max capacity, race conditions (2-4 scenarios)

4. **Error Philosophy** — How does this module handle failures? Fail-fast, fail-safe, retry-based, or propagate-up? Explain WHY this philosophy was chosen.

5. **Performance Characteristics** — What was optimized for? What's fast? What's slow? What tradeoffs were made? What would you change if constraints were different?

6. **Evolution Clues** — What suggests how this module evolved? Layered abstractions? Naming inconsistencies? TODO/FIXME comments? Overly complex areas?

### Phase 1C — Cross-Module Synthesis (NEW)

Synthesize understanding of how modules compose into a system.

Produce `docs/_research/_synthesis.md` covering:

1. **End-to-End Flows** — Trace 3-5 key user scenarios from entry to exit through all modules:
   - Entry point, each hand-off, decision points, exit point
   - Total latency/resource profile if discernible

2. **Coupling Analysis** — Where are modules tightly vs loosely coupled?
   - Shared types/interfaces — intentional or accidental?
   - Narrow vs wide interfaces
   - What breaks if you change module X's interface?

3. **Architectural Philosophy** — What overarching principles guide the system?
   - Correctness first or performance first?
   - Explicit over implicit or convention over configuration?
   - Composition or inheritance?
   - Support each observation with code evidence.

4. **Shared State Inventory** — What state is shared across modules? How is consistency maintained?

5. **System Evolution** — How was the system likely built up?
   - What's the "core" (most stable, most depended-upon)?
   - What was added later (wrappers, adapters, compatibility layers)?

---

## Generation Phases

### Phase 2 — Generate Style Spec

Before creating any HTML pages, generate `docs/_style-spec.md` using the [style-spec template](./resources/_style-spec.md). Fill in:
- `{{PROJECT_THEME_KEY}}` — always `neutra-ip` (unified key)
- `{{LANG}}` — primary code language (auto-detected in Phase 1A)
- `{{DATE}}` — generation date in ISO format
- `{{SOURCE_PATH}}` — relative path to the source directory

This file is the **single source of truth** for CSS/JS requirements.

### Phase 3 — Create L0 Project Hub (3-level only)

**Skip for 1-level and 2-level projects.**

Create `docs/index.html` using the [L0 template](./resources/l0-template.html).

Required sections:

- **Hero banner**: project name, subtitle, 2–3 sentence summary
- **Stat row**: module count, language, key metrics
- **Badges**: project-level traits

- **🎯 Project Philosophy** (REQUIRED):
  A dedicated section (200+ words) explaining:
  - What problem this project solves and why it exists
  - What design principles guide the architecture (infer from code patterns)
  - What the project prioritizes (performance? correctness? extensibility?)
  - How it fits in the broader ecosystem
  Use narrative voice: *"When you first look at this codebase, the most striking design choice is..."*

- **🏗️ Design Decisions** (REQUIRED):
  Table of 5-8 key architectural decisions with columns: Decision, Choice Made, Alternatives, Why This Approach.

- **System architecture diagram** (`flowchart TD`): all major modules grouped by function. **Label edges with WHY the dependency exists.**

- **Module cards**: one per module, grouped by category. Each description includes a 1-sentence "why it exists" statement.

- **🔗 Key Data Flows** (REQUIRED):
  2-3 Mermaid `sequenceDiagram` blocks showing major end-to-end flows with `Note over` annotations explaining WHY each hand-off occurs.

- **Cross-module connection diagram**: module boundary interactions with annotations
- **Navigation guide table**
- **Directory Map** — collapsible source tree
- **Footer** with search link

### Phase 4 — Create L1 Overview Pages

Create `docs/<module>_doc/index.html` using the [L1 template](./resources/l1-template.html).

Required sections:

- **Hero banner**: module name, subtitle, 2–3 sentence summary
- **Stat row**: sub-module count, key metrics
- **Badges**: key traits

- **🎯 Why This Module Exists** (REQUIRED):
  150+ words explaining what problem this module solves, why it exists as separate, and what the system would look like without it.

- **🏗️ Design Decisions** (REQUIRED):
  Table of 5+ key design choices with alternatives and rationale.

- **Architecture Mermaid diagram**: `flowchart LR` with subgraphs, actual class names, **annotated edges** explaining WHY. Target 12+ nodes.

- **Data-flow Mermaid diagram**: `sequenceDiagram` with 8-12 interactions and `Note over` annotations.

- **🚶 The Senior Engineer's Tour** (enhanced narrated walkthrough):
  10-14 steps tracing a concrete operation. Each step explains:
  - WHAT happens
  - WHY this step exists (what would break without it)
  - Non-obvious implementation details

- **Key components table**: **10-15 rows** with class names, file paths, and WHY-oriented descriptions.

- **⚡ Algorithm Spotlight** (REQUIRED):
  2-3 key algorithms with: name, purpose, why chosen over alternatives, complexity, and link to focus page.

- **Deep-dive focus sub-pages**: 3-5 topics, each as a dedicated focus page. Parent shows card-grid hub only.

- **⚠️ What Could Go Wrong** (REQUIRED):
  Table of 4+ failure scenarios: Failure, How Detected, Recovery Strategy, Cascading Effects.

- **📊 Performance Profile** (REQUIRED):
  100+ words on what's fast, what's slow, what tradeoffs were made and why.

- **Directory Map**, **Configuration table** (8-12 knobs), **Card grid**, **Footer**

### Phase 5 — Create L2 Pages (batch by size)

**Skip for 1-level projects.**

Create each `docs/<module>_doc/<submod>/index.html` using the [L2 template](./resources/l2-template.html).

Required sections:

- **Breadcrumb**, **Hero**, **Stat row**

- **🎯 Why This Component** (REQUIRED):
  100+ words on why this exists as separate, what problem it solves, how it fits into the module's design.

- **"What & Why" intro box**: plain-English overview (focus on WHY) + vivid analogy

- **🏗️ Design Rationale** (REQUIRED):
  3+ key implementation decisions with Why column.

- **Architecture Mermaid diagram**: classDiagram or flowchart with actual classes
- **Key classes/functions table**: **10-15 rows** with WHY-oriented Purpose column
- **Lifecycle/data-flow Mermaid diagram**: MANDATORY second diagram
- **Interactions table**: **6-10 rows** with WHY this interaction exists

- **📝 Annotated Code Walkthrough** (REQUIRED):
  Pick the most important function. Show actual code with `.code-walk` numbered callout annotations explaining WHY each block exists and what would break without it.

- **Deep-dive focus sub-pages**: 3-5 topics as dedicated focus pages. Parent shows card-grid hub.

- **⚠️ Edge Cases & Boundaries** (REQUIRED):
  3+ edge cases with "what actually happens when..." narratives.

- **Directory Map**, **Configuration/knobs table** (10-15 rows), **Code examples** (3+ snippets), **Footer**

### Phase 6 — Create Focus Deep-Dive Pages

Focus pages are the **deepest level of analysis**. Every deep-dive topic from Phase 1B research gets its own focus page.

**Use the [focus-template.html](./resources/focus-template.html) scaffold.**

Required sections:

- **Breadcrumb**, **Hero**, **"What & Why" intro box**

- **🎯 The Problem** (REQUIRED):
  What challenge does this mechanism solve? Why is it non-trivial? (150+ words)
  *"Race detection seems simple — just track reads and writes — but the challenge is doing it without making the simulation 100x slower."*

- **🔧 The Approach** (REQUIRED):
  How the authors solved it, explained narratively (200+ words). Walk through as if at a whiteboard.

- **🔄 Why Not Alternatives?** (REQUIRED):
  Table comparing 2-3 other approaches: Approach, Pros, Cons, Why Not Chosen.

- **Overview diagram**: Mermaid showing structure/flow with annotated edges
- **Summary grid**: 4-cell overview (role, inputs, decisions, outputs)
- **Decision Points table**: branching decisions with conditions and WHY

- **📖 Step-by-Step Mechanism Trace** (REQUIRED):
  8-12 steps with actual code at each step. Each step explains WHY and what happens if skipped.

- **Behavior diagram**: `stateDiagram-v2` or `sequenceDiagram`
- **Annotated code walkthrough**: `.code-walk` with WHY annotations

- **⚖️ Complexity & Tradeoffs** (REQUIRED):
  Time/space complexity. What was optimized. Under what conditions would a different approach be better?

- **Edge Cases table**: scenarios, behavior, code locations

- **🔄 Failure Recovery** (REQUIRED):
  How errors are detected and handled. What happens when recovery fails? Blast radius? (100+ words)

- **Configuration table**, **Related Topics**, **Directory Map**

**Target**: 500–800 lines, 2+ Mermaid diagrams, 3+ code blocks, 10+ content sections.

#### Focus Page: Update Parent

After creating a focus page, update parent's `<h2 id="deep-dives">` with card link:

```html
<h2 id="deep-dives">Deep-Dive Highlights</h2>
<p class="hub-note">Core mechanisms extracted into dedicated focus pages.</p>
<div class="card-grid deep-dive-grid">
  <a class="card" href="topic_slug/index.html" title="Topic — Deep Dive">
    <h4>Topic Name <span class="focus-badge">Focus</span></h4>
    <p>Short description</p>
    <div class="focus-meta">Extracted topic page</div>
  </a>
</div>
```

Required `<meta>` in focus page `<head>`:
```html
<meta name="wiki-focus-parent" content="../index.html">
```


### Phase 7 — Link Everything, Search & Enhancements

After all pages are created:
1. **Cross-references** — link related sub-modules to each other in their interaction tables
2. **Consistent footers** — all footers should have: back-link (to parent page)
3. **Breadcrumb consistency** — verify all breadcrumbs use the standard separator `›` (rsaquo entity). All breadcrumbs must follow this format:
   - L1 (3-level): `<a href="../index.html">Project</a> › Module`
   - L2 (3-level): `<a href="../../index.html">Project</a> › <a href="../index.html">Module</a> › SubModule`
   - L1 (2-level): no breadcrumb needed
4. **Search page** — create `docs/search.html` using the [search template](./resources/search-template.html), then build the search index:
   ```bash
   python3 scripts/build-search-index.py docs/
   ```
   This generates `docs/search-index.json`. Add a search link to the L0 hub footer. The search page loads the JSON index and provides live client-side full-text search.

5. **Navigation tree** *(optional)* — build the sidebar navigation JSON for pages that embed the sidebar loader:
   ```bash
   python3 scripts/build-nav-tree.py docs/
   ```
   This generates `docs/nav-tree.json`. See `build-nav-tree.py` header for the JS snippet to embed in templates.

6. **Link preview tooltips** — add hover tooltips to internal links showing the target page's subtitle:
   ```bash
   python3 scripts/add-link-tooltips.py docs/
   ```

7. **Auto-crosslink module names** — hyperlink first occurrences of module/sub-module names in body text:
   ```bash
   python3 scripts/auto-crosslink.py docs/
   ```

8. **CSS consistency check** — verify all templates contain the shared CSS tokens:
    ```bash
    python3 scripts/assemble-templates.py
    ```

9. **Stale page check** *(maintenance)* — detect pages that may need regeneration:
    ```bash
    bash scripts/stale-check.sh docs/ 30
    ```

10. **Class cross-references** — link class/struct names across pages:
    ```bash
    python3 scripts/class-crossref.py docs/
    ```

11. **Coverage dashboard** — generate a stats page with per-module metrics:
    ```bash
    python3 scripts/build-stats.py docs/
    ```

### Phase 8 — Verify

Run the [verify.sh](./scripts/verify.sh) script to check all pages in one command:

```bash
bash scripts/verify.sh docs/
```

This checks: theme toggle presence, hljs inclusion, `startOnLoad:false`, no `innerHTML` re-render, no `pre code` color override, intro boxes on all L2 pages, minimum line counts (218+), mermaid diagram counts (2+), broken internal links, focus page parent meta, and focus page back-links. See the script source for details.

Alternatively, run individual checks:

```bash
# All pages have theme toggle
grep -rlc 'themeToggle' docs/

# No bad patterns
grep -rl 'startOnLoad:true' docs/        # should be 0
grep -rl 'el\.innerHTML=src' docs/        # should be 0

# All L2 pages have intro boxes
for d in docs/*_doc/*/index.html; do grep -l 'What is this' "$d" || echo "MISSING: $d"; done

# Broken internal links
find docs -name '*.html' | while read f; do
  dir=$(dirname "$f")
  grep -oP 'href="([^"#]+)"' "$f" | grep -oP '"[^"]*"' | tr -d '"' | while read link; do
    [[ "$link" == http* || "$link" == mailto* ]] && continue
    [ ! -f "$dir/$link" ] && echo "BROKEN: $f -> $link"
  done
done
```




### Phase 9 — Publish Version (on-demand)

Run this whenever you want to create a snapshot before regeneration or after a milestone:

```bash
# Timestamped snapshot
bash scripts/publish-version.sh docs/

# Tagged + custom output base
bash scripts/publish-version.sh docs/ ~/wiki-archive --tag v2.1
```

The script creates a full copy, stamps version metadata into each HTML file, and appends to `versions.json`.

### Phase 10 — Post-Generation Check & Fix

After all pages are generated (or enhanced), run the post-check script to detect and auto-fix common HTML issues that slip through generation:

```bash
# Check & fix all projects in the wiki root
python3 fix_wiki_html.py

# Check & fix specific projects
python3 fix_wiki_html.py claude-code minimind gem5

# Dry-run: report issues without modifying files
python3 fix_wiki_html.py --check
```

The script scans every `index.html` under the target directories and detects **5 categories** of issues:

| # | Issue | Root Cause | Auto-Fix |
|---|-------|-----------|----------|
| 1 | `svg.outerHTML` instead of `cloneNode(true)` | Diagram zoom copies SVG via innerHTML, which corrupts namespaces | Replace with `el.querySelector('svg').cloneNode(true)` and `appendChild` |
| 2 | Missing scroll-wheel zoom on overlay | Overlay opens but has no zoom interaction | Inject `wheel` event listener with CSS `transform:scale()` (range 0.5–5.0) |
| 3 | Missing `data-source` saving before `mermaid.run()` | Theme toggle fails because rendered SVG overwrites original source | Insert `data-source` save loop before the first `mermaid.run()` call |
| 4 | Missing null guard on overlay element | `document.getElementById('overlay')` returns null on pages without diagrams, causing JS errors | Add `if(!overlay)return;` guard after `getElementById` |
| 5 | Wrong localStorage theme key | Pages use inconsistent keys (`wiki-theme`, `theme`, etc.) instead of `neutra-ip-theme` | Replace with `neutra-ip-theme` |

The script is **idempotent** — running it multiple times on already-fixed files produces no changes. Always run with `--check` first to review issues before applying fixes.

**Integration with the pipeline:** Phase 10 should be run after Phase 7 (verify) and before Phase 9 (publish). It catches issues that verify.sh does not check (JS correctness, zoom behavior, theme consistency).

---

## Batch Updates

When applying fixes or theme support across all pages at once, use the [batch update script](./scripts/batch_update.py) as a starting point rather than editing files individually. Copy it into the docs folder, customize the transformations, run it, then delete it.

## Export & Sharing

- **Single-file export**: `python3 scripts/export-single.py docs/ --toc` — merges all pages into one HTML for offline reading, email, or print.
- **Diagram export**: `python3 scripts/extract-diagrams.py docs/` — extracts Mermaid diagrams as standalone SVG files (requires `mmdc`).
- **Version diff**: `bash scripts/diff-versions.sh old_dir/ docs/ --html changelog.html` — compare two versions, produce a changelog.

## Incremental Regeneration

When source code changes after initial wiki generation, use [incremental-regen.sh](./scripts/incremental-regen.sh) to find which wiki pages are stale:

```bash
bash scripts/incremental-regen.sh <source_root> docs/ [git_ref]
# Examples:
bash scripts/incremental-regen.sh . docs/ HEAD~5       # last 5 commits
bash scripts/incremental-regen.sh . docs/ main          # vs main branch
```



## Standard Mermaid Re-render Function

All pages MUST include this function for theme toggling:

```javascript
function renderAllMermaid(theme) {
  var nodes = document.querySelectorAll('pre.mermaid');
  if (!nodes.length || !window.mermaid) return;
  nodes.forEach(function(el) {
    var src = el.getAttribute('data-source');
    if (src) { el.removeAttribute('data-processed'); el.textContent = src; }
  });
  try {
    mermaid.initialize({startOnLoad:false, theme: (theme === 'light') ? 'default' : 'dark',
      flowchart:{useMaxWidth:true, htmlLabels:true, curve:'basis'}});
    mermaid.run();
  } catch(e) { console.warn('mermaid re-render:', e); }
}
```


## Key Rules

1. **Self-contained HTML** — every page embeds all CSS inline in `<style>`. No external CSS links. Pages must work when opened directly via `file://`.

2. **`pre code` must NOT set `color`** — otherwise highlight.js token colors are overridden. Use `pre code{background:none;color:inherit;padding:0}` only.

3. **Code blocks use `class="language-{LANG}"`** — set the appropriate language class for highlight.js (e.g., `language-cpp`, `language-python`, `language-typescript`).

4. **localStorage key pattern**: Use a **single key** for the entire wiki: `neutra-ip-theme`. Do NOT create per-module or per-page keys — this ensures theme choice syncs across all pages. Never use variants like `wiki-theme`, `neutra_ip-theme`, or bare `theme`.

5. **Mermaid re-render on theme change** — all pages must use the **standard `renderAllMermaid(theme)` function** from the templates (see below). This function: saves original source in `data-source` attr before first render; on toggle, restores via `el.textContent` (NOT `innerHTML` — that corrupts angle brackets like `<<abstract>>`); re-inits with new theme; calls `mermaid.run()`. **Do not invent alternative implementations** — copy from template.

6. **No hardcoded colors in Mermaid `style` lines** — do NOT add `style NodeName fill:#0d1117,...` in diagrams. Let Mermaid's theme engine handle colors (`'dark'` / `'default'`). Hardcoded fills break in the opposite theme.

7. **`startOnLoad:false`** in `<head>` — Mermaid must NOT auto-render before the footer JS determines the correct theme.

8. **Research before writing** — read source files directly using `read_file` and terminal commands (`grep`, `head`, `cat`) before writing content. Wiki quality depends on this step. Use the structured research template from Phase 1, step 7.

9. **Every L2 page needs an intro box** — the "What & Why" box with analogy must appear between the badges/stat-row and the Table of Contents on every L2 page. Use the collapsible `<details>` pattern for the analogy so it doesn't add clutter for returning readers.

10. **Intro box content must be unique per sub-module** — never use the same generic text. Each "What is this?" paragraph should explain that specific sub-module's role. Each analogy must map the sub-module's core concept to a distinct, vivid real-world scenario.

11. **L1 pages need a narrated walkthrough** — after the data-flow diagram, add a step-by-step numbered list that traces one concrete operation through the entire module. Name specific sub-modules and typical cycle/latency counts at each step. This replaces abstract diagrams with a "follow along" story.

12. **Cross-module connection diagrams** — when documenting multiple related modules (e.g., core + uncore, frontend + backend), add a `sequenceDiagram` on the L0 project hub page showing how they connect at their boundary, with annotations at each level (hit/miss paths, protocol boundary). For 2-level projects with no L0, add this on the L1 page instead. Use actual `#include` dependencies discovered in Phase 1, step 5 rather than guessing connections.

13. **Flat L1 classification** — modules with fewer than ~50 source files OR no meaningful functional sub-directories get a single L1-flat page (`<module>/index.html`) that combines overview + deep-dive content on one page. Directories named `project/`, `t/`, `test/`, `scripts/`, `docs/`, `config/`, `build/` are NOT functional sub-modules — do not count them when deciding L1-flat vs L1+L2.

14. **Breadcrumb separator** — always use `›` (`&rsaquo;`) as the breadcrumb separator. Never use `>`, `→`, `/`, or `»`.

15. **Style spec as single source of truth** — generate `docs/_style-spec.md` in Phase 2. Read it before creating each page instead of repeating CSS/JS rules inline. This prevents style drift across pages and keeps page generation focused on content.

16. **Page generation pacing** — generate one page at a time using `create_file`. Each page generates 400-700 lines of HTML. Creating pages individually prevents context overflow and ensures each page gets full attention. For very large projects (20+ pages), save research data to `docs/_research/*.md` files to free up context between pages.

17. **Accessibility** — every page must include: (a) a skip-link (`<a href="#main" class="skip-link">Skip to content</a>`) as the first element inside `<body>`, (b) `aria-label="Toggle light/dark theme"` on the theme toggle button, (c) `role="navigation" aria-label="Breadcrumb"` on breadcrumb `<nav>` elements, (d) main content wrapped in `<main id="main">`. See the `.skip-link` CSS in templates.

18. **Print stylesheet** — every page must include a `@media print` block that: hides the theme toggle and skip-link, forces light-theme colors, sets `break-inside:avoid` on cards/diagrams, and optionally appends link URLs after anchors.

19. **Project structure fidelity** — Wiki page structure must mirror the actual project directory and code organization. Follow these rules:
    - **L1 sub-module cards must match real directory names** — list the actual directory names from the source tree, not invented groupings. Card descriptions should reference actual source paths (e.g., `src/arch_base/ · include/arch_base/`).
    - **Stat boxes must show domain-specific metrics** — don't use generic counts like "N source files". Study the code to find meaningful stats: number of protocols supported, fabric topology types, pipeline stages, cache levels, FSM states, etc.
    - **L2 page sections must follow the code's own organization** — if the source has separate concerns (e.g., BaseIP lifecycle vs UFI interface vs NIP interface vs D2D), give each its own H2 section with per-class method tables and code examples, rather than dumping everything into one flat "Key Classes" table.
    - **File paths in tables** — always include the actual header/source file path (e.g., `include/arch_base/base_ip.h`) rather than just the class name. This helps readers find the code.
    - **Per-class method tables** — for major classes, include a method/member table with columns "Method/Member", "When Called / Type", "Purpose". Show 4-8 methods per significant class, not just the class declaration.
    - **Code examples must be structural, not illustrative** — show real class declarations, representative function signatures, and usage patterns copied from source (verbatim or closely adapted). Don't invent simplified pseudo-code — readers want to see the actual API shape.
    - **Badge content must be domain-specific** — e.g., `🔵 BaseIP Root`, `🟢 Agent · Bridge · D2D`, `🟡 UFI / NIP Interfaces`. Don't use generic badges like `🔵 Neutra IP`, `🟢 arch_base`, `🟡 15 classes`.

20. **Mermaid diagram quality** — Diagrams must show real relationships with detail, not just boxes and arrows. Follow these rules:
    - **Use `classDiagram` for class hierarchies** — show inheritance (`<|--`), composition (`*--`), and aggregation (`o--`) with actual class names and key methods/properties. Example:
      ```
      classDiagram
        class BaseIP{+Init() +PreSimulation() +OnEvent() +CreatePipeline()}
        class BaseAgent{+ingress_queue +staging_queue +ProcIngressMsg() +ProcAgentMsg()}
        MultiHandlerModel <|-- BaseIP
        BaseIP <|-- BaseAgent
        BaseAgent <|-- MPortsAgent
      ```
    - **Use `flowchart` with subgraphs for module dependencies** — group related classes into named subgraphs that map to actual directories/modules. Label edges with the interface or protocol used (e.g., `-->|UFI|`, `-->|NIP Add/Drop|`, `-->|ActionList|`).
    - **Use `sequenceDiagram` with detailed participants for data flow** — name participants after actual classes/components (e.g., `participant AGT as BaseAgent`, `participant BRG as BaseBridge`). Include full request+response round-trips, credit flow, and error paths. Add `Note over` annotations for timing or key observations. Target 8-12 interactions, not 4-5.
    - **Use `stateDiagram-v2` for FSMs and lifecycle** — show actual states and transitions from the source code, not invented simplifications.
    - **L1 architecture diagrams** — the L1 flowchart must show class-level relationships across sub-modules with named subgraphs (one per sub-module/directory). Edges must be labeled with the actual interface contract (protocol name, API function, data type exchanged). This is the most important diagram in the wiki — it should take 20-30 Mermaid lines, not 8-10.
    - **L2 diagrams must be mechanism-specific** — don't repeat the L1 overview diagram. The L2 architecture diagram should show the internal class hierarchy of that specific sub-module. The L2 data-flow diagram should trace a concrete operation through that sub-module's classes.
    - **Minimum diagram complexity**: L1 architecture diagrams should have 12+ nodes and 10+ edges. L2 architecture diagrams should have 6+ nodes. Sequence diagrams should have 6+ participants and 8+ interactions.
    - **NO emojis in Mermaid node labels** — Unicode emoji characters (🔍, 📊, 🚀, etc.) cause Mermaid v10 to fail silently during parsing. Use plain text descriptions only inside node labels, `participant` names, and `Note` text. Emojis in HTML headings and prose are fine — just not inside `<pre class="mermaid">` blocks.

21. **Auto-generated TOC** — L1 and L2 pages use an empty `<nav class="toc" id="toc"></nav>` element that gets populated by footer JS from H2/H3 headings with `id` attributes. Do NOT manually write TOC `<ol>` entries — the JS handles this. Ensure all H2/H3 headings have `id` attributes for the auto-TOC to link to.

22. **Freshness metadata** — every page must include `<meta name="wiki-generated" content="{{DATE}}">` and `<meta name="wiki-source" content="{{SOURCE_PATH}}">` in `<head>`. Set `{{DATE}}` to the generation date (ISO format). Set `{{SOURCE_PATH}}` to the source directory path relative to the project root.

23. **Auto-detect language** — do NOT ask the user for the code language. Auto-detect it in Phase 1 step 6 from file extension distribution. Only fall back to asking if the distribution is ambiguous (no extension reaches 50%+).

24. **Search page** — always create `docs/search.html` and `docs/search-index.json` in Phase 6. The search page uses the [search template](./resources/search-template.html). The index is built by [build-search-index.py](./scripts/build-search-index.py). Add a search link to the L0 hub footer.

25. **Code snippet extraction** — during Phase 1 research (step 7), extract **3-5** representative code snippets per module (class declarations, key function signatures, enum definitions, configuration struct definitions) verbatim from source. These appear in the L2 "Code Examples" section for authenticity. At least 2 snippets must appear on every L2 page.

26. **Link preview tooltips** — after all pages are created, run [add-link-tooltips.py](./scripts/add-link-tooltips.py) to inject `title="..."` attributes on internal links showing the target page's subtitle text as a hover preview.

27. **Code copy button** — L1 and L2 pages include a "Copy" button on every `<pre><code>` block (excluding mermaid `<pre>`). The button is positioned top-right via `position:absolute`, hidden by default (`opacity:0`), and appears on `pre:hover`. Uses `navigator.clipboard.writeText()` with "Copied!" feedback. Print stylesheet hides `.copy-btn`.

28. **Diagram zoom/fullscreen** — L0, L1, L2, and focus pages include a fullscreen overlay for `.diagram-container` blocks. Clicking a diagram opens a centered overlay (`.diagram-overlay`) with the diagram SVG cloned in. Click outside or press Escape to close. CSS uses `z-index:3000` and `rgba(0,0,0,.85)` backdrop. Print stylesheet hides `.diagram-overlay`. **Important:** Mermaid v10+ sets an inline `style="max-width: Npx"` on rendered SVGs, which prevents them from scaling up inside the overlay. The overlay CSS MUST include `#diagramOverlay.active svg,#diagramOverlayContent svg{max-width:90vw!important;max-height:85vh!important;width:90vw!important}` to override the inline cap with `!important`.

    **Zoom consistency rules:**
    - ALL pages MUST use the same zoom pattern: click `.diagram-container` (or `.mermaid-wrap`) → clone SVG into `#diagramOverlayContent` → show `#diagramOverlay`.
    - The overlay content wrapper (`#diagramOverlayContent`) MUST have `background:var(--bg,#0d1117);border-radius:12px;padding:2rem;border:1px solid var(--border,#30363d)` to ensure readable background in zoomed view. This prevents contrast issues where SVG text becomes invisible against a bare dark backdrop.
    - **Never** use `content.innerHTML = dc.innerHTML` — this dumps raw HTML as a string and re-parses it, losing SVG fidelity. Instead, always clone the SVG node: `var svg=dc.querySelector('svg'); var clone=svg.cloneNode(true); content.innerHTML=''; content.appendChild(clone);` and apply `clone.style.maxWidth='90vw'`.
    - **Scroll-wheel zoom** — after clicking to open the overlay, users MUST be able to zoom in/out with the mouse scroll wheel. The overlay JS must listen for `wheel` events on `#diagramOverlayContent` and apply `transform:scale(N)` where N ranges from 0.5 to 5.0, incrementing by ±0.1 per wheel tick. Reset scale to 1.0 when the overlay closes. Use `{passive:false}` to allow `e.preventDefault()`. Add `transform-origin:center center` in CSS on `#diagramOverlayContent`.
    - When a wiki has shared assets (`docs/assets/neutra-docs-normalize.css` + `docs/assets/neutra-docs.js`), every page should reference them. The shared JS provides a consistent click-to-zoom handler for both `.diagram-container` and `.mermaid-wrap` elements, creating overlay elements if missing.
    - Do NOT use separate zoom mechanisms on different pages (e.g., `zoomDiagram()` on some, `toggleOverlay()` on others, inline `onclick` on others). Use one consistent pattern across all pages.

29. **Back-to-top button** — ALL 4 templates (L0, L1, L2, search) include a `#backToTop` button (fixed, bottom-right, `z-index:1000`). Shows after scrolling 400px (`window.scrollY > 400`). Smooth-scrolls to top on click. Hidden in print. Uses `.back-to-top.visible{display:flex}` toggle.

30. **Reading time estimate** — L1 and L2 pages auto-compute reading time from word count in `<main>` (`Math.ceil(words/200)` at 200 WPM). Displayed as "⏱ ~N min read" appended to the `.hero` div.

31. **Collapsible long tables** — L2 pages auto-wrap tables with 8+ rows in a `<details class="collapsible-table">` element. Summary shows row count. This prevents very long config/class tables from dominating the page.

32. **Source revision tracking** — ALL templates include `<meta name="wiki-source-rev" content="{{GIT_SHA}}">` in `<head>`. Set `{{GIT_SHA}}` to the short commit hash of the source at generation time (from `git rev-parse --short HEAD`). Used by `incremental-regen.sh` and `stale-check.sh` to detect when source has been updated.

33. **CSS dedup** — shared CSS tokens (design variables, body, headings, links, theme toggle, skip-link, back-to-top) are canonical in [_shared-css.txt](./resources/_shared-css.txt). Run [assemble-templates.py](./scripts/assemble-templates.py) to verify all templates contain these shared lines. Per-template CSS (badges, cards, diagrams, copy button, etc.) lives only in that template.

34. **CSS variable consistency** — ALL pages in a wiki MUST use the same CSS variable set. The canonical dark-theme palette is: `--bg:#0d1117;--surface:#161b22;--text:#c9d1d9;--accent:#58a6ff;--accent2:#3fb950;--accent3:#d29922;--accent4:#f85149;--border:#30363d;--heading:#f0f6fc;--code-bg:#161b22;--text-muted:#8b949e`. Light-theme overrides use `--bg:#fff;--surface:#f6f8fa;--text:#1f2328;--border:#d0d7de;--accent:#0969da`. Never introduce alternative palettes (e.g., catppuccin-style `#1e1e2e`) on individual pages.

35. **Auto-crosslinking** — after all pages are generated, run [auto-crosslink.py](./scripts/auto-crosslink.py) to hyperlink first occurrences of module/sub-module names in body text. Creates `.bak` backups. Only links within `<main>`, skipping `<a>`, `<code>`, `<pre>`, headings:
    ```bash
    python3 scripts/auto-crosslink.py docs/
    ```

36. **Stale page detection** — run [stale-check.sh](./scripts/stale-check.sh) to find wiki pages whose `wiki-generated` date exceeds a threshold:
    ```bash
    bash scripts/stale-check.sh docs/ 30  # warn about pages >30 days old
    ```

37. **Keyboard navigation** — L1 and L2 pages support `j`/`k` keys to scroll between H2 sections (smooth scroll). Search page supports `/` to focus the search input. All keyboard handlers skip `<input>`, `<textarea>`, and `contentEditable` elements.

38. **Versioned output** — use [publish-version.sh](./scripts/publish-version.sh) to publish timestamped or tagged snapshots of the wiki:
    ```bash
    bash scripts/publish-version.sh docs/                          # timestamped copy
    bash scripts/publish-version.sh docs/ ~/archive --tag v2.1     # tagged copy to custom base
    ```
    The script copies the wiki directory to `docs_YYYY-MM-DD_HHMMSS/` (or `docs_TAG/`), stamps every HTML with `<meta name="wiki-version" content="...">`, and maintains a `versions.json` manifest (version, timestamp, path, page-count, git-sha). Use this before regeneration to preserve a rollback snapshot.

39. **Focus deep-dive pages** — when a topic on an L2 page deserves much deeper exploration (specific algorithm, complex data structure, intricate protocol), generate a **focus page** using [focus-template.html](./resources/focus-template.html). Focus pages:
    - Live at `docs/<module>_doc/<submod>/<topic_slug>/index.html`
    - Include `<meta name="wiki-focus-parent" content="PARENT_PATH">` for parent tracking
    - Use 4-level breadcrumbs: `Project › Module › SubModule › Topic`
    - Have unique sections: `.focus-label` badge, `.callout` boxes (`.warn`/`.danger`/`.success`), `.code-walk` with numbered step annotations
    - Must preserve the full template invariants required by `verify.sh` (`skip-link`, `main`, `@media print`, diagram overlay, back-to-top, reading time, copy buttons)
    - After creating a focus page, run [link-focus-page.py](./scripts/link-focus-page.py) to insert a card into the parent L2's shared focus grid:
      ```bash
      python3 scripts/link-focus-page.py <parent_l2.html> <topic_slug> "<Topic Name>" "<Short description>"
      ```
    - Rebuild search index after adding focus pages (`python3 scripts/build-search-index.py docs/`)

40. **Version diff report** — compare two wiki snapshots and produce a changelog with [diff-versions.sh](./scripts/diff-versions.sh):
    ```bash
    bash scripts/diff-versions.sh docs_v1.0/ docs/                     # terminal report
    bash scripts/diff-versions.sh docs_v1.0/ docs/ --html changelog.html  # + HTML report
    ```
    Shows new/removed/modified pages with word-count and line-count deltas. HTML report includes a summary dashboard with dark/light theme.

41. **Coverage dashboard** — generate a `stats.html` page showing per-module coverage metrics with [build-stats.py](./scripts/build-stats.py):
    ```bash
    python3 scripts/build-stats.py docs/
    python3 scripts/build-stats.py docs/ --out docs/stats.html --stale-days 14
    ```
    Reports: total pages/lines/words/diagrams, focus pages, stale pages, thin pages, missing intro boxes. Includes per-module breakdown with relative content bars.

42. **Single-file export** — merge all wiki pages into one self-contained HTML with [export-single.py](./scripts/export-single.py):
    ```bash
    python3 scripts/export-single.py docs/                       # → docs-export.html
    python3 scripts/export-single.py docs/ --out wiki.html --toc  # with table of contents
    ```
    Each page becomes a section with page breaks. Includes embedded Mermaid and highlight.js. Suitable for printing, email, or offline reading.

43. **Mermaid diagram export** — extract diagrams as standalone SVG/PNG files with [extract-diagrams.py](./scripts/extract-diagrams.py):
    ```bash
    python3 scripts/extract-diagrams.py docs/ --dry-run           # list diagrams without rendering
    python3 scripts/extract-diagrams.py docs/ --out diagrams/     # render to SVG
    python3 scripts/extract-diagrams.py docs/ --format png --theme default
    ```
    Requires `mmdc` from `@mermaid-js/mermaid-cli` (`npm install -g @mermaid-js/mermaid-cli`). Auto-detects diagram type (flowchart, sequence, state, class) for file naming.

44. **Class cross-references** — link class/struct names across pages with [class-crossref.py](./scripts/class-crossref.py):
    ```bash
    python3 scripts/class-crossref.py docs/                       # add cross-ref links
    python3 scripts/class-crossref.py docs/ --dry-run             # preview without modifying
    ```
    Extracts class names from "Key Classes" tables, builds a class→page index, then hyperlinks the first occurrence of each class in other pages. Creates `.bak` backups. Complements auto-crosslink.py (which links module/sub-module names).

45. **CI workflow** — a GitHub Actions workflow template is provided at [resources/wiki-check.yml](./resources/wiki-check.yml). Copy it to `.github/workflows/wiki-check.yml` in your repo. It runs verify.sh and stale-check.sh on push/PR to `docs/`, generates the coverage dashboard, and uploads it as an artifact.

46. **Directory Map** — every L0, L1, L2, and focus page MUST include a `<h2 id="directory-map">Directory Map</h2>` section showing the source file tree relevant to that page's scope. Use a collapsible `<details open>` with a `<pre><code>` block containing Unicode box-drawing characters (`├── │ └──`). Annotate key files with `← Role: ...`. This section bridges the wiki and the actual codebase — readers use it to find source files. See the **Directory Map HTML Pattern** section for the exact HTML structure. Populate from real paths discovered in Phase 1 research, not invented paths.

47. **Post-generation HTML check** — after generating all pages, run `python3 fix_wiki_html.py [project_dirs...] --check` to detect common issues (see Phase 10). Fix them with `python3 fix_wiki_html.py [project_dirs...]`. The script is idempotent. Common patterns that trigger issues: (a) using `svg.outerHTML` instead of `cloneNode(true)` for diagram zoom, (b) overlay containers without scroll-wheel zoom handlers, (c) calling `mermaid.run()` without first saving `data-source`, (d) accessing overlay elements without null guards, (e) using localStorage keys other than `neutra-ip-theme`.





## CSS Design Tokens

| Token | Dark | Light |
|-------|------|-------|
| `--bg` | `#0d1117` | `#ffffff` |
| `--surface` | `#161b22` | `#f6f8fa` |
| `--border` | `#30363d` | `#d0d7de` |
| `--text` | `#c9d1d9` | `#1f2328` |
| `--text-muted` | `#8b949e` | `#656d76` |
| `--accent` | `#58a6ff` | `#0969da` |
| `--accent2` | `#3fb950` | `#1a7f37` |
| `--accent3` | `#d29922` | `#9a6700` |
| `--accent4` | `#f85149` | `#cf222e` |
| `--heading` | `#f0f6fc` | `#1f2328` |
| `--code-bg` | `#1c2128` | `#f6f8fa` |

## CDN Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| Mermaid.js | 10.x | Diagrams (flowchart, class, sequence) |
| Highlight.js | 11.9.0 | Code syntax highlighting |

## Component CSS Classes

| Class | Usage |
|-------|-------|
| `.hero` | Full-width banner with subtitle + description |
| `.stat-row > .stat-box` | Metric cards (`.num` + `.label`) |
| `.badge.{blue,green,yellow,red}` | Colored tag pills |
| `.diagram-container` | Theme-adaptive wrapper for `<pre class="mermaid">` |
| `.card-grid > .card` | Clickable sub-module cards (L1) or info cards (L2) |
| `.toc` | Two-column table of contents |
| `.breadcrumb` | Navigation breadcrumbs |
| `.footer` | Centered footer with back-link + search link |
| `.theme-toggle` | Fixed floating dark/light toggle button |
| `.intro-box` | "What & Why" intro box with border + rounded corners (L2 only) |
| `.search-input` | Full-width search input on search page |
| `.skip-link` | Hidden skip-to-content link, visible on `:focus` (accessibility) |
| `.search-input` | Full-width search input on search page |
| `.result` | Search result card with title, path, excerpt |
| `.copy-btn` | "Copy" button on code blocks, positioned absolute top-right (L1, L2) |
| `.diagram-overlay` | Fixed fullscreen overlay for zoomed diagrams (L0, L1, L2) |
| `.diagram-overlay-content` | Inner container for zoomed diagram content |
| `#diagramOverlay.active svg` | Forces Mermaid SVGs to scale up to 90vw in zoom overlay (overrides inline max-width set by Mermaid) |
| `.back-to-top` | Fixed bottom-right scroll-to-top button (all templates) |
| `.collapsible-table` | `<details>` wrapper for tables with 8+ rows (L2) |
| `.focus-label` | Red "Focus Deep-Dive" badge in hero (focus pages only) |
| `.callout` | Highlighted info/warning box with left border (focus pages); variants: `.warn`, `.danger`, `.success` |
| `.code-walk` | Numbered step-by-step code walkthrough with CSS counter (focus pages) |
| `.code-walk .step` | Individual step in code walkthrough, auto-numbered |
| `#directory-map` | Collapsible source tree section using `<details open>` + `<pre><code>` with box-drawing chars (all levels) |

## Intro Box HTML Pattern

Insert this between the badges/stat-row and the `<h2>Table of Contents</h2>` on every L2 page:

```html
<div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1.4rem 1.6rem;margin:1.5rem 0;">
<h3 style="margin-top:0;color:var(--accent);">&#128218; What is this &amp; why does it exist?</h3>
<p>PLAIN_ENGLISH_EXPLANATION — 2-4 sentences describing what this sub-module does
and why it exists, targeted at someone who has never read the source code.</p>
<details style="margin-top:.8rem;">
<summary style="cursor:pointer;color:var(--accent2);font-weight:600;">&#128161; Real-world analogy</summary>
<p style="margin-top:.5rem;padding-left:1rem;border-left:3px solid var(--accent3);color:var(--text-muted);">A VIVID CONCRETE METAPHOR mapping this sub-module to everyday life. 3-5 sentences, making the abstract concept tangible.</p>
</details>
</div>
```

## Narrated Walkthrough HTML Pattern

Insert this after the data-flow/lifecycle diagram on L1 pages:

```html
<div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1.4rem 1.6rem;margin:1.5rem 0;">
<h3 style="margin-top:0;color:var(--accent);">&#128694; Step-by-Step Narrated Walkthrough</h3>
<p style="color:var(--text-muted);margin-bottom:1rem;">Follow a single <strong>CONCRETE_OPERATION</strong> as it flows through the entire module:</p>
<ol style="line-height:2;">
<li><strong>Stage/Sub-module Name</strong> — What happens here, in plain English. Mention typical latency (e.g., "~4 cycles") or key concepts.</li>
<li><strong>Next Stage</strong> — Next step explanation...</li>
<!-- 8-12 steps covering the full path -->
</ol>
</div>
```

## Deep-Dive Section Pattern

Insert 3-5 of these H3 sections on every L2 page, after the interactions table and before the configuration table. Each deep-dive covers a core mechanism, algorithm, or subsystem with enough detail that a reader could understand how it works without reading the source. **This is the single most important content section** — it's what separates a shallow wiki from a genuinely useful reference.

```html
<h3 id="SLUG">MECHANISM_NAME Deep-Dive</h3>
<p>OPENING_PARAGRAPH — 2-3 sentences explaining what this mechanism does and why
it matters. Set context for someone who hasn't read the source.</p>

<p>DETAIL_PARAGRAPH — 3-5 sentences explaining HOW it works: the algorithm,
data structures, state transitions, or protocol steps involved. Name specific
classes and functions. Include cycle counts, bit widths, or table sizes where
known.</p>

<p>GOTCHA_PARAGRAPH (optional) — 1-2 sentences about performance implications,
common pitfalls, or non-obvious behavior. E.g., "When the table overflows,
the predictor falls back to static prediction, causing a ~15% misprediction
spike."</p>

<!-- Optional: additional Mermaid diagram for this mechanism -->
<div class="diagram-container">
<pre class="mermaid">
stateDiagram-v2
    [*] --> Idle
    Idle --> Pending : request arrives
    Pending --> Active : credits available
    Active --> Complete : data returned
    Complete --> Idle : entry freed
</pre>
</div>
```

### Deep-Dive Topic Ideas by Module Type

Use this as a starting point — add or substitute topics based on what the research reveals:

| Module Type | Good Deep-Dive Topics |
|-------------|----------------------|
| Pipeline/core | Fetch & decode stages, allocation/rename, scheduling policy, write-back arbitration, pipeline flush & recovery |
| Branch prediction | GHR-based prediction, pattern history tables, return stack buffer, indirect target predictor, update & training flow |
| Cache/memory | Replacement policy, prefetcher algorithms, miss status handling, store-to-load forwarding, coherence protocol |
| Execution | Port binding & scheduling, variable-latency operations, bypass network, replay mechanism |
| Uncore/fabric | Credit-based flow control, IDI/CMI protocol, snoop handling, directory-based coherence, QoS arbitration |
| Retirement | ROB management, exception handling, memory ordering enforcement, checkpoint & restore |
| Platform/SoC | Topology configuration, platform initialization, device model registration, interrupt routing |
| Power management | DVFS decision flow, C-state transitions, frequency scaling, telemetry counters |
| Infrastructure | Port-based data transfer, pipeline modeling primitives, register file allocation, event system |
| Tools/analysis | Trace format & parsing, statistics collection, checkpoint format, visualization pipeline |



## Configuration Reference Pattern

Add this on L2 pages — search source code for knob definitions, `#define` constants, and command-line flags:

```html
<h3 id="configuration">Configuration Reference</h3>
<table>
<tr><th>Parameter</th><th>Default</th><th>Description</th></tr>
<tr><td><code>bp.ghr_size</code></td><td>64</td><td>Global history register bit width — larger values capture more branch correlation at the cost of table size</td></tr>
<tr><td><code>bp.btb_entries</code></td><td>4096</td><td>Number of BTB entries — direct-mapped, indexed by PC bits [13:2]</td></tr>
<!-- 10-15 rows minimum -->
</table>
```

## Directory Map HTML Pattern

Add this section on **every L1, L2, and focus page** to show the source files/directories relevant to that page's scope. Use a collapsible `<details>` tree so it doesn't dominate the page. Populate it during Phase 1 research — list real paths discovered with `find`/`ls`, not invented ones.

For **L0 pages**, show the top-level project directory structure (modules only, no deep file listing).
For **L1 pages**, show the module's directory tree (sub-module directories + key files).
For **L2 pages**, show the sub-module's files with brief annotations.
For **focus pages**, show only the files directly relevant to the topic.

```html
<h2 id="directory-map">Directory Map</h2>
<details open>
<summary style="cursor:pointer;color:var(--accent);font-weight:600;">Source tree for this module</summary>
<pre style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1rem;margin-top:.5rem;font-size:.85rem;line-height:1.6;overflow-x:auto;"><code>module_name/
├── sub_dir_a/
│   ├── file_a1.ts          ← Role: brief annotation
│   ├── file_a2.ts          ← Role: brief annotation
│   └── index.ts            ← Role: entry point
├── sub_dir_b/
│   ├── file_b1.ts          ← Role: brief annotation
│   └── file_b2.ts          ← Role: brief annotation
├── config.ts               ← Role: module configuration
└── types.ts                ← Role: shared type definitions
</code></pre>
</details>
```

**Rules for Directory Map:**
- Use Unicode box-drawing characters (`├── │ └──`) for the tree
- Annotate key files with `← Role: ...` (keep to one short phrase)
- For large directories (20+ files), show the most important 15 and add `... (N more files)` at the end
- Directories get a trailing `/`
- The `<details open>` starts expanded; readers can collapse it
- This section goes **after** the Configuration table and **before** the Code Examples section on L2 pages, or after the Card Grid on L1 pages

## Cross-Module Connection Pattern

When documenting multiple related modules, add this to the top-level `index.html`:

```html
<h2>How ModuleA &amp; ModuleB Connect</h2>
<p>Explanation of where one module ends and the other begins.</p>
<div class="diagram-container">
<pre class="mermaid">
sequenceDiagram
    participant A as ModuleA Component
    participant Boundary as Protocol Boundary
    participant B as ModuleB Component
    A->>Boundary: Request (opcode)
    Note over A,Boundary: HIT → fast path done
    Boundary->>B: Forward on miss
    B-->>Boundary: Response data
    Boundary-->>A: Return to requester
</pre>
</div>
<blockquote>
<strong>Key insight:</strong> ModuleA owns X. ModuleB owns Y. The protocol boundary is Z.
</blockquote>
```

## Focus Page Content Structure

A focus page follows this section order:

1. **Breadcrumb** — `Project › Module › SubModule › Topic Name`
2. **H1 + Hero** — topic name with `.focus-label` badge ("Focus Deep-Dive"), subtitle, description
3. **What & Why intro box** — explain what this mechanism is and why it matters, tailored to a newcomer
4. **TOC** — auto-generated from H2/H3
5. **Overview Mermaid** — flowchart showing the mechanism's internal structure
6. **How It Works** — H2 section with H3 phases/stages, code snippets, `.callout` boxes for important notes
7. **Behavior Mermaid** — stateDiagram showing state transitions or lifecycle
8. **Annotated Code Walkthrough** — `.code-walk` with numbered `.step` divs, each containing a code block and explanation
9. **Edge Cases table** — scenario, behavior, notes
10. **Configuration table** — knobs/parameters specific to this mechanism
11. **Related Topics** — links to related focus pages or parent sections
12. **Footer** — back link to parent L2 + search link

### Focus Page Callout Pattern

```html
<div class="callout">
  <strong>Note:</strong> Explanation of an important implementation detail.
</div>
<div class="callout warn">
  <strong>Warning:</strong> Common pitfall or non-obvious behavior.
</div>
<div class="callout success">
  <strong>Performance:</strong> Why this design choice is efficient.
</div>
```

### Focus Page Code Walk Pattern

```html
<div class="code-walk">
  <div class="step">
    <h4>Lookup the prediction table</h4>
    <pre><code class="language-cpp">auto entry = table[hash(pc)];</code></pre>
    <p>The predictor hashes the program counter to index into...</p>
  </div>
  <div class="step">
    <h4>Check confidence counter</h4>
    <pre><code class="language-cpp">if (entry.conf >= threshold) { ... }</code></pre>
    <p>Only predictions with high confidence are used...</p>
  </div>
</div>
```

## Auto-generated TOC Pattern

L1 and L2 templates use auto-generated TOC instead of manual `<ol>` entries. Include this in the template:

```html
<!-- In the body: -->
<nav class="toc" id="toc"></nav>

<!-- In the footer script: -->
<script>
(function(){
  var toc=document.getElementById('toc');if(!toc)return;
  var headings=document.querySelectorAll('h2[id],h3[id]');
  var ol=document.createElement('ol');
  var currentH2Li=null;
  headings.forEach(function(h){
    if(h.closest('#toc,.toc'))return;
    var li=document.createElement('li');
    var a=document.createElement('a');a.href='#'+h.id;a.textContent=h.textContent;
    li.appendChild(a);
    if(h.tagName==='H3'&&currentH2Li){
      var sub=currentH2Li.querySelector('ol');
      if(!sub){sub=document.createElement('ol');currentH2Li.appendChild(sub);}
      sub.appendChild(li);
    }else{ol.appendChild(li);if(h.tagName==='H2')currentH2Li=li;}
  });
  toc.appendChild(ol);
})();
</script>
```

**Important**: All H2 and H3 headings must have `id` attributes (e.g., `<h2 id="architecture">Architecture</h2>`) for the auto-TOC to generate links. The TOC script runs before mermaid/hljs so the DOM is ready.

---





## Post-Generation Enhancement

### Quality Bar — Minimum Line Counts

| Page Level | Minimum | Target | Notes |
|------------|---------|--------|-------|
| L0 project hub | 350 | 400–500 | Philosophy, design decisions, 2+ data flow diagrams |
| L1 overview (with sub-modules) | 400 | 400–900 | Narrated walkthrough, design decisions, algorithm spotlight |
| L1 flat (no sub-modules) | 350 | 350–500 | Combines overview + deep-dive |
| L2 deep-dive (major) | 450 | 450–800 | Annotated code walkthrough, design rationale, 3-5 focus pages |
| L2 deep-dive (small) | 350 | 350–500 | 3+ deep-dive sections + design rationale |
| Focus page | 500 | 500–800 | Problem statement, alternatives comparison, step-by-step trace |

### Enhancement Checklist per Page

| Element | L0 | L1 | L2/Flat | Focus | Notes |
|---------|----|----|---------|-------|-------|
| "Why This Exists" section | ✅ | ✅ | ✅ | ✅ | Explains PURPOSE, not just function |
| Design Decisions table | ✅ | ✅ | ✅ | — | 5+ rows for L0/L1, 3+ for L2 |
| Intro box ("What is this?") | ✅ | ✅ | ✅ | ✅ | Unique vivid metaphor per page |
| `<details>` analogy | ✅ | ✅ | ✅ | ✅ | 3-5 sentence concrete metaphor |
| 2+ Mermaid diagrams | ✅ | ✅ | ✅ | ✅ | Annotated edges explaining WHY |
| 3rd Mermaid (recommended) | — | — | ✅ | ✅ | State or sequence diagram |
| Key classes/components table | — | ✅ | ✅ | — | **10–15 rows** minimum |
| Interactions table | — | ✅ | ✅ | — | **6-10 rows** with WHY column |
| Deep-dive focus sub-pages | — | ✅ | ✅ | — | **3–5 focus pages**; card-grid hub |
| Directory Map | ✅ | ✅ | ✅ | ✅ | Collapsible source tree |
| Configuration/knobs table | — | ✅ | ✅ | ✅ | **10–15 knobs** |
| Code examples | — | ✅ | ✅ | ✅ | **3+ snippets** of actual code |
| Narrated walkthrough | — | ✅ | — | — | **10-14 steps** with WHY |
| Module cards grid | ✅ | ✅ | — | — | Cards with "why it exists" |
| Algorithm Spotlight | — | ✅ | — | — | 2-3 algorithms with alternatives |
| Annotated Code Walkthrough | — | — | ✅ | ✅ | `.code-walk` with WHY annotations |
| Alternatives Comparison | — | — | — | ✅ | 2-3 alternatives with tradeoff table |
| Failure Analysis | — | ✅ | ✅ | ✅ | 4+ scenarios with recovery |
| Performance Profile | — | ✅ | — | — | What's fast/slow and WHY |
| Complexity Analysis | — | — | — | ✅ | Time/space with reasoning |

### Depth Verification Questions

Before finalizing any page, verify these are answered:

1. **WHY does this exist?** — Not "what does it do" but "what problem does it solve and why this approach?"
2. **What were the alternatives?** — At least 2 alternative approaches mentioned
3. **What tradeoffs were made?** — Explicit statement of what was sacrificed
4. **What would break if you removed this?** — Downstream impact analysis
5. **Could a newcomer explain the design to a colleague?** — The ultimate litmus test

### Enhancement Verification

```bash
# Check all pages meet minimum line count (no page under 350 lines)
for f in $(find docs -name 'index.html'); do
  lines=$(wc -l < "$f")
  [ "$lines" -lt 350 ] && echo "THIN: $f ($lines lines)"
done

# Every page has an intro box
for f in $(find docs -name 'index.html'); do
  grep -qL 'What is this' "$f" && echo "MISSING INTRO: $f"
done

# Every page has 2+ Mermaid diagrams
for f in $(find docs -name 'index.html'); do
  count=$(grep -c 'class="mermaid"' "$f")
  [ "$count" -lt 2 ] && echo "FEW DIAGRAMS: $f ($count)"
done

# Every page has a "Why" section
for f in $(find docs -name 'index.html'); do
  grep -qiL 'why.*exist\|design.*decision\|design.*rationale' "$f" && echo "NO WHY: $f"
done

# Every L2 page has annotated code walkthrough
for f in docs/*_doc/*/index.html; do
  grep -qL 'code-walk' "$f" && echo "NO CODE WALK: $f"
done
```
