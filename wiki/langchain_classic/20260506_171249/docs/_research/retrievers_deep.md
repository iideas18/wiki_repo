# Phase 1B Deep Analysis — `retrievers/`

## Existence rationale

`retrievers/` is the home of **strategies that wrap a vectorstore (or any document source) and produce relevant documents for a query**. A bare vectorstore exposes only `similarity_search`; production RAG systems need re-ranking, query expansion, ensemble fusion, parent-context retrieval, time-decayed scoring, and structured-filter inference. Each of these is a *strategy*, not a vendor — they apply uniformly to Pinecone, Chroma, FAISS, etc. By separating the strategy layer from the storage layer, `retrievers/` lets users compose techniques (multi-query → contextual compression → ensemble fusion) without touching the underlying store.

## Design decisions visible in the code

| Decision | Choice made | Plausible alternatives | Inferred rationale |
|---|---|---|---|
| Retriever interface | `BaseRetriever` is a `Runnable[str, list[Document]]` | Custom protocol | Lets retrievers compose with LCEL: `retriever \| prompt \| llm` |
| Strategy as wrapper | Each strategy holds a `base_retriever` | Subclass per-store | Keeps retrievers store-agnostic (works with any `BaseRetriever`) |
| Parent-document mechanism | Two splitters (parent + child) + a `ByteStore` for parents + a vectorstore for children | One vectorstore with chunk hierarchy | Decouples storage of the retrieved unit from the searched unit; parent text never enters the embedding model |
| MultiQuery generation | LLM rewrites the user's query into N variants | Embedding-side query augmentation | LLM rewrites capture *intent* (synonyms, expansions); embedding tricks don't generalise |
| Ensemble fusion algorithm | Reciprocal Rank Fusion (RRF) | Borda count; weighted mean of similarity | RRF is robust to scale differences across retrievers (BM25 vs embeddings); doesn't need probability calibration |
| Self-query language | LLM emits a structured `StructuredQuery(query=str, filter=Comparison/Operation)` | Free-form filter strings; SQL | A typed AST is parsable into vendor-specific filter syntax (Pinecone, Chroma, Weaviate) |
| Contextual compression pipeline | List of `BaseDocumentCompressor`s applied in order | Single compressor | Pipeline composition: redundancy filter → embedding filter → LLM extractor |
| Time-weighted scoring | `salience(doc) = sim(doc) + decay_rate^hours_since_access` | Hard cutoff window | Smooth recency boost preserves "old but very relevant" docs |

## Algorithm deep-dives

### 1. ParentDocumentRetriever

**Problem.** Embedding a 5-page document loses local detail; embedding 200-token chunks loses surrounding context. We want to **search small, return large**.

**Trace.**
1. **Ingestion:** for each parent doc:
    - Optional `parent_splitter` → list of "parent chunks" (e.g., paragraph-sized).
    - Each parent chunk is split with `child_splitter` into "child chunks" (e.g., 200 tokens).
    - Child chunks get an embedding + parent ID metadata; stored in `vectorstore`.
    - Parent chunks (text) stored in a `ByteStore` keyed by parent ID.
2. **Retrieval:** query → `vectorstore.similarity_search` returns matching child chunks → look up parent IDs → fetch parents from byte-store → de-dupe → return parents.

**Complexity.** Index: O(N_children) embeddings. Query: O(top_k) byte-store fetches. Top-k of children may yield <top_k unique parents.

**Why this design.** It separates *what we search over* (small, embedding-friendly chunks) from *what we return* (large, model-friendly chunks). The byte-store avoids re-storing the same parent text inside every child's metadata.

### 2. EnsembleRetriever / RRF

**Problem.** A vector retriever excels at semantic match; BM25 excels at exact lexical match. Neither is universally better. Combine them so the best of both ranks high.

**RRF formula:**
```
score(doc) = Σ_i  1 / (k + rank_i(doc))
```
where `rank_i` is doc's position in retriever i's ranked list (1-indexed) and `k` is a smoothing constant (default 60).

