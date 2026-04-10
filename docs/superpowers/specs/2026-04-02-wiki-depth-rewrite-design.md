# Wiki Generator Depth Rewrite — Design Spec

**Date:** 2026-04-02  
**Status:** Approved  
**Goal:** Rewrite the wiki-generator skill from scratch so generated wikis provide deep, narrative-style analysis that explains WHY code is designed the way it is — not just WHAT it does.

---

## Problem Statement

The current wiki generator produces accurate, well-structured documentation that covers code structure (WHAT) and mechanics (HOW), but lacks:

1. **Design rationale** — Why was this architecture/algorithm/pattern chosen?
2. **Alternatives analysis** — What other approaches could have been used?
3. **Cross-module reasoning** — Why do modules interact the way they do?
4. **Algorithm deep-dives** — Step-by-step traces with complexity and tradeoff analysis
5. **Failure analysis** — Not just error types, but recovery strategies and cascading effects
6. **Inferred intent** — Reading between the lines of code to explain design philosophy

The root cause is that the research phase is a single shallow pass, and the generation prompt doesn't mandate depth or narrative voice.

---

## Design Decisions

| Decision | Choice | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| Research approach | Multi-pass (3 phases) | Single enhanced pass | Single pass hits context limits before achieving depth |
| Writing voice | Narrative (senior engineer to new team member) | Academic, tutorial, mixed | Most natural for "understanding" goal; matches user preference |
| Design inference | AI infers intent from code patterns | Only state explicit facts | Code rarely documents "why"; inference is essential for depth |
| Coverage vs depth | Comprehensive (20+ pages, full depth) | Selective deep-dives | User wants everything covered deeply |
| Template approach | New section types added to existing template structure | Completely new page layouts | Preserves working CSS/JS/navigation while adding depth sections |

---

## Research Phase — 3-Pass Architecture

### Pass 1: Broad Survey (enhanced existing)

**Purpose:** Map the codebase terrain — modules, dependencies, patterns, entry points.

**Research prompt asks for:**
- Complete module inventory with roles and responsibilities
- Dependency graph (who depends on whom, and WHY)
- Architectural patterns detected (plugin, observer, state machine, pipeline, etc.)
- Entry points and key execution paths
- Design decisions visible in code structure (inheritance hierarchies, abstractions, data structure choices)
- Technology stack and framework choices with rationale

**Output:** `_research/01-survey.md` — structured overview

### Pass 2: Per-Module Deep Analysis (new)

**Purpose:** For each major module, ask the "WHY" questions that create real understanding.

**Research prompt per module asks:**
- **Existence rationale:** Why does this module exist? What problem does it solve that couldn't be solved another way?
- **Design choices:** What key design decisions were made? What patterns are used and why?
- **Alternatives analysis:** What other approaches could have been taken? Why was this one chosen? (Infer from code patterns, naming, comments, commit history if available)
- **Algorithm identification:** What are the 2-4 key algorithms/mechanisms? Trace each step-by-step.
- **Data flow:** What data enters, how is it transformed, what exits? Why this transformation pipeline?
- **State management:** What state does this module own? How does it change? What invariants must hold?
- **Error philosophy:** How does this module handle failures? Is it fail-fast, fail-safe, retry-based? Why?
- **Performance characteristics:** What are the time/space tradeoffs? What was optimized for and what was sacrificed?
- **Edge cases:** What happens at boundaries? Under stress? With malformed input?

**Output:** `_research/02-deep-{module-name}.md` per module

### Pass 3: Cross-Module Synthesis (new)

**Purpose:** Understand the system as a whole — how parts compose into a working system.

**Research prompt asks:**
- **End-to-end flows:** Trace 3-5 key user scenarios from entry to exit, through all modules involved
- **Coupling analysis:** Where are modules tightly coupled? Is this intentional? What would break if you changed the interface?
- **Shared state inventory:** What state is shared across modules? How is consistency maintained?
- **Architectural philosophy:** What overarching principles guide the system design? (e.g., "favor correctness over performance", "plugin-first extensibility")
- **Evolution patterns:** How was the system likely built up? What was added later? (Infer from code layering, naming conventions, abstraction levels)
- **Integration patterns:** How do modules discover/communicate with each other? (DI, events, direct calls, shared bus?)

