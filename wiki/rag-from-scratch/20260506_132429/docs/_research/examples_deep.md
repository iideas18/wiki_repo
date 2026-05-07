# Phase 1B — Deep Analysis: `examples/`

## Existence Rationale

`examples/` is **the actual product of this repository** — `src/` is the
side-effect of stabilising what the lessons have proven. Every numbered
directory (00–06) is a self-contained, runnable lesson with three artefacts:
`example.js` (the runnable code), `CONCEPT.md` (the *why*), and `CODE.md`
(the line-by-line walk). A learner can read one lesson without having read
any other.

This separation exists because the project's promise — "no black boxes" —
demands that **you can stop at any chapter and still have a working RAG
system you understand end-to-end**. If the early lessons depended on
`src/`, the reader would have to chase imports across files. By keeping each
`example.js` standalone (sometimes at the cost of duplicating ~50 LOC), the
author optimises for *cognitive locality* — everything you need to read is
in one tab.

## Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|----------|-------------|------------------------|---------------------|
| Lesson granularity | Numbered 00–06 with sub-lessons under 04, 05, 06 | Flat 1..N; tagged by topic | Sub-numbering signals "this concept needs multiple passes" without dirtying the top-level. |
| Code/concept split | Three files per lesson (`example.js` + `CONCEPT.md` + `CODE.md`) | Markdown with embedded code; inline comments only | Lets readers choose their depth: skim concept → read code → run example. |
| First lesson | `00_how_rag_works` does keyword scoring, no embeddings | Start with embeddings | Demystifies RAG before introducing vector math. The reader sees retrieve+generate working without any "AI". |
| Vector DB choice | `embedded-vector-db` (HNSW, in-process) | Qdrant/Chroma/PG-vector (network) | Local-first; no Docker required; matches "from scratch" promise. |
| Embedding model | `bge-small-en-v1.5.Q8_0.gguf` (384-d, ~33MB) | OpenAI text-embedding-3-small | Local, no API keys, runs on CPU. |
| Self-contained vs imports | Each `example.js` re-imports `Document` & helpers; minimal cross-lesson import | One shared scaffold | Cognitive locality (above) trumps DRY. |
| Retrieval lessons | 5 sub-lessons (basic → query-prep → hybrid → multi-query → query-rewriting) | One mega-lesson | Each sub-lesson teaches one *technique* in isolation, then the next layers complexity. |
| Output styling | Heavy use of `chalk`/`ora`/`boxen` via `OutputHelper` | Plain `console.log` | The lessons are *demos*. Visible structure helps the reader follow what's happening. |

## Algorithm Deep-Dives

### 1. Naïve keyword retrieval (`examples/00_how_rag_works`)

```javascript
const matches = queryWords.filter(word => docWords.includes(word)).length;
```

**Problem statement.** Establish the *retrieve-then-generate* pattern with no
embeddings, no LLM call — pure function over arrays. Pedagogical only.

**Why this algorithm.** It's deliberately bad. Showing "this works for some
queries, fails for others" sets up the motivation for embeddings in lesson 04.

**Edge cases.** Filter `score > 0` so unmatched queries return nothing,
triggering the "I don't have enough information" branch. This same pattern —
"return nothing on low confidence" — recurs in every later retrieval lesson.

### 2. HNSW kNN search (used in 05+ via `embedded-vector-db`)

The library is a thin wrapper around an HNSW index. The lessons treat it as
a black box but **explain its parameters**: `ef_construction`,
`ef_search`, `M`. The 05 lessons demonstrate the *speed vs precision* knob
by varying `ef_search` and observing recall drop.

**Why HNSW.** Logarithmic-ish lookup vs O(n) brute force. For 10K vectors it
gives sub-millisecond search; for 100K still <10ms.

**Tradeoff acknowledged in the lessons.** Approximate — not guaranteed to
return the true top-k. Acceptable for retrieval where one false-near vs
true-near is rarely catastrophic.

### 3. Hybrid score normalisation (`examples/06/03_hybrid_search`)

When combining a dense (cosine, 0–1) score with a sparse (BM25, unbounded)
score, you can't add them directly. The example demonstrates **min-max
normalisation per list** before combining via weighted sum:

```
hybrid = α · norm(dense) + (1-α) · norm(sparse)
```

Then the dynamic-weight idea: detect "looks like a SKU" (regex) and bump
sparse weight; otherwise lean dense.

### 4. Reciprocal Rank Fusion (`examples/06/04_multi_query_retrieval`)

Implementation in `multi-query-retrieval.js`. Walked through in `src_deep.md`.
The example calls it via `retrieveParallel(queries) → rrfFuse(lists)`
combined with optional dedup by max score.

### 5. Query rewriting (`examples/06/05_query_rewriting`)

Two-pass: heuristic normalisation (lowercase, strip stop-words, expand
contractions) feeds into an LLM call (`LlamaPrompter`) that produces 1–3
rewritten queries. The rewritten queries then drive the multi-query
retriever from lesson 04.

**Why two-pass?** Heuristic alone misses semantic expansion ("car" →
"automobile, vehicle"). LLM alone is slow. Heuristic-first cleans cheaply;
LLM expands what's worth expanding.

## Error Philosophy

The lessons are **demonstrative, not defensive**. They throw on missing model
files (`Failed to initialize embedding model: …`), but they don't try to
recover from a missing GGUF — the user is supposed to read the error,
download the model per `DOWNLOAD.md`, and re-run. This matches the
educational stance: surface the failure, teach the fix.

## Performance Characteristics

The lessons are **interactive demos**. Cold start dominates (model load
~1–3s); subsequent operations are sub-second. Vector DB inserts are batched.
Output is paced with `ora` spinners so the reader sees what's happening.

## Evolution Clues

- The retrieval lessons (06) introduce *helper modules* (`logger.js`,
  `config.js`, `multi-query-retrieval.js`, `query-rewriter.js`) — only at
  this level of complexity does the lesson need >1 file. This is the
  **promotion frontier**: the next batch of code likely to migrate to
  `src/retrievers/`.
- `04_multi_query_retrieval` and `05_query_rewriting` are the only lessons
  with `config.js` files — the rest read paths inline. These are the
  lessons where the user is expected to *iterate* (try different prompts).
- The early lessons keep the vector DB tiny (5–20 sample docs); later
  lessons (`05/03`, `06/03`) scale to 100s of products to demonstrate
  performance behaviour.
