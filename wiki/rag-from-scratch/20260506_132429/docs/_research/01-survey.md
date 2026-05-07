# Phase 1A — Broad Survey: rag-from-scratch

**Source:** `/mnt/disk1/zy/rag/rag-from-scratch` · git `38e1a7a`
**Language:** JavaScript (ES Modules, Node 18+ assumed; `"type": "module"`)
**Scope:** ~1,705 LOC in `src/` + helpers + ~6,954 LOC of tutorial examples
**Generated:** 2026-05-06

## Project Identity

`rag-from-scratch` is an **educational, dependency-light Retrieval-Augmented
Generation toolkit** that doubles as (a) a layered, growing JavaScript library
and (b) a sequenced tutorial. Its sister project is *AI Agents from Scratch*
(linked in README) and the design philosophy is explicit: *"No black boxes. No
cloud APIs. Just clear explanations, simple examples, and local code you fully
understand."*

The project deliberately mirrors LangChain.js's class-shape (`Document`,
`BaseLoader.load()`, `BaseTextSplitter.splitText()`, `Embeddings.embedQuery()`,
`BaseLLM.invoke()/stream()`) so that learners can transfer concepts later — but
strips away the abstractions, registries, and integrations that make LangChain
intimidating to a first-time reader.

## Depth Detection

Top-level functional dirs containing source files:

| Dir | Purpose | Has sub-dirs with code? |
|-----|---------|------------------------|
| `src/` | Reusable RAG library | YES (10 sub-dirs: chains, chat-models, embeddings, llms, loaders, prompts, retrievers, text-splitters, utils, vector-stores) |
| `examples/` | Numbered tutorial walkthrough | YES (00–06, several with sub-lessons) |
| `helpers/` | CLI prompter + output utilities | NO (3 flat files) |
| `models/` | GGUF model storage (`.gitkeep`) | NO |
| `images/` | Diagrams used in README | NO |

**Decision: 3-level wiki.** L0 hub → L1 module overviews (`src`, `examples`,
`helpers`) → L2 deep-dives for substantive sub-modules. `helpers/` is a
**flat L1** (3 files, no sub-dirs).

## Implementation Maturity Map

A striking observation from the file-size scan: **many `src/` files are empty
stubs.** This is not a bug — it's a roadmap. The author has scaffolded the
LangChain-shaped class taxonomy but only filled in the layers needed for the
current set of tutorials.

| Sub-module | Files filled | Files stubbed | Maturity |
|------------|-------------|---------------|----------|
| `embeddings/` | 2 (745 LOC) | 0 | **Mature** — caching + LangChain-shaped wrapper |
| `text-splitters/` | 4 (200 LOC) | 0 | **Mature** — Base / Character / Recursive / Token |
| `loaders/` | 2 (200 LOC) | 3 (`DirectoryLoader`, `TextLoader`, `PDFLoader`) | **Partial** — only PDFLoader implemented; others scaffolded |
| `llms/` | 3 (151 LOC) | 0 | **Mature** — BaseLLM + LlamaCpp |
| `chat-models/` | 1 (32 LOC) | 0 | **Minimal** — single ChatLlamaCpp |
| `utils/` | 3 (130 LOC) | 3 (`similarity.js`, `tokenizer.js`, `validators.js`) | **Partial** |
| `chains/`, `retrievers/`, `vector-stores/`, `prompts/` | index.js only | All class files empty | **Stub** — interface promised, not yet implemented |

The retrievers, vector-stores, and chains are **studied in the examples
directory rather than implemented in `src/`**. That's the educational rhythm of
this repo: each concept is first taught as a self-contained `example.js`
(complete with embedded `Document`, vector DB, retrievers), then *promoted* to
`src/` once stable.

## Cross-Module Dependencies

```
examples/*       → src/index.js (Document, PDFLoader)
                 → helpers/output-helper.js (chalk/ora UX)
                 → embedded-vector-db (npm)
                 → node-llama-cpp (npm)

src/index.js     → re-exports all sub-module index.js
src/embeddings/  → node-llama-cpp · crypto · fs/promises
src/loaders/     → pdf-parse · src/utils/Document
src/text-splitters/ → src/utils/Document (only)
src/llms/        → node-llama-cpp · src/utils/llama_cpp
src/chat-models/ → src/llms/LlamaCpp
helpers/         → openai · node-llama-cpp · chalk · ora
```

Two things stand out: (1) the **`Document` class is the universal currency** —
everything that flows between modules is either a `Document` or a
`number[]`/`Float32Array` (embedding vector); (2) `examples/` does NOT import
from each other — every lesson is **standalone runnable**, even when that means
duplicating ~50 LOC of boilerplate.

