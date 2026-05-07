# Phase 1B Deep Analysis — `agents/`

## Existence rationale

`agents/` packages the **act-observe-think loop** that turns an LLM into a tool-using agent. Where a `Chain` runs a fixed pipeline, an `Agent` returns either *"call this tool with these args"* or *"we're done, here's the final answer"*, and `AgentExecutor` runs that decision in a loop, accumulating a *trajectory* of (action, observation) pairs. Without `agents/`, library users would have to hand-write the parse → tool-dispatch → re-prompt cycle, which is exactly the boilerplate that distinguishes ReAct, MRKL, OpenAI Functions, OpenAI Tools, Structured Chat, and JSON Chat agents from one another. The module exists to (a) capture that loop once, (b) make agent flavours interchangeable behind a single executor, and (c) provide streaming via `AgentExecutorIterator`.

## Design decisions visible in the code

| Decision | Choice made | Plausible alternatives | Inferred rationale |
|---|---|---|---|
| Agent return type | `Union[AgentAction, AgentFinish]` | bool flag + payload; Result type | Two unrelated payload shapes (action call vs final string) — a tagged union beats a flag-bool |
| Multi-action support | `BaseMultiActionAgent.plan()` returns `list[AgentAction]` | Always one action per step | OpenAI tools/parallel function calls return multiple at once; not all flavours support it |
| Loop control | `AgentExecutor` owns the loop, agent is stateless | Agent owns loop | Lets users swap agent strategy without rewriting executor; supports iteration / streaming |
| Output parsing | Pluggable `AgentOutputParser` per flavour | One parser keyed by AgentType | Each flavour has its own format (ReAct text, JSON, XML, OpenAI tool calls); strategy is the right pattern |
| Scratchpad rendering | Pluggable `format_scratchpad/*` functions | Hardcoded format | Same agent loop with different prompt rendering — ReAct text vs OpenAI tool messages vs XML |
| Tool input | Pydantic schema on `BaseTool.args_schema` | dict-only | Pydantic gives validation, JSON-schema export (for OpenAI fn calling), and natural-language description for prompts |
| Stop conditions | `max_iterations` AND `max_execution_time` | iterations only | Wall-clock cap protects against pathological tool latency / model loops |
| Early stopping methods | `"force"` (return last text) or `"generate"` (LLM final call from trajectory) | Hard fail | Some agents loop forever near the cap; "generate" produces a graceful summary |
| Initialisation API | Two surfaces: `initialize_agent(AgentType, …)` (legacy) and `create_*_agent(...)` factories returning Runnable | Pick one | Factories yield LCEL-friendly Runnables; legacy enum kept for backwards compat |

## Algorithm deep-dives

### 1. The agent loop (`AgentExecutor._call`)

**Problem.** Run an agent until it returns `AgentFinish` *or* hits an iteration / time cap, while invoking the right tool, propagating callbacks, and streaming intermediate state.

**Trace.**
1. Initialise `intermediate_steps: list[tuple[AgentAction, str]] = []`.
2. Loop:
    1. Build prompt inputs `{"input": q, "intermediate_steps": intermediate_steps, "tool_names": tool_names, "tools": tools_doc}`.
    2. The agent (a `Runnable`) runs prompt-formatter → LLM → output-parser → returns `AgentAction|AgentFinish`.
    3. If `AgentFinish`: call `on_agent_finish`, return outputs.
    4. Else for each `AgentAction`:
        - `tool = name_to_tool[action.tool]`; if missing → `InvalidTool` returns an error string instead of raising (so the LLM can self-correct).
        - `observation = tool.run(action.tool_input)` (sync) or `arun` (async). Wrapped in `on_tool_start/end/error`.
        - Append `(action, observation)` to `intermediate_steps`.
    5. Check `iterations >= max_iterations` or `time_elapsed >= max_execution_time` → `return_stopped_response(early_stopping_method)`.
3. Output dict has `output`, optionally `intermediate_steps`.

**Complexity.** Per iteration: 1 LLM call + N tool calls (1 for single-action, ≥1 for multi). Total iterations bounded by `max_iterations` (default 15).

**Why this design.** The executor is **stateless across calls** — all state flows through `intermediate_steps`. This makes the agent serialisable mid-run for retry, makes streaming trivial (the iterator just `yield`s after each step), and lets users implement custom termination by subclassing `AgentExecutor` and overriding `_should_continue`.

