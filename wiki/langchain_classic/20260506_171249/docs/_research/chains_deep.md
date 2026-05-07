# Phase 1B Deep Analysis — `chains/`

## Existence rationale

`chains/` predates `langchain_core.runnables` (LCEL). It is the **original LangChain composition primitive**: a class hierarchy where each subclass overrides `_call(inputs) -> outputs` and the base class owns callbacks, validation, memory wiring, and verbose logging. Without `chains/`, every user of `LLMChain`, `RetrievalQA`, `MapReduceDocumentsChain`, or `RouterChain` (released 2022–2023) would be broken. It exists today as a **stable surface** for that pre-LCEL idiom while also wrapping LCEL internally for newer constructors like `create_retrieval_chain`.

## Design decisions visible in the code

| Decision | Choice made | Plausible alternatives | Inferred rationale |
|---|---|---|---|
| Composition mechanism | Subclass `Chain`, override `_call` | LCEL `\|` composition; closures; visitor pattern | Pydantic v1 BaseModel inheritance gave free validation + serialisation; subclass override is the most discoverable extension point for 2022 users |
| Sync/async parity | Both `_call` and `_acall`; default `_acall` raises | Async-only; sync wrapper around async | Many integrations were sync-only in 2022 (requests-based); forcing async would block adoption |
| Inputs/outputs typing | `dict[str, Any]` keyed by `input_keys` / `output_keys` | Dataclass; Pydantic model per chain | Dicts compose with `RunnableMap` and prompt templates without a translation layer |
| Memory integration | `BaseMemory` is a chain attribute; `prep_inputs` merges memory vars | Pass memory explicitly per call | Lets users plug memory into any chain without subclassing |
| Callback flow | `CallbackManager.configure(...)` produces a fresh manager per call | Single global manager | Per-run isolation needed for streaming + tracing trees |
| Document combination | Strategy classes: `Stuff`, `MapReduce`, `Refine`, `MapRerank` | Single switch-case in one class | Each strategy has different prompts/state; subclassing kept them readable |
| Router design | `RouterChain` (string → destination), `MultiRouteChain` dispatches | Single chain with conditional prompt | Allows mixing destinations of different signatures (LLMChain + tool + retrieval) |
| LCEL bridge | `create_retrieval_chain`, `create_history_aware_retriever` are LCEL chains exposed as a `Runnable` | Subclass `Chain` for them | Newer constructors prefer LCEL; legacy `Chain` API kept for old code |

## Algorithm deep-dives

### 1. `Chain.__call__` orchestration

**Problem.** Every chain subclass needs the same boilerplate: validate inputs, merge memory, fire `on_chain_start`, run the body, fire `on_chain_end` (or `on_chain_error`), persist memory, return outputs. Duplicating this in 30+ subclasses is a maintenance nightmare.

**Trace.**
1. `Chain.__call__(inputs)` (or `Chain.invoke` for the Runnable interface).
2. `prep_inputs(inputs)` — accept `str` (single-key chains), validate keys.
3. `prep_inputs` calls `memory.load_memory_variables` and merges into `inputs`.
4. `CallbackManager.configure` builds a manager from kwargs + global handlers.
5. `manager.on_chain_start(serialized=self.dict(), inputs)`.
6. `try: outputs = self._call(inputs, run_manager=child_manager)`.
7. `except: manager.on_chain_error(e); raise`.
8. `prep_outputs(inputs, outputs)` — saves to memory, validates output keys.
9. `manager.on_chain_end(outputs)`.
10. Returns dict.

**Complexity.** O(1) overhead per call modulo the body. The string-coercion and dict-merge fast paths are O(K) in the number of keys (typically 2–4).

**Why this design.** Subclasses only worry about *the actual computation*. Tests show this saved ~120 lines of duplication per chain.

**Edge cases.**
- Single-input chains accept a plain string and auto-key it (`inputs={input_key: "the string"}`).
- If `memory` is set and the chain has 2+ input keys, the chain raises unless one is the memory-managed key.
- `return_only_outputs=True` strips inputs from the returned dict (stops them from being echoed).

### 2. `MapReduceDocumentsChain`

**Problem.** Summarise / answer over a document set too large for a single LLM context. Must (a) parallelise the per-document work and (b) recursively combine until the combined output fits.

**Trace.**
1. Split docs into batches whose total token count ≤ `token_max`.
2. Call `llm_chain` on each batch (the **map** step), producing intermediate texts.
3. If `len(intermediate_texts)` is 1 → finalise.
4. Else: feed all intermediate texts into `combine_document_chain` and **recurse** if the combined fits in context, else split + map again. (The "collapse" step.)
5. Return final text.

**Complexity.** Time `O(N / batch_size)` LLM calls at the map level, then `O(log_batch_size N)` more at the reduce level. Async runs map-step in parallel.

**Why not "stuff"?** Stuff requires `n_docs * doc_tokens ≤ context_window`. MapReduce removes that ceiling at the cost of parallel LLM calls + a slight quality loss on collapse rounds.

### 3. Router chain dispatch

`MultiRouteChain.invoke({"input": q})`:
1. `router_chain.route({"input": q})` returns `Route(destination="sql", next_inputs={...})`.
2. `destination_chains[route.destination].invoke(route.next_inputs)`.
3. If destination unknown → `default_chain` if set, else raise.

This is a **strategy pattern** dispatched at runtime. The router is itself an LLM call (`LLMRouterChain`) with a JSON output parser, or a deterministic rule (`EmbeddingRouterChain`).

## Error philosophy

**Fail-fast at validation, propagate-up at runtime.** Pydantic v1 validators reject misconfigured chains at construction time (missing `output_key`, wrong `prompt` arity). At call time, exceptions bubble up but `manager.on_chain_error` is called first so tracers always see the failure. There is no automatic retry — that's the user's call (or `RetryOutputParser`'s job).

## Performance characteristics

- **Hot path:** prompt formatting + LLM call. Chain overhead is microseconds.
- **Slow path:** `MapReduce` collapses. Each collapse is a full LLM call.
- **Memory:** Linear in `intermediate_steps` for agents; documents are kept in process for `Stuff` / `MapRerank` until the final call.
- **Tradeoff:** dict-of-Any I/O is convenient but loses static typing — LCEL's typed Runnables are the modern answer.

## Evolution clues

- `chains/base.py` predates Pydantic v2 — uses `BaseModel`-from-v1 namespace.
- Recent additions (`history_aware_retriever.py`, `retrieval.py`, `combine_documents/__init__.py:create_stuff_documents_chain`) are LCEL-based and bypass `Chain`. They sit alongside the legacy classes.
- `qa_with_sources/`, `summarize/`, `question_answering/` have both `load_*` factory functions (legacy) and `create_*` factory functions (LCEL).
- Many `LLMChain` users are now told (via `@deprecated`) to migrate to `prompt | llm`.
