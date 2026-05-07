# MEMORY Module Deep-Dive

## Existence Rationale

Raw chat logs grow unbounded and slow down token counting. Without memory/, every chat request would include the entire history (tokens wasted), or users manually prune (tedious + lossy). The memory module extracts key facts via summarization and stores embeddings, so recent interactions stay fast while long histories compress.

### Real-World Analogy
Human memory: short-term recall (recent messages), long-term storage (facts + embeddings). memory/ mimics this by keeping recent chat in fast cache and old interactions in summarized vector form.

## Core Design Decisions

| Decision | Choice | Alternative | Why |
|----------|--------|-------------|-----|
| Adapter pattern for backends | Pluggable memory store (Postgres / Redis) | Single hardcoded DB | Lets users choose based on scale and cost. |
| Vector embeddings + summarization | Compress history into facts + embeddings | Keep all raw messages | Reduces token count by 80-90% on long chats. Alternatives: naive truncation loses context. |
| Hybrid cache + DB | Recent in-memory, old in persistent | All-in-memory (RAM pressure), all-in-DB (slow) | Balances speed and scale. |


## Algorithm Spotlight

### Summarization (extractive)
**Problem:** Select top-k sentences via TF-IDF or BM25
**Approach:** Regenerate summary on every query (expensive)
**Why:** O(n log k) via heap; summary is deterministic, cacheable.

## Failure Modes & Recovery

| Failure | Trigger | Detection | Recovery |
|---------|---------|-----------|----------|
| Vector DB down | Embedding write fails | Fallback to raw message summary | User sees less context but chat continues. |
| Cache eviction under load | Recent buffer overflows | LRU eviction: oldest recent msg moves to DB | Transparent; user doesn't notice. |


## Performance Notes

- ('In-memory recent buffer', '~1ms lookup vs ~10ms DB query')
- ('Vector similarity search', 'HNSW index: logarithmic search instead of linear scan')


## Key Files & Modules

- services/ — Memory service interface
- utils/ — Embedding, summarization helpers
