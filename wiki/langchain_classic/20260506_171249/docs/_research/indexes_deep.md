# Phase 1B Deep Analysis — `indexes/`

## Existence rationale

`indexes/` is the home of **incremental ingestion into a vectorstore**. The naïve approach — wipe and re-embed everything on every refresh — is slow and expensive. The `index()` algorithm uses a **record manager** (a SQL table of `(key, hash, source_id, updated_at)`) to compute the diff between *what we have* and *what should be there*, and emits only the deltas as adds and deletes. This is the difference between a 5-second nightly refresh and a 5-hour one.

## Design decisions

| Decision | Choice | Alternative | Rationale |
|---|---|---|---|
| Record manager backed by SQL | `SQLRecordManager` (SQLAlchemy) | In-memory; vectorstore-side metadata | Persistent across processes; doesn't depend on vectorstore having metadata filtering |
| Hash-based change detection | `hash(page_content + metadata)` keyed by `(source_id, key)` | Timestamp-only | Detects content edits even when source mtime is stale |
| Source-aware cleanup | `cleanup="full"` deletes everything *not* present in this run; `"incremental"` deletes only stale rows from the same `source_id`; `None` never deletes | One mode | "full" is for one-shot rebuilds; "incremental" is for periodic per-source refreshes |
| Batch upsert | Documents processed in `batch_size` chunks | One-by-one | Vectorstore embeddings amortise across batches |
| Deterministic IDs | `key` is hash-derived → upsert is idempotent | Random UUIDs | Re-running the same indexing job is a no-op rather than a duplicate flood |

## Algorithm deep-dive — `index()`

**Pseudocode.**
```python
existing = record_manager.list_keys(source_ids=[source])  # set of (key, hash)
new_keys = set()
for batch in batches(docs, batch_size):
    for doc in batch:
        key = hash(doc.page_content)
        if (source, key) not in existing or existing[key].hash != current_hash(doc):
            vectorstore.add_documents([doc], ids=[key])  # upsert
            record_manager.update([(key, source, current_hash(doc), now)])
        new_keys.add(key)

if cleanup == "full":
    stale = record_manager.list_keys() - new_keys
elif cleanup == "incremental":
    stale = record_manager.list_keys(source_ids=[source]) - new_keys
else:
    stale = set()
vectorstore.delete(stale)
record_manager.delete_keys(stale)
return {"num_added": ..., "num_updated": ..., "num_deleted": ..., "num_skipped": ...}
```

**Edge cases.**
- Two docs with identical content: same `key` → second is a no-op upsert; not a duplicate.
- Source that produces *fewer* docs than last run: `incremental` cleanup deletes the missing ones; `None` leaves them (orphans).
- Vectorstore that doesn't support deterministic IDs: `index()` raises with a clear error.

## Performance characteristics

- **Best case** (no changes): O(N_existing) record-manager read + zero vectorstore work.
- **Worst case** (full rewrite): O(N_docs) embed + upsert + delete.
- **Bottleneck:** embedding throughput (the vectorstore is usually fast; the embedding API is the queue).

## Evolution clues

`SQLRecordManager` started as the only backend; an interface (`RecordManager` ABC) and an `aindex` async variant followed. The cleanup modes accreted over time as users hit different ingestion patterns (one-shot rebuild vs source-by-source refresh).
