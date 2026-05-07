# Phase 1B Deep Analysis — `memory/`

## Existence rationale

`memory/` provides the **conversational state primitives** that turn a stateless chain into something that remembers prior turns. The contract is small and uniform: `load_memory_variables(inputs) -> dict` and `save_context(inputs, outputs) -> None`. The interesting variation is *what* state is kept and *how it is compacted*: raw buffer, sliding window, running summary, knowledge-graph triples, salient entity facts, vectorstore-indexed turns, or a token-budgeted hybrid. These are distinct algorithms — each is a deliberate trade between recall, fidelity, prompt cost, and latency.

## Design decisions visible in the code

| Decision | Choice made | Plausible alternatives | Inferred rationale |
|---|---|---|---|
| Memory contract | `BaseMemory.load/save_context` | Direct attribute access; observer | Two-method contract is small enough to subclass in a notebook; orthogonal to `Chain` |
| Sync write, lazy read | `save_context` mutates state synchronously; `load_memory_variables` reads on demand | Always lazy; always eager | Saving must be deterministic (next turn must see this turn); reading happens once per chain call |
| Compaction strategies as classes | Buffer / Window / Summary / SummaryBuffer / TokenBuffer / KG / Entity / VectorStore | Single class with config flags | Each algorithm has its own state shape (string vs list vs graph) — subclassing keeps state types clean |
| Summary memory uses an LLM | `_get_summary` calls an LLM with prior summary + new turns | Heuristic truncation | LLM summaries preserve semantic content much better; cost is the trade |
| Token-buffer eviction | FIFO drop until token count ≤ `max_token_limit` | Random / LRU | FIFO matches conversational recency intuition |
| ChatMessageHistory abstraction | Memory stores delegate to a `BaseChatMessageHistory` | Direct list | Lets memory be backed by Redis, file, Postgres, … without changing the algorithm |
| Entity extraction | Lightweight LLM call extracts entity names + summaries | NER + heuristic | LLM extraction handles cross-domain entities a static NER misses |
| Read-only / combined wrappers | `ReadOnlySharedMemory`, `CombinedMemory` | Inline composition | Allow agents to *expose* memory to a sub-chain without letting that sub-chain *write* to it |

## Algorithm deep-dives

### 1. ConversationSummaryBufferMemory

**Problem.** Pure buffer overflows context; pure summary loses recent detail. Combine: keep the last N turns verbatim, and an LLM summary of everything older.

**Trace.** On `save_context(input, output)`:
1. Append `(HumanMessage(input), AIMessage(output))` to `chat_memory.messages`.
2. Compute `total_tokens = sum(token_count(m) for m in messages)`.
3. While `total_tokens > max_token_limit`:
    - Pop the oldest message (or pair).
    - `moving_summary = llm.invoke(summary_prompt(moving_summary, popped_msg))`.
4. Persist `(moving_summary, remaining messages)`.

`load_memory_variables` returns: `system_summary` + the recent messages (in messages mode) or a flattened string (in string mode).

**Why this works.** Recent turns are kept verbatim — high fidelity for clarification turns. Older turns are folded into a running summary that preserves names/decisions/intents. The summary cost is amortised: only one LLM call when eviction triggers.

**Edge cases.**
- LLM call fails during eviction → state remains over budget; logged via callbacks.
- `max_token_limit` is approximate (token counter is an estimate for non-OpenAI models).

### 2. ConversationKGMemory

**Problem.** A multi-turn chat about Alice's preferences should let the agent answer "what does Alice like?" turns later. Summaries blur this; raw buffers exceed limits. Build a **knowledge graph**.

**Trace.**
1. After each turn, the LLM is asked to extract `(subject, predicate, object)` triples from the latest exchange.
2. Triples are added to `NetworkxEntityGraph` (in-memory by default).
3. On `load_memory_variables`, the LLM is asked which entities the new input mentions.
4. The retrieved entities' triples are formatted as text and added to the prompt.

**Why a KG.** Triples deduplicate naturally (`("Alice", "likes", "tea")` is the same regardless of phrasing) and support directed lookup (give me everything about Alice). Cost is two extra LLM calls per turn — acceptable for high-fidelity assistants.

### 3. VectorStoreRetrieverMemory

**Problem.** Long-running agents (weeks of conversation) blow past summary capacity. Index every turn into a vectorstore and retrieve only the relevant ones.

**Trace.**
1. `save_context(inputs, outputs)`: format `f"input: {…}\noutput: {…}"` → embed → upsert into vectorstore.
2. `load_memory_variables({"input": new_q})`: vectorstore.similarity_search(new_q, k=4) → format messages → return.

**Why.** Effectively unbounded memory at the cost of context-relevance precision. Works well for "support agent looks up past tickets from the same user" scenarios.

## Error philosophy

**Best-effort, never block the next turn.** Memory failures are logged but never raised (an agent can survive without long-term recall, but mid-turn crash loses context). LLM-driven memories (Summary, KG, Entity) catch parser errors and skip the problematic turn — the buffer still grows, just without the LLM-derived overlay.

## Performance characteristics

- **Buffer / Window:** O(1) save, O(N) read (N = window size). No LLM cost. **Cheapest.**
- **Summary / SummaryBuffer:** O(1) save (O(LLM) when eviction triggers), O(1) read. **One LLM call amortised per K turns.**
- **KG:** O(LLM) save (extract triples) + O(LLM) read (entity detection). **Two LLM calls per turn.**
- **VectorStore:** O(embed) save, O(embed + search) read. **Two embedding calls per turn, no LLM.**
- **Entity:** between Summary and KG.

## Evolution clues

- Most memory classes pre-date `BaseChatMessageHistory`; `chat_memory.py` shows the bolt-on:  `BaseChatMemory(BaseMemory)` adds a `chat_memory: BaseChatMessageHistory` attribute.
- `motorhead_memory.py` and `zep_memory.py` are external-service variants that delegate the entire algorithm to a server — kept for backwards compatibility but largely superseded by community packages.
- The newer LCEL pattern is `RunnableWithMessageHistory(runnable, get_session_history=...)` — explicit history rather than implicit memory. The classic `Memory` API persists for users on the legacy `Chain` surface.
