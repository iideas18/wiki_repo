# RAGFlow — Phase 1C Cross-Module Synthesis

This document captures **how the modules compose into a system**. Read it after the per-module deep-dives.

## 1. End-to-End Flows

### Flow A: Ingest a PDF → searchable chunks

1. **`web/`** — User drags a PDF into the upload widget on `KnowledgeBase` page (`web/src/pages/...`).
2. **`api/apps/document_app.py`** — Multipart `POST /v1/document/upload` is handled by a Flask blueprint, which calls `DocumentService.create()` to insert a row in MySQL and stage the file in MinIO/S3 (via `rag/utils/{minio,s3,...}_conn.py`).
3. **`api/db/services/task_service.py`** — `TaskService.create()` enqueues a parse-task in Redis (key per `task_id`).
4. **`rag/svr/task_executor.py`** — A long-running worker process loops over Redis, picks up the task, looks up `parser_id` in `FACTORY = {ParserType.NAIVE: naive, ParserType.PAPER: paper, ...}` (`rag/app/`).
5. **`deepdoc/parser/pdf_parser.py`** — Extracts text streams + bounding boxes; for scanned pages it falls through to `deepdoc/vision/ocr.py` and `deepdoc/vision/layout_recognizer.py` (PaddlePaddle/ONNX).
6. **`rag/app/<type>.chunk()`** — Type-specific chunker assembles chunks, optionally calling `rag/nlp/rag_tokenizer` for term boundaries.
7. **`rag/nlp/search.index_name()` / `rag/utils/{es,infinity}_conn.py`** — Chunk embeddings (computed via `rag/llm/embedding_model.py`) are written into the doc-store. Optional GraphRAG (`rag/graphrag/general/index.py`) extracts entities/relations and adds a graph.
8. **`task_executor`** — Updates progress via Redis pub/sub keys consumed by `web/` for live progress bars.

**Latency profile:** PDF parse 5–60s (OCR-bound for scanned), embedding 10–50ms/chunk, indexing batched. GraphRAG adds another 30s–10min depending on entity count.

### Flow B: Chat query → grounded answer

1. **`web/`** — User submits message in `Chat` page; SSE stream opens.
2. **`api/apps/restful_apis/.../conversation`** — Receives the message, persists to `Conversation` table.
3. **`api/db/services/dialog_service.py`** — Builds a `LLMBundle` (model adapter from `rag/llm/`), calls retrieval.
4. **`rag/nlp/search.py`** — Hybrid retrieval: BM25 over `content_ltks` field + dense vector ANN; results merged with rerank from `rag/llm/rerank_model.py`.
5. **`rag/raptor.py`** (optional) — If RAPTOR index is enabled, traverses the recursive summary tree.
6. **`rag/graphrag/search.py`** (optional) — Local + global community-report retrieval if KB has a knowledge graph.
7. **`api/db/services/dialog_service.py`** — Composes prompt with retrieved snippets, streams tokens from `rag/llm/chat_model.py` back through Flask SSE.
8. **`web/`** — Renders streaming answer with citations linking back to original chunks.

### Flow C: Run an agent canvas

1. **`web/src/pages/.../canvas`** — User clicks "Run" on a saved agent canvas.
2. **`api/apps/.../canvas`** — Handler instantiates `agent.canvas.Graph` from stored DSL JSON.
3. **`agent/canvas.py`** — Topologically schedules components; routes data along edges. Iteration/loop nodes wrap sub-graphs.
4. **`agent/component/llm.py`, `agent/component/agent_with_tools.py`** — Invoke LLMs via `rag/llm/`, optionally with tool calls (`agent/tools/*`).
5. **`agent/sandbox/`** — `Code` components run in a constrained sub-process for security.
6. **Streaming back** — Per-component progress events flow over the same SSE channel.

### Flow D: Pipeline (next-gen DAG ingest)

`rag/flow/pipeline.py` — `Pipeline(Graph)` *extends* `agent.canvas.Graph`, meaning the ingest path is being unified with the agent canvas. A pipeline is a DAG of `parser → chunker → tokenizer → extractor → indexer` nodes editable in the same canvas UI.

