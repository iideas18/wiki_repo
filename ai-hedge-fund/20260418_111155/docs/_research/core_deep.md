# Core Infrastructure — Deep Analysis

## Existence Rationale
The core infrastructure (graph/, data/, llm/, tools/, utils/, cli/) provides the foundational plumbing that all agents depend on. Without it, every agent would need to independently manage LLM connections, financial data fetching, state management, and CLI parsing. By centralizing these concerns, the project achieves consistency (all agents use the same data source and LLM interface) and extensibility (adding a new agent requires zero infrastructure changes).

## Design Decisions
| Decision | Choice Made | Alternatives | Rationale |
|----------|------------|-------------|-----------|
| State management | LangGraph TypedDict with merge operators | Class-based state, Redux-style | TypedDict is lightweight, merge operators handle parallel agent writes |
| LLM abstraction | Single get_model() factory | Per-agent LLM config, direct API calls | Centralizes provider switching (OpenAI/Groq/Anthropic) |
| Data caching | In-memory dict keyed by (ticker, date_range) | Redis, SQLite cache, file cache | Simple and sufficient for single-run sessions |
| Financial data | Single API wrapper (Financial Datasets) | Multiple data sources, yfinance | Clean single-source design, easy to mock |
| CLI framework | argparse + questionary | Click, Typer, Fire | Minimal dependencies, interactive selection |

## Algorithm Deep-Dives

### LangGraph Fan-Out/Fan-In
- **Problem**: Run N independent agents in parallel, then aggregate their signals
- **Approach**: StateGraph with edges from start_node to all analyst nodes, all converging to risk_management
- **Why LangGraph**: Built-in parallel execution, state merging via operators, message history
- **Complexity**: O(max_agent_time) for parallel phase, O(1) for aggregation

### merge_dicts State Reducer
- **Problem**: Multiple agents writing to the same data dict simultaneously
- **Approach**: Custom merge function `{**a, **b}` as Annotated operator
- **Edge case**: Last-write-wins for conflicting keys (acceptable since agents write to separate keys)

## Error Philosophy
Fail-safe with graceful degradation. Individual agent failures don't crash the pipeline — the remaining agents' signals are still aggregated. LLM call failures return empty signals rather than raising exceptions.

## Performance Characteristics
- **Fast**: Agent parallel execution via LangGraph
- **Slow**: LLM API calls (network-bound, 1-5s per agent)
- **Bottleneck**: Sequential risk_manager → portfolio_manager phase
