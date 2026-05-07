# RAGFlow — Phase 1A Survey (Broad)

**Source:** `/mnt/disk1/zy/rag/ragflow` · **Git rev:** `e8f19aa33` · **Generated:** 2026-05-06

## What is RAGFlow?

RAGFlow is an open-source Retrieval-Augmented Generation (RAG) engine built around **deep document understanding**. It is a full-stack application that lets users upload heterogeneous documents (PDF, DOCX, slides, images, audio, tabular data), chunk and embed them with knowledge of their visual/structural layout, and then query that knowledge base via chat, agents, or an SDK. Unlike thin wrappers around an embedding model, RAGFlow ships its own deep-learning pipeline for OCR, layout analysis and table parsing (`deepdoc/`), a full agent framework with a graph-canvas DSL (`agent/`), Graph-RAG construction (`rag/graphrag/`), and a polished web UI (`web/`).

## Target wiki depth

**3-level** — project root has 9+ functional sub-module directories, each with their own meaningful sub-directories with source files. The hub (`L0`) links to per-module overviews (`L1`); large modules expand into per-sub-module deep-dives (`L2`).

## Top-level scope

| Module | Lang | Files | Role |
|---|---|---|---|
| `rag/` | Python | 111 .py | Core RAG pipeline: chunking, embedding, retrieval, GraphRAG, RAPTOR, NLP, LLM abstractions |
| `api/` | Python | 98 .py | Flask REST API server, blueprints, DB models, services |
| `agent/` | Python | 87 .py | Agent canvas DSL, components (LLM/retrieval/loop/categorize), tools, sandbox |
| `deepdoc/` | Python | 37 .py | Deep document parsing: PDF/DOCX/PPT/XLSX/HTML, OCR, layout & table-structure recognizer |
| `internal/` | Go (+C++) | 218 .go / 115 cpp/h | Higher-performance Go services (admin, server, dao, engine, tokenizer C++ binding) |
| `web/` | TypeScript/React | 1100 .ts/tsx | Full SPA frontend (chat, KB, agent canvas, document viewer) |
| `common/` | Python | 91 .py | Shared utilities, settings, constants, parsers, token utils |
| `mcp/` | Python | 3 .py | Model-Context-Protocol server exposing RAGFlow as MCP tools |
| `sdk/` | Python | 19 .py | Python SDK for RAGFlow REST API |
| `memory/` | Python | 12 .py | Long-term memory subsystem for chat sessions |
| `tools/` | Python | 24 .py | DevOps / data-loading utility scripts |
| `admin/` | Python | 14 .py | Admin tooling |

## Architecture (one line)

> **Documents → DeepDoc parse/OCR → RAG chunk/embed/index → ES/Infinity/OpenSearch → Retriever → LLM → Chat / Agent / API.**
> The `web/` SPA orchestrates user interactions; `api/ragflow_server.py` is the Flask entry; `rag/svr/task_executor.py` is the async background worker that executes parsing/indexing jobs queued in Redis. `internal/` is a parallel Go server that re-implements many of the same DAO/handler layers for higher-throughput deployments.

## Discovered cross-module dependencies (Python)

- `api.apps.*` → `rag.nlp.search`, `rag.flow.*`, `agent.canvas`, `deepdoc.*`
- `rag.svr.task_executor` → `rag.app.*` (parsers per ParserType), `rag.graphrag.*`, `rag.raptor`, `rag.nlp.search`, `rag.utils.*`, `agent.canvas`
- `rag.flow.pipeline` → `agent.canvas.Graph` (pipelines are agent canvases)
- `agent.component.*` → `rag.nlp.search`, `rag.llm.*`, `api.db.services.*`
- `mcp/*` → `sdk.python.ragflow_sdk`
- `web/src/services/*` → REST endpoints under `api.apps.restful_apis`
- `internal/dao/*` mirrors `api/db/db_models.py` schema for Go-side access

## Auto-detected language

**Python** is the dominant backend language (~700 files). Secondary: **TypeScript/React** for the SPA (1100 files), **Go** for `internal/` (218 files), **C++** for the rag-tokenizer C-API binding (`internal/cpp/`, 115 files).