## Module Reports

### src/embeddings — Mature
- **Purpose:** Convert text → fixed-dimension vectors via local llama.cpp.
  Adds an LRU + persistent cache around the raw embed call.
- **Key Classes:** `EmbeddingModel`, `EmbeddingCache`.
- **Algorithms:** SHA-256 keyed lookup; LRU by `lastAccessed`; batch parallel
  embedding via `Promise.all(batch.map(...))`; cosine similarity (manual loop).
- **Knobs:** `modelPath`, `dimensions=384`, `batchSize=32`, `cache=true`,
  `maxSize=10000`, `useHash=true`, `hashAlgorithm='sha256'`.
- **Design decisions visible:** caches on the **text key**, not the (text +
  model) key — implies single-model usage; `useHash=true` default trades
  privacy/length for fixed-size keys.

### src/text-splitters — Mature
- **Purpose:** Split long text into overlapping chunks suitable for embedding.
- **Key Classes:** `BaseTextSplitter`, `CharacterTextSplitter`,
  `RecursiveCharacterTextSplitter`, `TokenTextSplitter`.
- **Algorithm:** Recursive splitter tries separators in priority order
  `['\n\n', '\n', '. ', ' ', '']`, falling through to finer granularity when a
  chunk overflows `chunkSize`. The `mergeSplits` helper enforces overlap by
  shifting the front of `current[]` while `length > chunkOverlap`.
- **Knobs:** `chunkSize=1000`, `chunkOverlap=200`, `separators[]`,
  `lengthFunction`, `encodingName='cl100k_base'`.
- **Design decisions visible:** `TokenTextSplitter` approximates token count as
  `chars / 4` rather than calling tiktoken — keeps the dependency surface
  zero. The `lengthFunction` injection is the seam that lets a real tokenizer
  drop in later.

### src/loaders — Partial
- **Purpose:** Read raw bytes/files and emit `Document[]`.
- **Key Classes:** `BaseLoader` (abstract), `PDFLoader`.
- **Stubs:** `DirectoryLoader`, `TextLoader`.
- **Mechanism:** `PDFLoader` wraps `pdf-parse`'s `PDFParse`. With
  `splitPages:false` it yields **one** `Document`; with `splitPages:true` it
  iterates pages and emits one Document per page with `metadata.page`.
- **Helper functions:** `cleanText` (whitespace + newline collapse),
  `constructDocument` (metadata builder).
- **Design decisions visible:** `loadAndSplit(splitter)` convenience method
  short-circuits to `load()` if no splitter is passed — explicitly modelled on
  LangChain.

### src/llms — Mature
- **Purpose:** Local LLM completion / streaming via node-llama-cpp.
- **Key Classes:** `BaseLLM` (abstract), `LlamaCpp` (concrete).
- **Mechanism:** `LlamaCpp.initialize()` is a static factory that wires
  `getLlama() → loadModel() → createContext() → createSession()` and optionally
  builds a GBNF grammar. `invoke()` delegates to `session.prompt()`. `stream()`
  is currently a *fake stream* — it collects tokens via the `onToken` callback
  then yields them after generation completes.
- **Knobs:** `contextSize=2048`, `batchSize=512`, `threads=4`, `maxTokens`,
  `temperature`, `topK`, `topP`, `gpuLayers`, `gbnf`.

### src/utils — Partial
- **Purpose:** Cross-cutting helpers and shared types.
- **Key:** `Document` (the canonical text+metadata pair); `llama_cpp.js`
  (factory functions `createLlamaModel/Context/Session/Grammar`).
- **Stubs:** `similarity.js`, `tokenizer.js`, `validators.js`.

### src/chat-models — Minimal
- `ChatLlamaCpp extends LlamaCpp` and adds a single `_formatMessagesToPrompt()`
  that joins `[{role, content}]` into `role: content\n…` lines. It's
  intentionally shallow — proves the inheritance shape works.

### src/chains, retrievers, vector-stores, prompts — Stub
- Only `index.js` exists with named-export `{ }` placeholders. These are the
  layers that the **examples teach** — they are not yet generalised into `src/`.

### examples/ — The actual curriculum
Numbered 0–6, each lesson is `example.js` + `CONCEPT.md` + `CODE.md`. The
`CONCEPT.md` explains the WHY in markdown; `CODE.md` is a code-walk; `example.js`
is runnable end-to-end. Total ~6,954 LOC across 15 lessons.