**Output:** `_research/03-synthesis.md`

---

## Content Architecture

### Page Types & Required Sections

#### L0 — Project Hub

| Section | Content | Min Length |
|---------|---------|-----------|
| **Project Philosophy** | Why this project exists, what problem it solves, what principles guide its design | 200 words |
| **Architecture Overview** | System-level Mermaid diagram with annotated edges explaining WHY each connection exists | 15+ nodes |
| **Design Decisions** | Table of 5-8 key architectural choices with alternatives and rationale | 5 rows |
| **How It All Fits Together** | Narrative walkthrough of the system's big picture, how modules compose | 300 words |
| **Module Cards** | Quick reference cards for each module with 1-sentence "why it exists" | all modules |
| **Key Data Flows** | 2-3 Mermaid sequence diagrams showing major end-to-end flows | 2 diagrams |

#### L1 — Module Overview

| Section | Content | Min Length |
|---------|---------|-----------|
| **Why This Module Exists** | Problem statement, design rationale, what the world looks like without it | 150 words |
| **The Senior Engineer's Tour** | Narrated walkthrough (10-14 steps) where each step explains WHY, not just WHAT. "If you removed this step, X would break because Y" | 14 steps |
| **Design Decisions** | Table of key choices: pattern used, alternatives, why this was chosen | 5 rows |
| **Architecture Diagram** | Module internals with annotated relationships | 10+ nodes |
| **Key Components** | Table with file paths, purpose, and "why it's designed this way" | 10 rows |
| **Algorithm Spotlight** | 2-3 key algorithms with brief trace and complexity analysis | 2 algorithms |
| **How This Module Connects** | Cross-module Mermaid diagram showing this module's role in the system | 1 diagram |
| **What Could Go Wrong** | Failure modes with detection → recovery → cascading effects | 4+ scenarios |
| **Performance Profile** | What's fast, what's slow, what was the intentional tradeoff | 100 words |

#### L2 — Sub-Module / Component Page

| Section | Content | Min Length |
|---------|---------|-----------|
| **Why This Component** | Why this exists as a separate component (not merged into parent) | 100 words |
| **Design Rationale** | Key implementation decisions and why | 3 decisions |
| **Annotated Code Walkthrough** | Real code with numbered callouts explaining each significant line/block | 1 walkthrough |
| **Interactions** | How this component talks to others, with WHY the interface looks this way | table |
| **Edge Cases & Boundaries** | What happens at limits, with empty input, during failures | 3+ cases |

#### Focus — Deep Dive Page

| Section | Content | Min Length |
|---------|---------|-----------|
| **The Problem** | What challenge does this mechanism solve? Why is it non-trivial? | 150 words |
| **The Approach** | How the authors solved it, explained narratively | 200 words |
| **Why Not Alternatives?** | Explicit comparison with 2-3 other approaches, with tradeoff table | 2 alternatives |
| **Step-by-Step Trace** | Walk through the algorithm with real code, annotated at each decision point | 8+ steps |
| **Mermaid Diagram** | State/sequence/flow diagram of the mechanism | 1+ diagrams |
| **Complexity & Tradeoffs** | Time/space analysis, what was optimized, what was sacrificed | 100 words |
| **Edge Cases** | Boundary conditions with "what actually happens when..." narratives | 3+ cases |
| **Failure Recovery** | How errors are detected and handled in this mechanism | 100 words |

---

## Writing Voice Guidelines

### Tone

The wiki reads like a **senior engineer writing a technical blog post** for a new team member. It's:

- **Conversational but precise** — uses "you" and "we", but never vague
- **Opinionated with evidence** — "This is a good design because X" rather than just "This does X"
- **Inference-friendly** — explicitly marks inferred intent: *"Based on the shadow memory pattern, the authors likely chose this over versioned snapshots because..."*