## Key entry points

| Process | Entry | Purpose |
|---|---|---|
| API server | `api/ragflow_server.py` | Flask app, blueprints, DB init |
| Task worker | `rag/svr/task_executor.py` | Background parse/embed/index loop |
| Cache file svr | `rag/svr/cache_file_svr.py` | File caching daemon |
| Sync data source | `rag/svr/sync_data_source.py` | External connector polling |
| MCP server | `mcp/server/server.py` | Expose tools over MCP |
| Web dev | `web/vite.config.ts` | Vite/React SPA |
| Go server | `internal/cmd/.../main.go` | Alternate Go service binary |
| Agent sandbox | `agent/sandbox/` | Code-exec sandbox for `Code` component |

## Per-module high-level summaries

### `rag/`
Heart of the engine. `rag/app/*.py` provides per-document-type chunkers (`naive`, `paper`, `book`, `manual`, `presentation`, `qa`, `table`, `resume`, `picture`, `audio`, `email`, `tag`). `rag/flow/` is the newer DAG-based pipeline (parse → chunk → tokenize → extract). `rag/nlp/` holds the proprietary `rag_tokenizer` (Chinese-aware, dictionary + DART trie), search query rewriting, term-weighting and synonym expansion. `rag/llm/` defines `Base` classes for chat/embedding/rerank/cv/tts/sequence2txt with adapters for OpenAI, Bedrock, Ollama, Tongyi, Xinference, etc. `rag/graphrag/` implements both Microsoft "GraphRAG-General" and the lighter "LightRAG" variants — entity extraction, community detection (Leiden), mind-map construction, hybrid search. `rag/raptor.py` is the recursive-clustering hierarchical summarisation index. `rag/utils/*_conn.py` are pluggable doc-store / object-store / vector-store backends (ES, Infinity, OpenSearch, OB, MinIO, S3, Azure, GCS, OSS, OpenDAL).

### `api/`
Flask app exposing `restful_apis/` (v1 REST), `sdk/` (programmatic SDK endpoints), plus cross-app blueprints (`document_app.py`, `llm_app.py`). `api/db/db_models.py` defines all Peewee ORM tables. `api/db/services/*.py` is the business-logic layer (`document_service.py`, `dialog_service.py`, `task_service.py`, `knowledgebase_service.py`, `canvas_service.py`). `api/apps/services/` holds higher-level orchestration. `api/db/joint_services/` cross-cuts services (e.g. `memory_message_service.py`).

### `deepdoc/`
Parsers for `pdf`, `docx`, `excel`, `ppt`, `html`, `markdown`, `epub`, `json`, `txt`, `figure`, `resume`, plus alternative engines `mineru`, `docling`, `paddleocr`, `tcadp`, `opendataloader`. `deepdoc/vision/` holds the layout / table-structure / OCR neural recognizers built on PaddlePaddle/ONNX.

### `agent/`
Workflow-DSL canvas (`canvas.py` → `Graph`). `agent/component/` provides 20+ node types: `begin`, `llm`, `agent_with_tools`, `categorize`, `switch`, `iteration`/`iterationitem`, `loop`/`loopitem`, `message`, `invoke`, `data_operations`, `excel_processor`, `string_transform`, `variable_aggregator`, `variable_assigner`, etc. `agent/tools/` houses external integrations (web search, code-exec sandbox, SQL, calls to retrieval). `agent/templates/` ships ready-to-import canvas DSL JSONs. `agent/plugin/` is the third-party plugin loader.

### `internal/` (Go)
Parallel Go service exposing many of the same endpoints but at higher throughput. Layered: `handler/` (HTTP handlers) → `service/` (business logic) → `dao/` (DB access via GORM) → `entity/` (struct models). Has its own `tokenizer/` Go wrapper that calls into `internal/cpp/rag_analyzer_c_api.cpp` (Darts-double-array trie + PCRE2). `internal/engine/` orchestrates jobs, `internal/cache/` Redis layer, `internal/storage/` object-store abstraction.

