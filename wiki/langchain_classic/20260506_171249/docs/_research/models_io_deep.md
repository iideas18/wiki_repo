# Phase 1B Deep Analysis — Models I/O (`llms/`, `chat_models/`, `embeddings/`, `prompts/`)

## Existence rationale

These four modules are the **provider façade** between user code and the actual LLM/embedding service. After the package split, the *real* implementations migrated to `langchain_community.{llms,chat_models,embeddings}` and provider packages (`langchain_openai`, `langchain_anthropic`, …). What remains in `langchain_classic` is:

1. A **lazy `__getattr__` trampoline** that forwards `langchain_classic.llms.OpenAI` to `langchain_community.llms.OpenAI`.
2. A **deprecation warning** emitted on first access.
3. A handful of **classic, non-trivial wrappers** that pre-date the split: `CacheBackedEmbeddings`, `init_chat_model` (provider-detection), `prompts/example_selector/` re-exports.

The point of this design is migration: legacy code keeps working (with warnings) while users are nudged toward the canonical import path.

## Design decisions

| Decision | Choice | Alternative | Rationale |
|---|---|---|---|
| Lazy `__getattr__` per module | First-access import + warn | Eager imports | Avoids loading 70+ provider deps on `import langchain` |
| Deprecation messages with replacement path | "...moved to `langchain_openai`" | Generic warning | Actionable for the user |
| `CacheBackedEmbeddings` lives in `langchain_classic` | Unique algorithm | Move to community | It's provider-agnostic and used by every retriever pipeline; staying in classic gives it a stable home |
| `prompts/` re-exports `langchain_core.prompts.*` | Pure shim | Implement here | Templates are core abstractions; classic should not duplicate |
| `init_chat_model` provider routing | String like `"openai:gpt-4o-mini"` parsed | One factory per provider | Lets configuration files specify model without import-time provider choice |

## Algorithm deep-dive — `CacheBackedEmbeddings`

**Problem.** Embedding the same documents twice (during a re-index, during dev iteration, during testing) wastes API calls. Cache the result.

**Trace.** `embed_documents(texts)`:
1. `keys = [hash_func(t) for t in texts]` (default SHA256).
2. `cached = byte_store.mget(keys)` — bytes-typed values for hits, None for misses.
3. Decode hits via `decoder` to get back float vectors.
4. `missing_idx = [i for i, c in enumerate(cached) if c is None]`.
5. `new_vectors = underlying_embedder.embed_documents([texts[i] for i in missing_idx])`.
6. `byte_store.mset([(keys[i], encoder(new_vectors[j])) for j, i in enumerate(missing_idx)])`.
7. Splice cached + new in original order; return.

`embed_query` does **not** cache by default — queries are usually unique strings (typos, paraphrases) so cache hit rate is low and the cost of cache pollution outweighs the win.

**Why a `ByteStore` rather than a typed `Mapping[str, list[float]]`.** Lets the same cache back arbitrary content (embeddings now, raw bytes later) and slots into any of `LocalFileStore`, `RedisStore`, `InMemoryByteStore`. The encoder/decoder are pluggable.

## Error philosophy

Deprecated trampolines emit a warning (suppressed in interactive REPLs to avoid spam) and proceed. Real errors come from the underlying community/provider package and propagate unchanged.

## Cross-module dependencies

```
langchain_classic.{llms, chat_models, embeddings}  ──`__getattr__`──►  langchain_community.{llms, chat_models, embeddings}
                                                                                              │
                                                                                              ▼
                                                                                  provider packages (httpx, openai, …)

langchain_classic.prompts  ──re-exports──►  langchain_core.prompts (PromptTemplate, ChatPromptTemplate, MessagesPlaceholder, FewShotPromptTemplate, …)

CacheBackedEmbeddings ──►  storage.ByteStore  ──►  Local / In-memory / Redis backends
```

## Evolution clues

- `chat_models.base.init_chat_model` is a relative newcomer — string-based provider routing reflects the "config as code" pattern.
- The `embeddings/cache.py` (CacheBackedEmbeddings) migrated *to* `langchain_classic` from `langchain_community` because it depends only on core + storage and is widely reused.
- A few internal helper symbols in `prompts/example_selector/` still live here (LLM-driven semantic similarity selectors) rather than in core, because they carry an LLM dependency.
