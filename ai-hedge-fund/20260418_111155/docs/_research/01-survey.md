# AI Hedge Fund — Phase 1A Broad Survey

## Project Overview
AI-powered hedge fund proof-of-concept for educational purposes. Multi-agent system where AI agents embodying famous investor personas analyze stocks and produce trading signals, which are aggregated by a risk manager and portfolio manager.

**Repository**: github.com/virattt/ai-hedge-fund  
**Primary Language**: Python (src/, app/backend/, v2/) + TypeScript (app/frontend/)  
**Commit**: 0f6ac48  
**Total Source Files**: ~235 (125 .py, 110 .ts/.tsx)

## Structure & Depth Detection

### Top-Level Modules
| Module | Files | LOC | Role |
|--------|-------|-----|------|
| src/agents/ | 22 | ~7000 | AI investor agent definitions |
| src/backtesting/ | 11 | ~3500 | Historical backtesting engine |
| src/graph/ | 2 | ~180 | LangGraph workflow orchestration |
| src/data/ | 3 | ~250 | Data models & caching |
| src/llm/ | 2 | ~260 | LLM model configuration |
| src/tools/ | 2 | ~300 | Financial data API tools |
| src/utils/ | 9 | ~1500 | Utilities (display, progress, etc.) |
| src/cli/ | 2 | ~200 | CLI argument parsing |
| app/backend/ | 34 | ~4100 | FastAPI web backend |
| app/frontend/src/ | 108 | ~14200 | React/TypeScript frontend |
| v2/ | 20 | ~870 | Next-gen quantitative pipeline |
| tests/ | 15 | ~1200 | Test suite |

### Depth Decision: 3-LEVEL
- 5+ major functional areas (agents, backtesting, core infra, webapp, v2)
- Each has meaningful sub-structure
- Total ~235 source files across Python + TypeScript

### Wiki Structure Plan
```
L0: AI Hedge Fund (project hub)
├── L1: agents_doc/ (22 agent files → 3 L2 sub-pages)
│   ├── L2: investor-personas/ (13 famous investor agents)
│   ├── L2: quantitative/ (fundamentals, technicals, sentiment, valuation)
│   └── L2: management/ (risk manager + portfolio manager)
├── L1: backtesting_doc/ (backtesting engine)
│   ├── L2: engine/ (core engine, controller, trader)
│   └── L2: portfolio/ (portfolio tracking, metrics, output)
├── L1: core_doc/ (core infrastructure)
│   ├── L2: graph/ (LangGraph state + workflow)
│   └── L2: data-tools/ (data models, cache, API tools, LLM config)
├── L1: webapp_doc/ (full-stack web application)
│   ├── L2: backend/ (FastAPI backend)
│   └── L2: frontend/ (React frontend)
└── L1-flat: v2/ (next-gen pipeline, WIP)
```

## Key Dependencies
- LangGraph/LangChain: Agent orchestration framework
- OpenAI/Groq/Anthropic: LLM providers
- Financial Datasets API: Market data source
- FastAPI: Web backend framework
- React Flow: Visual workflow editor (frontend)
- SQLAlchemy: Database ORM
- Pydantic: Data validation

## Cross-Module Dependencies
- src/agents/* → src/graph/state.py (AgentState)
- src/agents/* → src/tools/api.py (financial data)
- src/agents/* → src/llm/models.py (LLM configuration)
- src/main.py → src/graph/ + src/agents/ + src/utils/
- src/backtesting/ → src/agents/ + src/graph/ + src/tools/
- app/backend/services/graph.py → src/agents/ + src/graph/
- app/backend/services/backtest_service.py → src/backtesting/

## Architectural Patterns
1. **Multi-Agent Pipeline** (fan-out/fan-in): All analyst agents run in parallel, then converge to risk manager → portfolio manager
2. **LangGraph StateGraph**: Directed graph with shared state (AgentState with messages, data, metadata)
3. **Repository Pattern**: Backend uses repositories for database access
4. **SSE Streaming**: Real-time execution updates via Server-Sent Events
5. **Visual Workflow Builder**: React Flow-based drag-and-drop agent composition
6. **Persona-Based Prompting**: Each agent has a system prompt embodying a famous investor's philosophy

## Key Algorithms & Mechanisms
1. **Agent Signal Aggregation**: Each agent produces a signal (bullish/bearish/neutral with confidence), risk manager aggregates
2. **Portfolio Position Sizing**: Kelly criterion and risk-adjusted position sizing
3. **Backtesting Engine**: Day-by-day historical simulation with the full agent pipeline
4. **Mean-Variance Optimization** (v2): Portfolio weight optimization using Markowitz framework
5. **LLM Tool Calling**: Agents use function calling to retrieve financial data

## Terminology
- **Analyst Agent**: An LLM-powered agent with a specific investing persona
- **Signal**: A trading recommendation (bullish/bearish/neutral) with confidence score
- **AgentState**: LangGraph shared state containing messages, data, and metadata
- **Portfolio**: Cash + positions (long/short) with cost basis tracking
- **Margin**: Collateral required for short positions
- **Flow**: A saved visual workflow configuration in the web app
- **Node**: A visual element in the React Flow graph (agent, input, output)
