# Phase 1B — Deep Analysis: `src/`

## Existence Rationale

`src/` is the **library half** of the project — the code a downstream consumer
would `npm install` and import from. It exists as a separate unit (vs. just
publishing the `examples/`) because the author wants to **train two muscles at
once**: (1) explain a concept end-to-end in a single self-contained
`example.js`, then (2) extract the stable abstractions into a layered library
that mirrors LangChain.js. Without `src/`, every example would re-implement
`Document`, the splitter base, and the embedding cache — making the
educational arc collapse into a flat pile of scripts.

The current `src/` is **deliberately partial**: only the layers that the first
six lessons depend on are filled in (`embeddings`, `text-splitters`, `loaders`,
`llms`, `utils`). The empty `chains/`, `retrievers/`, `vector-stores/`, and
`prompts/` are scaffolded with named-export `index.js` files — they hold a
*place* in the import graph for future lessons.

## Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|----------|-------------|------------------------|---------------------|
| Class shape | LangChain.js naming (`Document`, `BaseLoader.load()`, `embedDocuments/embedQuery`) | Custom names; functional API only | Lower cognitive cost when learners graduate to LangChain proper. |
| Async setup | Static factory `LlamaCpp.initialize()` returning the instance | `new LlamaCpp(); await x.init();` two-step | Atomic init prevents "half-constructed" instances escaping. JavaScript can't `await` in a constructor. |
| Cache key | SHA-256 hash of the text alone | (text + modelPath); raw text | Single-model usage assumed; fixed-length keys simplify on-disk JSON cache. Hash hides the original text in dumps unless `useHash=false`. |
| Cache eviction | LRU by `lastAccessed` | LFU; FIFO; weighted by length | LRU is the right default for "frequently re-asked" queries during interactive RAG sessions. |
| Splitter overlap | `mergeSplits()` shifts the front of `current[]` while `length > chunkOverlap` | Re-slice from end of previous chunk | The shift-front approach yields **char-accurate** overlap regardless of separator; the alternative would tangle with separator stripping. |
| Token estimation | `chars / 4` heuristic in `TokenTextSplitter` | Bundle tiktoken; ship a wasm tokenizer | Zero-dependency. Acceptable error band for chunk-size budgeting (real BPE tokens average ~4 chars in English). |
| Streaming impl | Collect tokens via callback, then yield (fake stream) | Use a queue/AsyncIterator with backpressure | Educational placeholder — true streaming requires plumbing `onToken` through an async iterator; left as a future exercise. |
| ESM throughout | `"type": "module"` + relative `./Foo.js` imports | CommonJS; bundled UMD | "No black boxes" — `node example.js` works without any build step. |

## Algorithm Deep-Dives

### 1. Recursive separator-aware text splitting (`RecursiveCharacterTextSplitter.splitText`)

**Problem.** Cut a long text into chunks ≤ `chunkSize` while keeping logical
boundaries (paragraphs > sentences > words > characters). A naïve
`text.match(/.{1,1000}/g)` would slice mid-word and destroy meaning at every
chunk boundary.

**Step-by-step.**
1. Pick the **most coarse** separator that actually appears in the text by
   walking `['\n\n', '\n', '. ', ' ', '']` left-to-right.
2. `splits = text.split(separator).filter(Boolean)` — drop empty pieces.
3. For each `s`: if `lengthFunction(s) ≤ chunkSize`, append to `temp`.
4. Otherwise, flush `temp` via `mergeSplits()` (with overlap), and **recurse**
   into `s` with the next finer separator list.
5. After the loop, flush remaining `temp`.

**Complexity.** `O(N · log_S(N))` where `N = text length`, `S = avg split fanout`. In
practice each recursion level processes a small minority of the text, so the
constant factor is dominated by the outermost split.

**Why this algorithm.** Alternatives: (a) hard char-window — destroys
boundaries; (b) sentence tokenizer (regex on `[.!?]\s`) — misses code/markup;
(c) NLP sentencizer — adds dependency. Recursive separators is the
LangChain-standard middle ground: respects structure when present, degrades
gracefully when not.

**Edge cases.** Empty text → no chunks. Single huge token (no separators
present) → falls through to `''` separator and outputs the raw oversize
string (better than raising). `chunkOverlap >= chunkSize` → constructor
throws.

### 2. LRU eviction in `EmbeddingCache._evictLRU`

**Problem.** Bounded cache must drop the *least-useful* entry when full.