> **Inferred design intent:** The team appears to be migrating from per-ParserType monolithic chunkers in `rag/app/` toward composable DAG pipelines. This is a major architectural evolution visible in the code.

### Flow E: GraphRAG construction

1. `rag/svr/task_executor.run_graphrag_for_kb()` — Triggered after document parsing.
2. `rag/graphrag/general/extractor.py` — Per-chunk LLM call extracts (entity, relation, description) tuples.
3. `rag/graphrag/general/entity_resolution.py` — Deduplicates entities across chunks via embedding similarity.
4. `rag/graphrag/general/leiden.py` — Runs Leiden community detection on the entity graph.
5. `rag/graphrag/general/community_reports_extractor.py` — LLM summarises each community.
6. `rag/graphrag/general/mind_map_extractor.py` — Builds a hierarchical mind map.
7. Results land in the doc-store under graph-specific indexes.

## 2. Coupling Analysis

| Boundary | Coupling | Notes |
|---|---|---|
| `web/` ↔ `api/apps/restful_apis` | **Loose** (HTTP/JSON) | The two could be deployed separately; web only depends on REST contract |
| `api/` ↔ `rag/` | **Tight** (Python imports) | Services directly call `rag.nlp.search`, `rag.flow.pipeline`, `rag.graphrag.*`. They live in the same process for many code paths |
| `rag/svr/task_executor` ↔ `api/` | **Tight** but via shared MySQL/Redis | Task executor reads/writes `Task`, `Document` rows; uses Redis for progress |
| `agent/canvas` ↔ `rag/flow/pipeline` | **Inheritance** | `Pipeline(Graph)` — pipelines reuse the canvas execution engine |
| `internal/` (Go) ↔ `api/` (Python) | **Schema-coupled** | Both read the same MySQL tables; Go side mirrors models in `internal/dao/` |
| `rag/llm/` ↔ providers | **Plugin** | Adapter classes per vendor; new providers added without touching callers |
| `rag/utils/{store}_conn` ↔ doc-store backends | **Plugin** | `storage_factory.py` selects at runtime based on settings |
| `deepdoc/` ↔ `rag/app/` | **Loose** | `rag/app/<type>.chunk()` calls into deepdoc parsers but parsers don't know about chunkers |
| `mcp/` ↔ `sdk/` | **Tight** | MCP server uses sdk to talk to RAGFlow REST |

**What breaks if you change interface X?**
- Change `rag.nlp.search.search()` signature → breaks `api/db/services/dialog_service.py`, `agent/component/retrieval.py`, `internal/service/search.go` (last via convention only).
- Change `agent.canvas.Graph` execution model → breaks `rag/flow/pipeline.py`, all agent canvas runs, the pipeline UI.
- Change `ParserType` enum → breaks every `rag/app/*` registration in `FACTORY`.

## 3. Architectural Philosophy

Reading across the codebase, several themes emerge:

**(a) Pluggable everything.** Doc-stores, object-stores, LLM providers, parsers, chunkers, agent components — all use registry/factory patterns. The team clearly designed for *vendor optionality* over a single curated stack. This is a deployment-first philosophy: enterprises with different infrastructures can swap any layer.

**(b) Domain-first naming.** Types are named for their domain role (`ParserType.NAIVE`, `ParserType.PAPER`, `Pipeline`, `Graph`, `Canvas`) rather than CS abstractions. Reading the source feels like reading a documentation glossary — terms map directly to UI concepts.

**(c) Python first, Go where it matters.** Heavy ML/LLM/orchestration stays in Python (where the ML ecosystem lives). The Go `internal/` exists for high-throughput HTTP paths and to leverage cgo into the C++ tokenizer. The duplication is intentional — both stacks share the schema, neither is canonical.

**(d) Worker-queue separation.** The clearest design choice. The Flask API never blocks on parsing; everything heavy goes through `task_executor` over Redis. This lets the API be slim and stateless, and it lets parse jobs scale horizontally by spawning more `task_executor` processes.