### `web/` (TypeScript)
React 18 + Vite + Tailwind + shadcn/ui SPA. Pages under `src/pages/` cover knowledge-base management, chat, agent canvas (graph editor), document viewer, file manager, settings. `src/services/` calls REST endpoints. `src/hooks/` for React-Query data layer. `src/components/` for shadcn-based UI.

### `common/`
Cross-cutting helpers: `settings.py`, `constants.py` (enums for LLMType/ParserType/TaskType), `crypto_utils`, `token_utils`, `tag_feature_utils`, `connection_utils`, `mcp_tool_call_conn.py`, `data_source/` adapters, `doc_store/` interfaces.

### `mcp/`, `sdk/`, `memory/`, `tools/`, `admin/`
Smaller modules. MCP server exposes RAGFlow KB-search and chat as MCP tools to LLM clients. SDK is a thin Python wrapper around the REST API. Memory implements per-tenant long-term memory. Tools are CLI utilities. Admin is server administration helpers.

## Architectural patterns observed

| Pattern | Where | Why |
|---|---|---|
| Plugin/registry | `rag/llm/`, `rag/utils/storage_factory.py`, `rag/app/` | Multi-vendor support for LLMs/stores/parsers |
| Abstract base + concrete | `rag/llm/{Chat,Embedding,Rerank}Base` | Uniform interface across providers |
| Producer/consumer with Redis | `rag/svr/task_executor.py` ↔ Redis stream | Decouple HTTP from heavy parse jobs |
| Strategy by ParserType | `rag/svr/task_executor.do_handle_task()` | Choose parser by document kind |
| Graph DSL / Canvas | `agent/canvas.py` (DAG of components) | User-editable workflows |
| Layered DAO / Service | `api/db/services`, `internal/handler→service→dao` | Separation of concerns |
| Pluggable doc-store | `rag/utils/{es,infinity,opensearch,ob}_conn.py` | Choose vector backend |
| Pluggable object-store | `rag/utils/{minio,s3,azure,gcs,oss,opendal,encrypted}_conn.py` | Storage portability |
| OCR/layout pipeline | `deepdoc/vision/recognizer.py` → ONNX | Self-contained doc understanding |
| Recursive summarisation | `rag/raptor.py` | Multi-level abstraction in retrieval |
| Knowledge graph + community detection | `rag/graphrag/general/leiden.py` | GraphRAG-style global queries |

## Domain terminology (cross-module)

KB (knowledge base), tenant, dialog, canvas / pipeline, parser type, chunk, doc-id, task, RAPTOR, GraphRAG / LightRAG, mind map, entity-resolution, community report, embedding, rerank, retriever, hybrid search, BM25, dense vector, OCR, layout recognizer, TSR (table structure recognizer), bbox, page-num token, doc-store, object-store, MCP, LLM bundle, tenant LLM, model provider, plugin, sandbox, agent canvas, component DSL, iteration/loop, switch, variable aggregator, generator, prompt template.

## Wiki target structure (decided)

```
docs/
  index.html                       ← L0 project hub
  search.html
  search-index.json
  rag_doc/                         ← L1: rag/
    index.html
    app/index.html                 ← per-type chunkers
    flow/index.html                ← DAG pipeline
    nlp/index.html                 ← rag_tokenizer + search/query
    llm/index.html                 ← model abstractions
    graphrag/index.html            ← GraphRAG-General + Light + RAPTOR
    utils/index.html               ← doc-/object-store backends
    svr/index.html                 ← task executor
  api_doc/                         ← L1: api/
    index.html
    apps/index.html
    db/index.html
    services/index.html
  agent_doc/
    index.html
    canvas/index.html
    component/index.html
    tools/index.html
  deepdoc_doc/
    index.html
    parser/index.html
    vision/index.html
  internal_doc/                    ← Go
    index.html
    handler/index.html
    service/index.html
    dao/index.html
    cpp/index.html                 ← C++ rag analyzer
  web_doc/
    index.html
    pages/index.html
    services/index.html
  common/index.html                ← L1-flat
  mcp/index.html                   ← L1-flat
  sdk/index.html                   ← L1-flat
```