**Trace.**
1. Run all child retrievers in parallel (async).
2. For each retriever, rank its returned docs.
3. For each (retriever, doc) pair, accumulate `1/(k+rank)` into doc's score (de-duplicated by content hash or doc ID).
4. Sort by combined score descending; return top-k.

**Why RRF.** It avoids the calibration problem: vector cosine and BM25 scores aren't directly comparable. Rank-only fusion sidesteps this. The `k=60` constant prevents the top-1 of each retriever from dominating.

### 3. SelfQueryRetriever

**Problem.** A user asks *"comedies from the 90s with rating > 8"*. We have a vectorstore with `genre`, `year`, `rating` metadata. A pure embedding search won't filter on `year > 1990` reliably.

**Trace.**
1. LLM is shown:
    - `metadata_field_info` (each filterable field with name, type, description).
    - `document_contents` description.
    - The user query.
    - Output schema: `{"query": str, "filter": Operation|Comparison|None}`.
2. LLM emits structured query. Filter is a tree of `Comparison(comparator, attribute, value)` and `Operation(operator, arguments)`.
3. The retriever's `structured_query_translator` (vendor-specific: `ChromaTranslator`, `PineconeTranslator`, …) lowers the AST to native filter syntax.
4. Vectorstore is called with the rewritten query string + native filter.

**Why an AST.** Without it, LangChain would need an LLM-specific prompt for each vendor's filter dialect. The AST + per-vendor translator pattern keeps the LLM prompt vendor-agnostic.

### 4. ContextualCompressionRetriever

**Problem.** A retriever returns 10 docs with 800 tokens each — 8000 tokens of context. Half is irrelevant noise. Compress before passing to the answering LLM.

**Pipeline.** A list of `BaseDocumentCompressor`s:
- `EmbeddingsRedundantFilter` — drops docs whose embedding is >0.95 similar to a doc already kept (de-dup near-duplicates from chunking).
- `EmbeddingsFilter` — drops docs whose embedding similarity to query is below threshold (cheap cull).
- `LLMChainExtractor` — calls an LLM per doc to extract just the spans relevant to the query.
- `LLMChainFilter` — calls an LLM with yes/no per doc.
- `CrossEncoderReranker` — rescore with a cross-encoder model (slow but accurate).

Compressors are applied in order; a typical pipeline is `EmbeddingsFilter → LLMChainExtractor` (cheap cull then expensive extract).

## Error philosophy

**Best-effort, partial results.** A failing child retriever in an ensemble doesn't kill the query — it's logged via callbacks and skipped. A failing self-query parse falls back to a non-filtered vector search. This makes retrievers robust enough to put behind a user-facing chat without circuit breakers.

## Performance characteristics

- **MultiQuery cost:** 1 LLM call (rewrite) + N vectorstore queries (typically 3 variants) — query latency ≈ slowest variant.
- **Ensemble cost:** parallel; latency ≈ slowest child.
- **Compression cost:** can be substantial — `LLMChainExtractor` is one LLM call per doc, so 10 docs = 10 calls. Use `EmbeddingsFilter` first to cull cheaply.
- **Time-weighted memory:** maintains `last_accessed_at` per doc; needs the underlying store to support metadata updates.

## Evolution clues

- `BaseRetriever`'s API has evolved from `get_relevant_documents(query) -> list[Document]` to the Runnable interface (`invoke(query) -> list[Document]`); both surfaces are kept for backward compat.
- `MultiVectorRetriever` and `ParentDocumentRetriever` share the *small-search-large-return* idea; ParentDocument is the constrained-but-easier API.
- Self-query *translators* live next to vectorstore vendor packages — the strategy/translator split is a canonical adapter pattern.
- `document_compressors/` is a sibling sub-package because compressors compose with `ContextualCompressionRetriever`; conceptually they're the same family.