**(e) Agents and pipelines unified.** `Pipeline(Graph)` — the same DAG engine drives both user-built agent canvases and system-managed ingest pipelines. This is a significant bet: it commits the team to maintaining one execution model, but it pays off by letting users compose ingest steps the same way they compose chat agents.

**(f) Self-contained doc understanding.** Most RAG products outsource OCR/layout to vendor APIs. RAGFlow ships its own `deepdoc/vision/` neural pipeline (PaddlePaddle/ONNX). This is the project's biggest differentiator — and the steepest dependency cost.

## 4. Shared State Inventory

| State | Owner | Consumers | Consistency |
|---|---|---|---|
| MySQL `Task`, `Document`, `Conversation`, `KB`, `Tenant`, `User` | `api/db/db_models.py` (Peewee) | api/, rag/svr/, internal/ | DB transactions; no cross-process locks beyond Redis distributed-lock for progress updates |
| Redis: progress logs, task queues, distributed locks | `rag/utils/redis_conn.py` | api/, rag/svr/, agent runs | Pub/sub semantics; one writer per `task_id` |
| Doc-store (ES/Infinity/OpenSearch): chunks, embeddings, graph | `rag/utils/{es,infinity}_conn.py` | api/db/services/dialog_service, rag/nlp/search, rag/graphrag/search | Eventual consistency; bulk writes |
| Object-store: raw documents, chunk images | `rag/utils/{minio,s3,...}_conn.py` | deepdoc parsers, web file viewer | Immutable once written |
| File system: model checkpoints, config | `conf/`, `~/.ragflow/` | task_executor, api server | Read-only at runtime |
| Plugin registry: `agent/plugin/GlobalPluginManager` | agent/plugin | agent canvas runs | In-memory per process |

## 5. System Evolution

Reading the code archeologically, here's how the system likely grew:

**Layer 1 (core):** `rag/nlp/`, `rag/llm/`, `deepdoc/` — the original differentiator. The C++ tokenizer (`internal/cpp/`) and the layout/TSR models predate the Go service.

**Layer 2 (orchestration):** `api/` (Flask blueprints) + `rag/svr/task_executor.py` — the original product surface. `rag/app/<type>.py` chunkers were added one at a time as new document types were supported (paper, book, manual, etc.).

**Layer 3 (knowledge graph):** `rag/graphrag/general/` (Microsoft GraphRAG port) added later, then `rag/graphrag/light/` (LightRAG variant) added even later. The two coexist; users pick per-KB.

**Layer 4 (agent canvas):** `agent/canvas.py` + `agent/component/` introduced graph-DSL workflows. Templates ship example agents.

**Layer 5 (pipeline = canvas):** `rag/flow/pipeline.py = Pipeline(Graph)` — the *most recent* layer. The ingest pipeline became a special agent canvas. This is the unification step.

**Layer 6 (Go service):** `internal/` — added for performance-sensitive deployments. Mirrors the Python schema; cgo-binds the C++ tokenizer for max throughput.

**Layer 7 (frontend modernization):** `web/` shows clear migration markers — README mentions UmiJS but `vite.config.ts` is present, suggesting a migration to Vite. shadcn/ui and Tailwind are recent additions.

**Layer 8 (interop):** `mcp/`, `sdk/` — wrappers exposing RAGFlow over MCP and as a Python library, added once the core was stable.

## 6. Cross-cutting Concerns

- **Authentication.** Tenant-scoped throughout. Every service takes `tenant_id`. JWT/cookie auth in `api/apps/auth/`. The Go service replicates this.
- **Internationalisation.** Frontend has `web/src/locales/`. README is translated into 11 languages.
- **Telemetry.** Progress callbacks (`pipeline.callback()`) push into Redis logs. No structured tracing visible — likely added later.
- **Testing.** `test/`, `test/unit_test`, `test/playwright`. ~250 Python test files. Integration tests run against live services.
- **Configuration.** `conf/` + environment vars. `common/settings.py` holds runtime settings. `conf/models/` lists supported LLM providers.
