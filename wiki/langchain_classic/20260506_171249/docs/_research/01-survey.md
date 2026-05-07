# Phase 1A — Broad Survey: `langchain_classic`

**Source path:** `/mnt/disk1/zy/LLM/agent/langchain/libs/langchain/langchain_classic`
**Source SHA:** `1519ed5afb`
**Generated:** 2026-05-06
**Language:** Python (1,321 source files)

---

## What this package is

`langchain_classic` is the **legacy, batteries-included surface** of LangChain. After the 0.1 → 0.2/0.3 refactor split LangChain into `langchain_core` (abstractions: Runnable, BaseMessage, tools, prompts), `langchain_community` (3rd-party integrations), and provider-specific packages (`langchain_openai`, `langchain_anthropic`, …), `langchain_classic` was preserved as the home of:

1. **High-level orchestration primitives** — `Chain`, `AgentExecutor`, `MultiQueryRetriever`, `ParentDocumentRetriever`, conversational memory.
2. **Compatibility shims** — re-exports of types that used to live in `langchain.*` so legacy code keeps importing.
3. **Lazy integration trampolines** — `__getattr__` hooks that forward `langchain_classic.llms.OpenAI` to `langchain_community.llms.OpenAI`, with deprecation warnings.

It is *the surface code* — the parts intentionally kept stable so user code from 2023 still runs in 2026.

## Depth detection

```
langchain_classic/                 ← 28 functional sub-modules, 1321 .py files
├── chains/         (28 sub-dirs, 140 files)   ← L1+L2 candidate
├── agents/         (17 sub-dirs, 146 files)   ← L1+L2 candidate
├── tools/          (64 sub-dirs, 186 files)   ← L1, sub-dirs are integrations
├── document_loaders/ (2 sub-dirs, 166 files)  ← L1 flat (mostly re-exports)
├── llms/           (1 sub-dir,  83 files)
├── retrievers/     (2 sub-dirs, 78 files)
├── vectorstores/   (2 sub-dirs, 75 files)
├── utilities/      (0 sub-dirs, 58 files)
├── embeddings/     (0 sub-dirs, 51 files)
├── callbacks/      (2 sub-dirs, 45 files)
├── memory/         (1 sub-dir,  39 files)
├── chat_models/    (0 sub-dirs, 35 files)
├── evaluation/     (10 sub-dirs, 32 files)
├── output_parsers/ (0 sub-dirs, 23 files)
├── utils/          (0 sub-dirs, 15 files)
├── graphs/         (0 sub-dirs, 13 files)
├── prompts/        (1 sub-dir,  12 files)
├── document_transformers/ (1 sub-dir, 11 files)
├── chat_loaders/   (0 sub-dirs, 10 files)
├── indexes/        (1 sub-dir,   9 files)
├── storage/        (0 sub-dirs,  8 files)
├── smith/          (1 sub-dir,   7 files)
├── docstore/       (0 sub-dirs,  6 files)
├── _api/           (0 sub-dirs,  5 files)
├── load/           (0 sub-dirs,  4 files)
├── runnables/      (0 sub-dirs,  3 files)
├── adapters/       (0 sub-dirs,  2 files)
└── (single-file modules) cache.py · globals.py · hub.py · sql_database.py ·
                          requests.py · python.py · serpapi.py · text_splitter.py
                          · base_language.py · base_memory.py · model_laboratory.py
```

**Decision:** **3-level wiki** (L0 hub + L1 module overviews). L2 deep-dives are produced selectively for the most algorithmically interesting modules: `chains`, `agents`, `retrievers`, `memory`. The remaining modules are documented as **L1-flat** pages (single comprehensive page each), since their sub-dirs are either single-file integrations (`tools/gmail/`, `tools/jira/`) or single-purpose helpers.

## Module classification table