| # | Topic | LOC | Notes |
|---|-------|-----|-------|
| 00 | How RAG Works | 68 | Pure JS, no embeddings — keyword score |
| 01 | LLM basics (node-llama-cpp + wrapper) | 224 | Two sub-lessons |
| 02 | Data Loading | 98 | PDF parsing |
| 03 | Text Splitting & Chunking | 355 | Comparison of strategies |
| 04 | Embeddings (similarity → generation) | 884 | Two sub-lessons |
| 05 | Vector Store (3 sub-lessons) | 1,973 | embedded-vector-db |
| 06 | Retrieval Strategies (5 sub-lessons) | 3,352 | Basic, query-prep, hybrid, multi-query, query-rewrite |

### helpers/ — Flat (3 files, 152 LOC)
- `OutputHelper` — chalk/ora wrappers, `runExample()`, `analyzeChunks()`,
  `withSpinner()`. Powers the rich CLI output of every example.
- `OpenAIClient` — minimal wrapper around the OpenAI SDK's
  `client.responses.create({model, input})`.
- `LlamaPrompter` — a simpler `LlamaCpp` cousin used directly by the
  retrieval-strategy examples for query rewriting.

## Terminology

- **RAG** — Retrieval-Augmented Generation: retrieve relevant context from a
  knowledge store, then feed it to an LLM as part of the prompt.
- **Embedding** — fixed-length real-valued vector (here: 384-dim, from
  `bge-small-en-v1.5`).
- **Chunk** — a sub-document produced by a splitter; the unit indexed in the
  vector store.
- **Vector store / Namespace** — the keyed collection storing
  `{vector, metadata}` rows; this project uses `embedded-vector-db` (HNSW).
- **Cosine similarity** — `dot(a,b) / (|a|·|b|)`, the default similarity metric.
- **HNSW** — Hierarchical Navigable Small World, the approximate-NN index used.
- **kNN** — k-nearest-neighbours search.
- **Reciprocal Rank Fusion (RRF)** — combine multiple ranked lists by summing
  `1 / (k + rank + 1)`. Used in multi-query retrieval.
- **Hybrid search** — combine dense (semantic) + sparse (keyword/BM25) results.
- **Reranker** — a second-stage scorer (often a cross-encoder) that re-orders
  top-N retrieved candidates.
- **Multi-query retrieval** — generate paraphrases of a query, retrieve for
  each, fuse the results.
- **Query rewriting** — heuristic or LLM-driven normalisation/expansion of the
  user query before retrieval.
- **GGUF** — the quantised model file format consumed by llama.cpp.
- **GBNF** — llama.cpp's grammar language used to constrain generation.
- **Document** — `{pageContent, metadata, id?}` — the universal payload.
- **LRU cache** — least-recently-used eviction policy used in `EmbeddingCache`.
- **Sliding-window chunking** — chunk strategy with `chunkOverlap`-character
  overlap between adjacent chunks (preserves cross-boundary context).

## Architectural Patterns Observed

1. **Abstract-base + concrete subclass** (`BaseLoader → PDFLoader`,
   `BaseLLM → LlamaCpp`, `BaseTextSplitter → CharacterTextSplitter`). Why:
   matches LangChain.js verbatim, lowering the cost of "graduating" learners
   to that ecosystem.
2. **Static async factory** (`LlamaCpp.initialize()`). Why: constructors can't
   `await`, but the model load is a multi-step async pipeline. The factory
   keeps the constructor cheap and the load atomic.
3. **Optional caching layer** (`EmbeddingCache` injected into `EmbeddingModel`).
   Why: caches are pure side-channels — they can be added/removed without
   changing the call signature.
4. **Functional helpers in examples** (`rrfFuse`, `withTimeout`, `withRetry`).
   Why: pedagogical clarity. A class hierarchy would obscure that RRF is a
   one-equation algorithm.
5. **Index re-export barrels** (every sub-module has `index.js`). Why: lets the
   top-level `src/index.js` do `export * from './embeddings/index.js'` and gives
   consumers a single import surface.
6. **`type: module` ESM throughout** — no Babel/TS toolchain. Why: keeps the
   "no black boxes" promise; readers can `node example.js` directly.

## Stat Snapshot

| Metric | Value |
|--------|-------|
| Total `.js` files | 70 |
| Total LOC (`src/` + helpers) | ~1,857 |
| Total LOC (examples) | ~6,954 |
| Sub-module dirs in `src/` | 10 |
| Tutorial lessons | 15 (numbered 00–06) |
| External runtime deps | 8 (chalk, ora, openai, node-llama-cpp, pdf-parse, embedded-vector-db, dotenv, node-fetch, boxen) |
| Tested concrete classes | `EmbeddingModel`, `EmbeddingCache`, `PDFLoader`, `BaseTextSplitter`, `Character/Recursive/TokenTextSplitter`, `LlamaCpp`, `ChatLlamaCpp`, `Document` |
| Empty stub files | 12 |