### Voice Examples

**❌ Current (shallow):**
> "The `MemCheck` plugin checks for memory access violations by tracking allocated regions."

**✓ Target (deep):**
> "Why shadow memory? The `MemCheck` plugin maintains a parallel 'shadow' of every allocated region. When your kernel accesses address X, MemCheck doesn't scan a list of valid regions — it jumps straight to the shadow slot for X in O(1). The authors could have used a sorted interval tree (O(log n) lookups) or a hash map (amortized O(1) but with rehashing stalls). Shadow memory trades 2x base memory for guaranteed constant-time checks with zero allocation jitter — the right call for a tool that instruments every single memory operation."

### Inference Markers

When the AI infers intent not explicitly stated in code/comments, it uses phrasing like:
- *"Based on the code structure, this was likely designed to..."*
- *"The choice of X over Y suggests the authors prioritized..."*
- *"Reading between the lines of the inheritance hierarchy..."*

This distinguishes fact from analysis while still providing the depth users need.

---

## Template Changes

### New CSS Classes

```css
.design-rationale    /* Design Decisions table container */
.why-box            /* "Why This Exists" explanation box */
.algorithm-trace    /* Step-by-step algorithm walkthrough */
.code-annotation    /* Annotated code with numbered callouts */
.tradeoff-table     /* Performance/design tradeoff comparison */
.alternatives-grid  /* Side-by-side alternatives comparison */
.failure-analysis   /* What Could Go Wrong section */
.inference-marker   /* "Based on code patterns..." italic marker */
```

### New Mermaid Diagram Types Required

- **Annotated dependency graphs** — edges have labels explaining WHY the dependency exists
- **State diagrams** — for lifecycle management, execution phases
- **Decision trees** — for algorithm branching points

---

## Pipeline Changes

### `run_wiki_gen.sh` Updates

```
Phase 1A: Broad Survey Research     → _research/01-survey.md
Phase 1B: Per-Module Deep Research  → _research/02-deep-{name}.md (per module)
Phase 1C: Cross-Module Synthesis    → _research/03-synthesis.md
Phase 2:  HTML Generation           → (using all research as context)
Phase 3:  Post-processing           → (existing: search index, nav, etc.)
Phase 4:  Integration               → (existing: update_index.py chain)
```

The key change: Phase 1 becomes three sub-phases, each building on the previous. The shell script orchestrates these as separate Copilot invocations, passing accumulated research forward.

---

## Quality Bar

A generated wiki page passes the quality bar when:

1. Every section answers "WHY" — not just "WHAT" or "HOW"
2. At least 2 design decisions are analyzed per module page
3. At least 1 alternative approach is compared per focus page
4. Code annotations explain intent, not just mechanics
5. Cross-module connections are explicit (not just "module A uses module B" but "module A uses module B because...")
6. A reader unfamiliar with the codebase could explain the design philosophy after reading the wiki
7. Inferred design rationale is clearly marked but present throughout

---

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `.github/skills/wiki-generator/SKILL.md` | **Rewrite** | Complete rewrite with 3-pass research, narrative voice, depth mandate |
| `resources/l0-template.html` | **Redesign** | Add philosophy, design decisions, data flows sections |
| `resources/l1-template.html` | **Redesign** | Add design rationale, algorithm spotlight, failure analysis sections |
| `resources/l2-template.html` | **Redesign** | Add component rationale, annotated code, edge cases sections |
| `resources/focus-template.html` | **Redesign** | Restructure for deep algorithm trace + alternatives comparison |
| `scripts/run_wiki_gen.sh` | **Modify** | Add Pass 2 and Pass 3 orchestration to research phase |

## Files NOT Changed

- Version switcher system (generate_versions.py, inject_version_switcher.py)
- update_index.py, fix_wiki_html.py
- Hub index.html
- Post-processing scripts (search index, navigation, etc.)