| Module | Role | Doc style | Why this style |
|---|---|---|---|
| `chains` | Composition primitive (the original LangChain idea) | L1 + 5 deep-dive focus pages | Heavily structured, multi-pattern (LCEL bridge, retrieval, router, summarize) |
| `agents` | Tool-using LLM loop | L1 + 5 deep-dive focus pages | Algorithmic (act-observe loop), multiple agent flavours |
| `tools` | BaseTool + 60+ integrations | L1 flat | Integrations are roll-ups; one `BaseTool` algorithm |
| `retrievers` | Strategies that wrap vectorstores | L1 + focus pages on MultiQuery / ParentDocument / Ensemble / Self-Query | Each retriever is its own algorithm |
| `memory` | Conversation state | L1 + focus pages on Summary / KG / Token-Buffer | Each is a distinct compaction algorithm |
| `vectorstores` | Re-export shim around community vectorstores | L1 flat | Almost no logic owned here |
| `document_loaders` | Re-export shim, 166 file/web/cloud loaders | L1 flat | Pure delegation |
| `document_transformers` | Splitters + redundancy filters | L1 | Small, but `text_splitter.py` is a real algorithm |
| `llms` / `chat_models` / `embeddings` | Lazy trampolines | L1 flat each | Provider-agnostic façades |
| `output_parsers` | Parse → structured value | L1 (focus on retry, fix, pydantic) | Self-contained |
| `prompts` | Re-export of `langchain_core.prompts` | L1 flat | Pure shim |
| `callbacks` | Observer pattern, manager fan-out | L1 flat | One mechanism, many subscribers |
| `evaluation` | Scoring + criteria + comparison | L1 (focus on criteria CoT) | 10 sub-dirs, each a metric family |
| `smith` | LangSmith runner | L1 | Bridge to external service |
| `utilities` | API wrappers (search, sql, requests) | L1 flat | Each is small |
| `runnables` | OpenAI Assistants + utility | L1 flat | Tiny |
| `indexes` | Record manager + `index()` algorithm | L1 (focus on record manager hash) | One non-trivial algorithm |
| `storage` | KV abstractions | L1 flat | Small |
| `docstore` | In-memory doc lookup | L1 flat | Tiny legacy module |
| `graphs` | Graph DB query wrappers | L1 flat | One thin pattern |
| `chat_loaders` | Chat history → BaseMessage | L1 flat | Each loader is small |
| `load` | Serialization (`Serializable`) | L1 flat | One pattern |
| `_api` | Deprecation machinery | L1 flat | Cross-cutting infrastructure |
| `adapters` / `schema` / `utils` / `runnables` | Misc shims | Combined into "Foundations" L1 | Tiny each |

## Cross-module dependency map (high-level)

```
                         langchain_core
                       (Runnable, BaseMessage, BaseTool, BaseRetriever,
                        BasePromptTemplate, Document, BaseLanguageModel)
                              ▲           ▲          ▲           ▲
                              │           │          │           │
   ┌──────────────────────────┘           │          │           └────────────┐
   │                          ┌───────────┘          │                        │
   │                          │                      │                        │
chains/  ◄─── prompts/   ◄── llms/, chat_models/   tools/   ◄── output_parsers/
   ▲          ▲              embeddings/             ▲
   │          │              callbacks/              │
   │          └──────────────────┐                   │
   │                             │                   │
agents/  ─────────────────►  memory/  ◄── retrievers/  ◄── vectorstores/
   │                                                       ▲
   └─► utilities/  ─────► tools/integrations/              │
                                                  document_loaders/  ──► document_transformers/
                                                                              │
                                                                              ▼
                                                                          indexes/, storage/
   evaluation/  ─────► chains/  + criteria
   smith/       ─────► evaluation/  + LangSmith API

   graphs/      ─────► graph DB drivers (neo4j, networkx, kuzu)
   load/        ◄── used by every Serializable subclass
   _api/        ◄── used by every deprecated symbol
```

## Architectural patterns observed across the codebase

1. **Template Method** — `Chain._call` / `_acall` and `BaseRetriever._get_relevant_documents` define the skeleton; subclasses override one method. Lets the base class own logging/callback orchestration.
2. **Observer (callbacks)** — `CallbackManager` fans `on_*_start/end/error` to N handlers. Decouples instrumentation from logic.
3. **Strategy** — agent output parsers (ReAct, JSON, OpenAI tools, XML) are interchangeable strategies behind `AgentOutputParser`. Same for memory (Buffer, Summary, KG, TokenBuffer).
4. **Composite (LCEL)** — Runnables compose with `|`; the new world. `langchain_classic` uses LCEL internally for `create_retrieval_chain`, `create_history_aware_retriever`.
5. **Lazy trampoline** — module-level `__getattr__` looks up integration classes from `langchain_community` on first access, emitting a deprecation warning. See `llms/__init__.py`, `chat_models/__init__.py`, `tools/__init__.py`.
6. **Decorator (deprecation)** — `@deprecated` from `_api.deprecation` wraps classes/functions with a runtime warning. Centralised migration path.
7. **Adapter** — `runnables/openai_functions.py`, `adapters/openai.py` translate provider-specific shapes to LangChain abstractions.
8. **Iterator (agent loop)** — `AgentExecutorIterator` exposes per-step yields so a UI can stream reasoning steps.

## Domain terminology (cross-module glossary)

