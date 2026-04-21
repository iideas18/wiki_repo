# AI Hedge Fund — Phase 1C Cross-Module Synthesis

## End-to-End Flows

### Flow 1: CLI Trading Decision
1. User runs `python src/main.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-03-01`
2. `src/cli/input.py` parses arguments, prompts for analyst selection
3. `src/main.py:create_workflow()` builds LangGraph StateGraph with selected analysts
4. LangGraph invokes all analyst agents IN PARALLEL (fan-out from start_node)
5. Each agent (e.g., warren_buffett) calls `src/tools/api.py` for financial data
6. Each agent uses `src/llm/models.py` to call LLM with persona prompt
7. Agent returns signal to AgentState.data.analyst_signals
8. All agents converge → risk_management_agent evaluates aggregate risk
9. risk_manager → portfolio_management_agent makes final trade decisions
10. `src/utils/display.py` prints formatted trading output

### Flow 2: Web App Execution (SSE)
1. User builds visual workflow in React Flow frontend
2. Frontend sends flow config + tickers to `POST /hedge-fund/run`
3. `app/backend/services/graph.py` converts React Flow nodes to LangGraph
4. Backend creates execution run record in SQLite
5. Agents execute, streaming progress events via SSE
6. Frontend updates node statuses in real-time (idle → progress → complete)
7. Final portfolio decisions returned as SSE complete event

### Flow 3: Backtesting
1. User configures date range + agents in CLI or web app
2. `src/backtesting/controller.py` orchestrates day-by-day simulation
3. For each trading day: run full agent pipeline → get decisions → execute trades
4. `src/backtesting/portfolio.py` tracks positions, P&L, margin
5. `src/backtesting/metrics.py` calculates Sharpe, drawdown, returns
6. `src/backtesting/output.py` generates performance report

## Coupling Analysis

### Tight Coupling (Intentional)
- **AgentState** is the universal contract: all agents read/write the same TypedDict
- **tools/api.py** is the single data gateway: every agent calls the same financial data functions
- **llm/models.py** centralizes LLM configuration: all agents use `get_model()` + `call_model()`

### Loose Coupling (Good)
- Agents are independent of each other: no agent imports or calls another agent
- Backtesting wraps the same pipeline used in live mode (no separate logic)
- Web app backend uses src/ as a library — clean import boundary

### Interface Width
- AgentState is a WIDE interface (messages + data + metadata dicts) — flexible but weakly typed
- Each agent returns a structured JSON signal but enforces it via LLM prompt, not code schema

## Architectural Philosophy

### 1. Persona-First Design
The core innovation is encoding investor philosophies as LLM system prompts. The code structure mirrors this: one file per investor, each self-contained with its own analysis logic and prompt template.

### 2. Parallel-Then-Aggregate
All analyst agents run independently in parallel (LangGraph fan-out), then converge through risk management and portfolio management. This mirrors how a real hedge fund operates: analysts research independently, then a committee decides.

### 3. Education Over Production
The system prioritizes readability and extensibility over performance. No optimization for latency, no connection pooling, no retry logic. Adding a new agent = copying a file and adding to ANALYST_ORDER.

### 4. Composition Over Inheritance
Agents are functions, not classes. They share state via AgentState dict, not through OOP inheritance. This makes them easy to add/remove from the workflow.

### 5. Progressive Enhancement (CLI → Web → v2)
The system evolved: CLI first (src/main.py), then web app (app/), then quantitative v2 pipeline. Each layer wraps the previous without replacing it.

## Shared State Inventory
| State | Scope | Mechanism |
|-------|-------|-----------|
| AgentState | Per-execution | LangGraph in-memory state dict |
| Portfolio | Per-execution | Python dict passed through AgentState.data |
| analyst_signals | Per-execution | Dict in AgentState.data, keyed by agent name |
| Flow configs | Persistent | SQLite database (app/backend/) |
| API keys | Persistent | SQLite + environment variables |
| Financial data cache | Session | In-memory dict in src/data/cache.py |

## System Evolution
1. **Core** (most stable): src/graph/state.py, src/tools/api.py — the data contract and data source
2. **Agents layer**: src/agents/ — the persona-based analyst agents
3. **Orchestration**: src/main.py, src/graph/ — the LangGraph workflow
4. **Backtesting**: src/backtesting/ — historical simulation wrapper
5. **Web app**: app/ — full-stack interface added later
6. **v2**: Next-gen quantitative pipeline (newest, still WIP)
