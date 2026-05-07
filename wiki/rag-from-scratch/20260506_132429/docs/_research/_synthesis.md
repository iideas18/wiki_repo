# Phase 1C — Cross-Module Synthesis

## End-to-End Flows

### Flow A — A learner runs `examples/00_how_rag_works/example.js`

```
node example.js
    ↓
example.js [self-contained]
    ↓ (no src/ imports — pure JS)
naiveKeywordSearch()    → returns top-2 docs by keyword overlap
generateAnswer()        → string-concat the retrieved docs
console.log(…)
```

**No cross-module dependency.** The reader can stop here and still understand
the *retrieve-then-generate* shape. Latency: ~0ms (no model loading).

### Flow B — A learner runs `examples/03_text_splitting_and_chunking/example.js`

```
example.js
    ↓ imports
src/index.js → src/loaders/PDFLoader, src/utils/Document
helpers/output-helper.js → OutputHelper
    ↓
PDFLoader('https://…/foo.pdf').load() → Document[]
    ↓ (uses pdf-parse from npm)
inline TextSplitter (re-implemented in example) → Document[] (chunked)
OutputHelper.formatChunkPreview() → terminal output
```

This is a **hybrid lesson**: it imports `Document` and `PDFLoader` from
`src/` (the parts that already exist) but **re-implements the splitter
inline** (because that's what's being taught this lesson). When the reader
moves to lesson 04, the splitter has been "promoted" and they import it from
`src/text-splitters`.

### Flow C — A learner runs `examples/05_building_vector_store/01_in_memory_store/example.js`

```
example.js
    ↓
const llama = await getLlama({logLevel:"error"})        // ~1s cold start
const model = await llama.loadModel({modelPath: bge-small.gguf})  // ~500ms
const ctx = await model.createEmbeddingContext()
    ↓
const db = new VectorDB({dimensions: 384, max: 10000})
    ↓ for each Document
ctx.getEmbeddingFor(text).vector → number[384]
db.insert(NS, vector, metadata)
    ↓ user query
ctx.getEmbeddingFor(query).vector
db.search(NS, qvec, topK=5) → [{vector, metadata, similarity}]
    ↓
OutputHelper.formatStrategyComparison(…)
```

**Latency profile.** Cold start ≈1.5s. Per-doc embed ≈10–30ms. Insert ≈0.5ms.
Search ≈1–5ms over 10K vectors (HNSW).

### Flow D — A learner runs `examples/06_retrieval_strategies/04_multi_query_retrieval/example.js`

```
user query
    ↓ (LLM rewrite, see 06/05)
queries = [original, paraphrase1, paraphrase2]
    ↓ retrieveParallel(queries, {getEmbedding, search, namespace, topK:5})
parallel: [embed→search] × 3
    ↓ rrfFuse(resultLists, k=60)
ranking[]  →  top-N  →  feed to LLM as context  →  generate answer
```

This is the **mature pipeline**: parallel multi-query retrieval, fusion,
context augmentation. The example is 943 LOC — the longest in the repo.

### Flow E — A consumer using the library: `import { PDFLoader, RecursiveCharacterTextSplitter, EmbeddingModel } from 'rag-from-scratch'`

```
const docs    = await new PDFLoader(url).load()
const chunks  = await new RecursiveCharacterTextSplitter().splitDocuments(docs)
const embeds  = new EmbeddingModel({modelPath:'…'}); await embeds.initialize()
const vectors = await embeds.embedDocuments(chunks.map(c=>c.pageContent))
// store in user's preferred vector DB
```

Notice what's missing: `vector-stores`, `retrievers`, `chains`. A consumer
today still has to write this layer themselves. **The library is honest about
its current state** by exporting empty index.js modules — the imports work,
they just don't yield classes yet.

## Coupling Analysis