**Step-by-step.** Linear scan over `Map.entries()`, tracking `oldestTime` and
`oldestKey`. After loop: `cache.delete(oldestKey); stats.evictions++`.

**Complexity.** `O(n)` per eviction. Acceptable because evictions are rare on
the hot path — most queries hit. A doubly-linked-list LRU (`O(1)`) would be
faster but adds 30+ lines of bookkeeping.

**Why this algorithm.** Pedagogical: anyone reading the source can grok
"linear scan, smallest wins" instantly. The author traded asymptotic
optimality for readability.

### 3. Cosine similarity (`EmbeddingModel._cosineSimilarity`)

```javascript
for (let i = 0; i < vec1.length; i++) {
  dotProduct += vec1[i] * vec2[i];
  mag1 += vec1[i] * vec1[i];
  mag2 += vec2[i] * vec2[i];
}
return dotProduct / (Math.sqrt(mag1) * Math.sqrt(mag2));
```

**Why a manual loop?** A vectorised `Float32Array` + SIMD would be faster, but
the manual loop is **textbook** — it makes the formula
`(a · b) / (‖a‖ · ‖b‖)` legible to a learner who's just heard "vectors".
Length mismatch throws explicitly. Zero magnitude returns `0` rather than
NaN.

### 4. Reciprocal Rank Fusion (`examples/06_*/multi-query-retrieval.rrfFuse`)

**Problem.** When you run the same retrieval against multiple paraphrased
queries, you get N ranked lists. RRF combines them into a single ranking
that's robust to which list each doc came from.

**Formula.** `score(d) = Σ_lists 1 / (k + rank(d, list) + 1)` with `k=60`
(industry default).

**Why RRF over score-fusion?** Raw similarity scores from different queries
aren't directly comparable (different denormalisation). Rank-based fusion
sidesteps the calibration problem entirely. It's the *Bayes-classifier-by-rank*
of retrieval ensembles.

## Error Philosophy

`src/` is **fail-fast at the boundaries, fail-soft inside**:

- Constructors / `initialize()` throw immediately on missing `modelPath` or
  invalid `chunkOverlap >= chunkSize`. The user is told before any work begins.
- `_ensureInitialized()` throws if a method is called before
  `initialize()` — prevents silent NPEs deep in llama.cpp.
- The cache, by contrast, **never throws**: cache miss returns `null`, the
  caller falls through to the model. A side-channel that fails should never
  break the primary path.
- `LlamaCpp.invoke()` wraps llama.cpp errors in a higher-level
  `Error("LlamaCpp invoke failed: …")` — preserves the cause but tags the
  origin so a user staring at a stack trace knows which layer surfaced it.

## Performance Characteristics

**Fast paths.** Cache hits in `EmbeddingModel.embedQuery()` are O(1) Map lookup
plus SHA-256 (≈5µs for short text). Batch embedding parallelises within a
batch via `Promise.all` — wall-clock is bound by the slowest item, not the
sum. Splitter `mergeSplits()` is a single O(N) pass.

**Slow paths.** Cold model load (`LlamaCpp.initialize`) is ~1–3s for a 1B
parameter quantised model. Embeddings of fresh text route through llama.cpp's
`getEmbeddingFor()` (~10–50ms per call depending on model and CPU).

**Memory.** `EmbeddingCache` is bounded by `maxSize` entries (default 10,000).
At 384 dims × 4 bytes = ~1.5KB per entry → ~15MB at full capacity. Disk dumps
write JSON (verbose but trivially loadable).

## Evolution Clues

- The empty `chains/`, `retrievers/`, `vector-stores/`, `prompts/`
  directories — each with a hollow `index.js` — strongly suggest the author
  is following the lesson curriculum and will fill these in as lessons 06+
  stabilise. The shape of the future code is already implied.
- `extractTextFromPDF` at the bottom of `PDFLoader.js` is annotated
  `@deprecated` and labelled "legacy function" — evidence the file went
  through a refactor from procedural to class-based.
- `RecursiveCharacterTextSplitter` constructs a `new
  RecursiveCharacterTextSplitter({ ...this, separators: nextSeparators })` —
  the `...this` spread leaks every property including `cache`-related fields
  if added later. Minor smell that suggests this code predates the splitter
  hierarchy.
- The "fake stream" implementation in `LlamaCpp.stream()` (collect-then-yield)
  looks like a placeholder — a TODO without the comment.