| Term | Meaning |
|---|---|
| **Runnable** | Core abstraction with `.invoke / .ainvoke / .batch / .stream`. Replaces Chain. |
| **Chain** | Pre-Runnable composition primitive; subclass `Chain`, override `_call`. |
| **Agent** | Returns either an `AgentAction` (call this tool) or `AgentFinish` (we're done). |
| **AgentExecutor** | The loop that runs agents until `AgentFinish` or limits reached. |
| **Tool** | A callable with a Pydantic input schema, name, description; `BaseTool` ABC. |
| **Toolkit** | A collection of related Tools (e.g., `SQLDatabaseToolkit`). |
| **Retriever** | `Runnable[str, list[Document]]`, abstracts vectorstore + strategy. |
| **VectorStore** | Embedding-indexed document storage with `similarity_search`. |
| **Document** | `{page_content, metadata}` pair. |
| **Memory** | Read/write buffer for conversation context (`load_memory_variables`, `save_context`). |
| **Callback** | Hook invoked at lifecycle events (`on_llm_start`, `on_chain_end`, …). |
| **CallbackManager** | Fan-out object that wraps a list of handlers. |
| **Prompt template** | A string with `{placeholders}`, optionally with partials and example selectors. |
| **OutputParser** | `Runnable[str, T]` that turns LLM text into structured output. |
| **Serializable** | Mixin that records `__module__` / `__class_name__` so a Chain can be JSON-dumped. |
| **LCEL** | "LangChain Expression Language" — the `R1 \| R2 \| R3` composition style. |
| **Record manager** | `indexes/`-owned table that tracks doc hashes & timestamps for incremental upsert. |
| **MMR** | Maximum Marginal Relevance — diversity-aware re-ranking used in vectorstores/retrievers. |
| **RRF** | Reciprocal Rank Fusion — combines rankings in `EnsembleRetriever`. |
| **Trajectory** | The list of `(action, observation)` tuples produced by an agent run. |
| **Intermediate steps** | Synonym for trajectory; appears in `AgentExecutor` outputs. |
| **Scratchpad** | The agent's running notebook — the textual rendering of intermediate steps fed back into the next prompt. |
| **AgentAction / AgentFinish** | Output union returned by `BaseSingleActionAgent.plan()`. |
| **AgentType** | Legacy enum (`ZERO_SHOT_REACT_DESCRIPTION`, `OPENAI_FUNCTIONS`, …). |
| **Deprecation warning** | Surfaced by `@deprecated` and `_warn_on_import`; suppressed in interactive envs. |

## Per-module headline metrics

| Module | Files | Key public symbols | Sub-modules |
|---|---:|---|---|
| chains | 140 | `Chain`, `LLMChain`, `SequentialChain`, `RouterChain`, `RetrievalQA`, `ConversationalRetrievalChain`, `MapReduceDocumentsChain`, `StuffDocumentsChain` | 28 |
| agents | 146 | `AgentExecutor`, `BaseSingleActionAgent`, `Tool`, `initialize_agent`, `create_react_agent`, `create_openai_tools_agent`, `create_structured_chat_agent` | 17 |
| tools | 186 | `BaseTool`, `Tool`, `StructuredTool`, `tool` (decorator), `render_text_description`, `convert_to_openai_function` | 64 |
| retrievers | 78 | `MultiQueryRetriever`, `ParentDocumentRetriever`, `EnsembleRetriever`, `ContextualCompressionRetriever`, `SelfQueryRetriever`, `TimeWeightedVectorStoreRetriever` | 2 |
| vectorstores | 75 | `VectorStore`, `VectorStoreRetriever` (re-exports) | 2 |
| document_loaders | 166 | `BaseLoader` (re-export), 160+ integrations | 2 |
| document_transformers | 11 | `EmbeddingsRedundantFilter`, `LongContextReorder`, `BeautifulSoupTransformer` | 1 |
| llms | 83 | Trampolines for OpenAI, Anthropic, HuggingFace, … | 1 |
| chat_models | 35 | Trampolines | 0 |
| embeddings | 51 | Trampolines + `CacheBackedEmbeddings` | 0 |
| memory | 39 | `ConversationBufferMemory`, `ConversationSummaryMemory`, `ConversationKGMemory`, `EntityMemory`, `VectorStoreRetrieverMemory`, `ConversationTokenBufferMemory` | 1 |
| callbacks | 45 | `CallbackManager`, `BaseCallbackHandler`, `StdOutCallbackHandler`, `StreamingStdOutCallbackHandler`, `FileCallbackHandler`, `LangChainTracer` | 2 |
| prompts | 12 | Re-exports `PromptTemplate`, `ChatPromptTemplate`, `FewShotPromptTemplate`, `MessagesPlaceholder` | 1 |
| output_parsers | 23 | `RetryOutputParser`, `OutputFixingParser`, `PydanticOutputParser`, `StructuredOutputParser`, `RegexParser`, `EnumOutputParser` | 0 |
| evaluation | 32 | `load_evaluator`, `LabeledCriteriaEvalChain`, `QAEvalChain`, `EmbeddingDistanceEvalChain`, `StringDistanceEvalChain`, `TrajectoryEvalChain` | 10 |
| smith | 7 | `run_on_dataset`, `arun_on_dataset` | 1 |
| utilities | 58 | `SerpAPIWrapper`, `GoogleSearchAPIWrapper`, `WikipediaAPIWrapper`, `SQLDatabase`, `RequestsWrapper`, `PythonREPL` | 0 |
| docstore | 6 | `InMemoryDocstore`, `Wikipedia` | 0 |
| storage | 8 | `LocalFileStore`, `InMemoryByteStore`, `EncoderBackedStore`, `create_lc_store` | 0 |
| indexes | 9 | `index()`, `aindex()`, `SQLRecordManager` | 1 |
| graphs | 13 | `Neo4jGraph`, `NetworkxEntityGraph`, `KuzuGraph`, `NebulaGraph` | 0 |
| chat_loaders | 10 | `BaseChatLoader`, `merge_chat_runs`, `map_ai_messages` | 0 |
| schema | 43 | Re-exports `langchain_core.runnables`, `messages`, `outputs`, `agent`, `documents` | 2 |
| _api | 5 | `@deprecated`, `surface_langchain_deprecation_warnings` | 0 |
| load | 4 | `Serializable`, `dumps`, `loads` | 0 |
| adapters | 2 | `openai.py` — message/tool-call shape adapter | 0 |
| runnables | 3 | `OpenAIAssistantRunnable`, `create_openai_fn_runnable` | 0 |
| utils | 15 | `get_from_dict_or_env`, `mock_now`, `interactive_env`, `aiter`, `formatting` | 0 |

## Top-level single-file modules

- `cache.py` — `BaseCache` interfaces (re-export), `InMemoryCache`, SQLite cache.
- `globals.py` — `get_verbose / set_verbose`, `get_debug / set_debug`, `get_llm_cache / set_llm_cache`. Process-global toggles.
- `hub.py` — `pull(repo_id)` / `push(repo_id, object)` against the LangChain Hub.
- `model_laboratory.py` — runs the same prompt across multiple models for side-by-side comparison.
- `text_splitter.py` — re-exports `langchain_text_splitters` (`RecursiveCharacterTextSplitter`, …).
- `sql_database.py` — re-export of `langchain_community.utilities.SQLDatabase`.
- `requests.py` / `python.py` / `serpapi.py` — single-class re-exports.
- `formatting.py` — string templating helper used by prompts.
- `base_language.py` / `base_memory.py` — re-exports of core abstractions.
- `env.py` — environment lookup helpers.
- `example_generator.py` / `input.py` — small helpers for prompt examples.

## Source tree (top-level)

```
langchain_classic/
├── _api/                  ← deprecation infrastructure
├── adapters/              ← provider adapters (currently openai.py)
├── agents/                ← Agent loop, AgentExecutor, agent flavours
├── cache.py               ← LLM response cache
├── callbacks/             ← Observer pattern fan-out
├── chains/                ← Chain abstraction + 28 chain families
├── chat_loaders/          ← chat history → BaseMessage
├── chat_models/           ← lazy trampolines to community
├── docstore/              ← legacy in-memory document store
├── document_loaders/      ← 160+ file/web/cloud loaders
├── document_transformers/ ← splitters & filters
├── embeddings/            ← lazy trampolines + CacheBackedEmbeddings
├── env.py
├── evaluation/            ← QA, criteria, distance, comparison evals
├── example_generator.py
├── formatting.py
├── globals.py             ← process-wide toggles
├── graphs/                ← graph DB query wrappers
├── hub.py                 ← LangChain Hub pull/push
├── indexes/               ← record manager + index() upsert algorithm
├── input.py
├── llms/                  ← lazy trampolines to community
├── load/                  ← Serializable mixin
├── memory/                ← conversation state strategies
├── model_laboratory.py
├── output_parsers/        ← retry, fix, pydantic, structured parsers
├── prompts/               ← re-exports of langchain_core.prompts
├── python.py
├── requests.py
├── retrievers/            ← MultiQuery, ParentDoc, Ensemble, SelfQuery
├── runnables/             ← OpenAIAssistantRunnable + helpers
├── schema/                ← legacy type re-exports
├── serpapi.py
├── smith/                 ← LangSmith runner
├── sql_database.py
├── storage/               ← KV abstractions
├── text_splitter.py
├── tools/                 ← BaseTool + 60+ integration sub-dirs
├── utilities/             ← API wrappers
└── utils/                 ← misc helpers
```
