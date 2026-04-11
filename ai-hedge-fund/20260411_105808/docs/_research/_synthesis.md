# Phase 1C — Cross-Module Synthesis

## End-to-End Flows

### Flow 1: Single Stock Analysis (CLI)
1. **Entry**: `main.py` → `parse_cli_inputs()` → user selects tickers, analysts, model
2. **Workflow Build**: `create_workflow()` → LangGraph StateGraph with selected analyst nodes
3. **Fan-Out**: `start_node` → all selected analysts execute in parallel
4. **Agent Execution**: Each agent calls `tools/api.py` → `data/cache.py` → external API
5. **Agent Signal**: Each agent returns `{signal, confidence, reasoning}` into `state["data"]["analyst_signals"]`
6. **Risk Management**: `risk_management_agent` reads all signals, calculates volatility-adjusted position limits
7. **Portfolio Decision**: `portfolio_management_agent` reads signals + limits, calls LLM for final decision
8. **Output**: `print_trading_output()` renders colored tables with decisions and reasoning

### Flow 2: Backtesting
1. **Entry**: `backtester.py` → `parse_cli_inputs()` → creates BacktestEngine
2. **Prefetch**: Engine prefetches 1 year of prices, metrics, insider trades, news for all tickers + SPY
3. **Daily Loop**: For each business day in date range:
   a. Get current prices for all tickers
   b. Run full agent ensemble via AgentController (same as Flow 1)
   c. Execute trades via TradeExecutor (buy/sell/short/cover)
   d. Calculate portfolio value and exposures
   e. Update performance metrics (Sharpe, Sortino, max drawdown)
   f. Print updated results table
4. **Output**: Final performance metrics, portfolio value history

### Flow 3: Web Application Run
1. **Entry**: POST `/api/hedge-fund/run` with HedgeFundRequest
2. **Setup**: AgentService resolves graph nodes → agent functions, loads API keys from DB
3. **SSE Stream**: Yields StartEvent, then spawns agent execution
4. **Agent Loop**: Same as Flow 1 but with per-agent model selection from graph config
5. **Progress**: ProgressUpdateEvents streamed as agents complete
6. **Storage**: Results saved to HedgeFundFlowRun + HedgeFundFlowRunCycle
7. **Completion**: CompleteEvent with full results

## Coupling Analysis

### Tight Coupling
- **agents/* ↔ tools/api.py**: Every agent imports API functions directly; changing the API interface breaks all agents
- **agents/* ↔ graph/state.py**: All agents depend on AgentState TypedDict and show_agent_reasoning
- **main.py ↔ utils/analysts.py**: Analyst registry is the single source of truth for agent discovery

### Loose Coupling
- **agents ↔ backtesting**: Backtesting only knows `run_hedge_fund()` — doesn't import individual agents
- **app/backend ↔ src/**: Web app imports `run_hedge_fund` and `BacktestEngine` — clean interface boundary
- **llm/models.py ↔ agents**: Agents don't import LLM models directly — `call_llm()` abstracts this

### Intentional Shared Types
- `AgentState` TypedDict — shared bus for all inter-agent communication
- `AnalystSignal` Pydantic model — standardized signal format
- `Price`, `FinancialMetrics`, etc. — shared data schemas

## Architectural Philosophy

1. **Composition over Inheritance**: No agent base class. Agents are functions, not class hierarchies. This is deliberate — agents share a pattern but not behavior.

2. **Correctness first**: Agents prioritize analysis quality over speed. Linear backoff (60s+) on rate limits shows willingness to wait for correct data.

3. **Convention over configuration**: Agent registration in `ANALYST_CONFIG` uses a consistent dict structure. Adding a new agent means: create file, add to config dict, done.

4. **Explicit over implicit**: AgentState fields are explicitly typed. Portfolio positions track long AND short separately. No hidden state.

5. **Separation of concerns**: Analysis (agents) → Risk (risk_manager) → Decision (portfolio_manager). Each stage has clear inputs and outputs.

## Shared State Inventory

| State | Owner | Consumers | Consistency |
|-------|-------|-----------|-------------|
| AgentState.data.analyst_signals | Each agent writes its own key | Risk manager, portfolio manager | Merge-dict reducer ensures no conflicts |
| AgentState.data.portfolio | main.py initializes | Risk manager reads, portfolio manager reads | Immutable during agent fan-out |
| AgentState.messages | All agents append | Portfolio manager reads last message | operator.add ensures ordering |
| Cache (in-memory) | tools/api.py | All agents (read-through) | Single-threaded; no race conditions |
| Database (SQLite) | app/backend | Web routes only | Session-scoped transactions |

## System Evolution

### Core (most stable)
- `graph/state.py` — AgentState definition (rarely changes)
- `tools/api.py` — API client (changes only when provider changes)
- `data/models.py` — Pydantic schemas (additive changes only)

### Middle Layer
- `agents/portfolio_manager.py` — evolved from simple to deterministic constraints + LLM
- `agents/risk_manager.py` — added correlation analysis and volatility adjustment
- `backtesting/` — refactored from monolithic `backtester.py` to component architecture

### Recent Additions
- `app/backend/` — web interface added after CLI was mature
- Ollama support — local LLM capability added for privacy/cost
- News sentiment agent — split from general sentiment agent
- Growth agent — added to fill analysis gap