**Edge cases.**
- `OutputParserException` during parsing: if `handle_parsing_errors=True` (or a callable), error message becomes an observation and loop continues; else propagates.
- Tool not found: returns the error as observation (prevents fatal exception from a hallucinated tool name).
- `early_stopping_method="generate"`: a final LLM call constructs a graceful answer from the trajectory.
- `return_intermediate_steps=True`: full trajectory in output dict (used by tracing / eval).

### 2. Scratchpad formatting (`format_scratchpad/`)

**Problem.** Different agent prompts expect different serialisations of the running trajectory. ReAct expects plaintext (`Thought: … Action: … Observation: …`), OpenAI tools expects a list of `ToolMessage` objects, XML expects `<tool_input>` tags.

**Solutions.**
- `format_log_to_str` — ReAct text format
- `format_to_openai_function_messages`, `format_to_openai_tool_messages` — convert to chat messages
- `format_xml`, `format_log_to_messages` — XML and structured chat variants
- `format_to_tool_messages` (Claude tools)

The agent's prompt template references `{agent_scratchpad}`; the chosen formatter is the only thing that varies per flavour.

### 3. Output parsing (`agents/output_parsers/`)

**Problem.** Convert raw LLM text → `AgentAction|AgentFinish`.

ReAct (`react_single_input.py`):
1. Look for `Final Answer:` → `AgentFinish(return_values={"output": text_after})`.
2. Else regex `Action: <tool>\nAction Input: <input>` → `AgentAction(tool, input, log=raw_text)`.
3. Both miss → `OutputParserException` (caller decides recovery).

OpenAI tools (`openai_tools.py`): no parsing — the LLM has already produced structured `tool_calls`; convert directly.

JSON Chat (`json.py`): expect `{"action": "...", "action_input": ...}` blob; parse with `json.loads`, fall back to `parse_json_markdown` for fenced blocks.

XML (`xml.py`): regex `<tool>name</tool><tool_input>...</tool_input>` → `AgentAction`.

**Why pluggable.** Each format makes the LLM more or less reliable depending on training data — Claude does best with XML, OpenAI tool-tuned models do best with native tools, smaller open models often ground better in JSON. The parser is interchangeable behind `AgentOutputParser`.

## Error philosophy

**Tolerate parser errors when configured; surface tool errors but feed them back as observations.** The default behaviour is *propagate* (so the user notices), but `handle_parsing_errors=True` flips into a *self-correct* mode where the LLM sees its own mistake on the next iteration. This trades safety for autonomy — explicit opt-in.

`InvalidTool` (a built-in Tool returned when the LLM picks a non-existent name) is the cleanest example: the LLM hallucinated a tool, so we return *"Tool X not found. Available tools: …"* as the observation instead of crashing.

## Performance characteristics

- **Latency dominator:** the LLM call inside the loop. With max_iterations=15 a worst-case agent run is 15× single-LLM latency.
- **Optimisation lever:** parallel tool calls (multi-action agents like OpenAI tools), which cut wall-clock for fan-out queries roughly N×.
- **Streaming:** `AgentExecutorIterator` yields after each step so a UI can show the chain-of-thought as it grows.
- **Memory profile:** `intermediate_steps` keeps every observation in memory; long-running agents with verbose tools (HTML scraping) can spike RAM.

## Evolution clues

- The legacy `AgentType` enum + `initialize_agent` is gradually being replaced by `create_*_agent` factories that return Runnables. `create_react_agent`, `create_openai_tools_agent`, `create_structured_chat_agent`, `create_tool_calling_agent`, `create_json_chat_agent`, `create_xml_agent`, `create_self_ask_with_search_agent` all live next to their legacy class-based equivalents.
- `tool_calling_agent/` is the newest and is provider-agnostic (works with any LLM exposing `bind_tools`) — the others are flavour-specific.
- `openai_assistant/` wraps the OpenAI Assistants v2 API as a Runnable that sits *outside* the standard executor loop (the assistant handles the loop server-side).
- Naming inconsistencies (`openai_functions_agent` vs `openai_functions_multi_agent` vs `openai_tools` vs `tool_calling_agent`) reflect OpenAI's own API evolution: text → functions → parallel tool calls.
