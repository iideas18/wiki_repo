# Phase 1A — Broad Survey: AI Hedge Fund

## Project Identity
- **Name**: AI Hedge Fund
- **Repository**: github.com/virattt/ai-hedge-fund
- **Language**: Python (100%)
- **Framework**: LangGraph + LangChain + FastAPI
- **Git SHA**: c45b50f
- **Source File Count**: 107 Python files (~20,080 LOC)

## Structure & Depth Detection

### Top-Level Layout
```
ai-hedge-fund/
├── src/                    ← Core trading logic
│   ├── agents/             ← 19 analyst agents + 2 management agents (20 files)
│   ├── backtesting/        ← Backtesting engine (10 files)
│   ├── data/               ← Data models & caching (3 files)
│   ├── graph/              ← LangGraph state (2 files)
│   ├── llm/                ← LLM provider abstraction (2 files + JSON configs)
│   ├── tools/              ← Financial API client (2 files)
│   ├── utils/              ← Utilities (8 files)
│   ├── cli/                ← CLI input parsing (2 files)
│   ├── main.py             ← CLI entry point
│   └── backtester.py       ← Backtest entry point
├── app/
│   ├── backend/            ← FastAPI web server (20+ files, 5 sub-dirs)
│   └── frontend/           ← React UI (node_modules present)
├── tests/                  ← Unit & integration tests
├── docker/                 ← Docker configuration
├── pyproject.toml          ← Poetry dependencies
└── README.md
```

### Depth Decision
- **Result**: 3-level project
- src/ has 8+ sub-module dirs with source files
- app/backend/ has 5 sub-directories (database, models, repositories, routes, services)
- Sufficient complexity for L0 hub + L1 overviews + L2 deep dives

## Module Classification

| Module | Dir | Files | LOC | Role | L1 Type |
|--------|-----|-------|-----|------|---------|
| agents | src/agents/ | 21 | ~8,500 | AI analyst agents with distinct investment philosophies | L1 + L2 |
| backtesting | src/backtesting/ | 10 | ~1,800 | Historical simulation engine | L1 + L2 |
| data & orchestration | src/data/, src/graph/, src/tools/, src/llm/ | 9 | ~2,200 | Data pipeline, state machine, LLM abstraction | L1 + L2 |
| web application | app/backend/ | 20+ | ~3,500 | FastAPI REST API with SSE streaming | L1 + L2 |
| utilities | src/utils/, src/cli/ | 10 | ~1,200 | Display, progress tracking, CLI parsing | Covered in parent |

## Cross-Module Dependencies

```
main.py
  → agents/* (via utils/analysts.py registry)
  → graph/state.py (AgentState TypedDict)
  → utils/display.py (output formatting)

agents/*
  → tools/api.py (financial data fetching)
  → data/cache.py (response caching)
  → data/models.py (Pydantic schemas)
  → graph/state.py (AgentState, show_agent_reasoning)
  → utils/llm.py (call_llm helper)
  → llm/models.py (get_model, ModelProvider)

backtesting/engine.py
  → main.py/run_hedge_fund (the agent callable)
  → backtesting/controller.py → portfolio.py → trader.py
  → backtesting/metrics.py, valuation.py, output.py
  → tools/api.py (data prefetching)

app/backend/
  → services/agent_service.py → main.py/run_hedge_fund
  → services/graph.py (modified workflow for web)
  → database/ (SQLAlchemy ORM)
  → routes/ (FastAPI endpoints)
```

## Key Architectural Patterns

1. **Multi-Agent Ensemble**: 19 independent analyst agents run in parallel via LangGraph, each producing bullish/bearish/neutral signals with confidence scores
2. **Fan-Out/Fan-In**: Agents fan out from start_node, fan back into risk_management_agent, then portfolio_manager
3. **Agent State Bus**: Shared TypedDict (AgentState) with merge-dict reducers for message passing
4. **Separation of Analysis and Decision**: Analysts only analyze; risk manager sets position limits; portfolio manager makes final trades
5. **Cache-Through Data Layer**: API responses cached in-memory with dedup merging
6. **LLM-Agnostic**: Supports 13 LLM providers via factory pattern

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| Orchestration | LangGraph | latest |
| LLM Framework | LangChain | latest |
| Web Framework | FastAPI | latest |
| Database | SQLite (SQLAlchemy) | - |
| Data Validation | Pydantic v2 | latest |
| HTTP Client | requests | - |
| Data Analysis | pandas, numpy | - |
| CLI | questionary, colorama | - |
| Frontend | React + Vite | - |
| Package Manager | Poetry | - |

## 19 Analyst Agents

### Investor-Inspired (13):
1. Aswath Damodaran — DCF valuation specialist
2. Ben Graham — Value investing, margin of safety
3. Bill Ackman — Activist investing, business quality
4. Cathie Wood — Disruptive innovation, growth
5. Charlie Munger — Moat analysis, quality businesses
6. Michael Burry — Contrarian deep value
7. Mohnish Pabrai — Dhandho: heads-I-win, tails-I-don't-lose-much
8. Nassim Taleb — Tail risk, antifragility, convexity
9. Peter Lynch — GARP, PEG ratio, "buy what you know"
10. Phil Fisher — Scuttlebutt, management quality, innovation
11. Rakesh Jhunjhunwala — Growth + value, emerging markets
12. Stanley Druckenmiller — Macro + momentum
13. Warren Buffett — Owner earnings, competitive moat, circle of competence

### Quantitative/Analytical (6):
14. Technical Analyst — Multi-strategy: trend, mean reversion, momentum, volatility, stat arb
15. Fundamentals Analyst — Financial statement analysis (profitability, growth, health, valuation)
16. Growth Analyst — Revenue/earnings growth trajectory
17. Sentiment Analyst — Market sentiment via insider trades
18. News Sentiment Analyst — News headline sentiment analysis
19. Valuation Analyst — DCF and comparable valuation

### Management (2):
20. Risk Manager — Volatility-adjusted position sizing with correlation analysis
21. Portfolio Manager — Final trade decisions via LLM with deterministic constraints

## Terminology

| Term | Definition |
|------|-----------|
| AgentState | LangGraph TypedDict shared across all agents (messages, data, metadata) |
| Signal | Agent output: bullish/bearish/neutral with confidence 0-100 |
| Fan-out/Fan-in | Parallel agent execution pattern in LangGraph |
| Margin of Safety | Discount of market price vs intrinsic value |
| PEG Ratio | Price/Earnings to Growth ratio |
| Owner Earnings | Buffett's FCF proxy: net income + D&A - capex |
| Hurst Exponent | Statistical measure: <0.5 mean-reverting, =0.5 random, >0.5 trending |
| ADX | Average Directional Index — trend strength indicator |
| FCFF | Free Cash Flow to Firm — DCF input |
| CAPM | Capital Asset Pricing Model — cost of equity estimation |
| Barbell Strategy | Taleb: extreme safety + extreme risk, nothing in between |
| Dhandho | Pabrai: "heads I win big, tails I don't lose much" |
| Scuttlebutt | Fisher: qualitative research on management and products |
| BacktestEngine | Orchestrator that runs the trading system over historical dates |
| TradeExecutor | Validates and executes buy/sell/short/cover orders |
| Portfolio | Tracks cash, positions (long/short), margin, realized gains |