| Boundary | Type | Risk if changed |
|----------|------|-----------------|
| `Document` shape (`{pageContent, metadata, id?}`) | Used by every loader, splitter, retriever, example | **CRITICAL.** Changing this would ripple to ~70 files. Stable for that reason. |
| `Embeddings.embedQuery(text) → number[]` and `embedDocuments(texts) → number[][]` | LangChain-shaped | **Stable.** Mirrors LangChain — diverging would defeat the promotion path. |
| `BaseLoader.load() → Document[]` | One concrete impl (PDFLoader) | **Loose.** Adding TextLoader/DirectoryLoader is additive. |
| `BaseTextSplitter.splitText() / splitDocuments()` | Three concrete impls | **Stable.** `lengthFunction` injection is the deliberate seam. |
| `BaseLLM.invoke / stream / batch` | One concrete impl (LlamaCpp) | **Loose.** Streaming is currently a placeholder — could be replaced without breaking callers. |
| `examples/*/example.js` ↔ `helpers/output-helper.js` | Style coupling | **Cosmetic.** OutputHelper changes wouldn't break logic. |
| `examples/06/04` ↔ `multi-query-retrieval.js` (sibling file) | Functional helper colocation | **Tight but contained.** This is the promotion candidate for `src/retrievers/`. |

## Architectural Philosophy

Three principles are visible in the code, not just the README:

1. **Cognitive locality > DRY.** Lessons re-implement what they teach.
   `examples/03/example.js` writes its own `TextSplitter` even though
   `src/text-splitters/BaseTextSplitter.js` exists. *Rationale:* a reader
   can understand lesson 03 without ever opening `src/`. DRY would force
   tab-jumping.
2. **LangChain.js as North Star.** Class names, method signatures, and even
   `loadAndSplit(splitter)` convenience methods are copied verbatim. The
   library is teaching LangChain's *shape* without LangChain's *weight*.
3. **Local-first, no API keys.** Every default path uses node-llama-cpp +
   GGUF + embedded-vector-db. OpenAI is supported but optional
   (`openai-prompter.js` only used where rewriting benefits from a strong
   model). Keeps the project runnable on a laptop with no internet.

## Shared State Inventory

There is **no global state** in `src/` — every class owns its instance
state, every example creates fresh `VectorDB`/`EmbeddingModel` instances.
The only "shared state" is on disk:

- `models/*.gguf` — quantised model files (downloaded per `DOWNLOAD.md`,
  read by `LlamaCpp` and `EmbeddingModel`).
- Persisted embedding cache JSON (`EmbeddingCache.saveToDisk` / `loadFromDisk`).
- `.env` (`OPENAI_API_KEY`).

This statelessness is a deliberate design call. RAG systems have a reputation
for hidden global registries (LangChain's `registerLLM`, etc.). This project
takes the opposite stance: **everything is explicit, every dependency is
constructor-injected**.

## System Evolution

The "core" of the system — the part that's stable, depended-upon, and unlikely
to change — is the `Document` class (40 LOC). Around it, layers were added
in this likely order:

1. `Document` — the universal payload. (Earliest, most stable.)
2. `PDFLoader` + `BaseLoader` — needed by lesson 02.
3. `BaseTextSplitter` + `RecursiveCharacterTextSplitter` — needed by lesson 03.
4. `EmbeddingModel` + `EmbeddingCache` — needed by lesson 04.
5. `LlamaCpp` + `BaseLLM` + `llama_cpp.js` — needed by lesson 06.
6. `helpers/` — emerged once the same chalk/ora boilerplate appeared in 5+
   lessons.

What's coming next (visible from the empty stubs):
- `src/retrievers/` — promotion target for `multi-query-retrieval.js` and the
  hybrid/rerank logic in lessons 06/02–04.
- `src/vector-stores/InMemoryVectorStore.js` and `LanceDBVectorStore.js`,
  `QdrantVectorStore.js` — wrappers around `embedded-vector-db` and the two
  external systems.
- `src/chains/RAGChain.js` — the "everything plugged together" convenience.
- `src/prompts/PromptTemplate.js` — already implied by `src/prompts/templates/`.

The project is therefore a **work-in-progress library tracking a finished
curriculum**. Reading the empty files tells you where the author plans to
stabilise next.

## Key Insight

> **The most useful sentence to remember:** "Examples teach, src crystallises,
> helpers ornament." Every cross-module decision falls out of that ordering.
