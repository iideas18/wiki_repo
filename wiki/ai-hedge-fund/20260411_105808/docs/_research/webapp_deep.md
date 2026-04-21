# Phase 1B — Web Application Module Deep Analysis

## Existence Rationale
The web application (app/backend/) exists to provide a visual, interactive interface for the AI hedge fund. The CLI is powerful but requires technical users. The web app democratizes access by offering a React-based UI where users can visually compose agent pipelines (via a node graph editor), run analyses, execute backtests, and view results in real-time via Server-Sent Events. Without this module, the system would be CLI-only.

## Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|----------|------------|----------------------|-------------------|
| FastAPI | Async Python web framework | Flask, Django, Express.js | Native async support for SSE streaming; Pydantic integration matches data models |
| SQLite | File-based database | PostgreSQL, MongoDB | Zero configuration; educational project doesn't need production DB |
| SQLAlchemy ORM | Declarative models | Raw SQL, Tortoise ORM | Industry standard; Alembic migration support |
| Server-Sent Events | One-way streaming for progress updates | WebSockets, polling | Simpler than WebSockets for unidirectional updates; native HTTP |
| React Flow UI | Node-based graph editor for agent composition | Form-based config, drag-and-drop list | Visual representation matches the underlying LangGraph architecture |
| API key storage in DB | Encrypted storage with provider-based keys | Environment variables only | Web users can't edit .env files; per-provider granularity |
| Repository pattern | Separate repository classes for DB access | Direct ORM queries in routes | Testability and separation of concerns |

## Architecture

### Layer Structure
```
Routes (API endpoints)
  → Services (business logic)
    → Repositories (data access)
      → Database (SQLAlchemy ORM)
```

### Key Routes
| Route | Method | Purpose |
|-------|--------|---------|
| /api/hedge-fund/run | POST | Run single analysis with SSE streaming |
| /api/hedge-fund/backtest | POST | Run historical backtest with SSE streaming |
| /api/flows | CRUD | Manage flow configurations (node graphs) |
| /api/flow-runs | CRUD | Manage flow execution history |
| /api/api-keys | CRUD | Manage LLM provider API keys |
| /api/language-models | GET | List available LLM models |
| /api/ollama/* | GET/POST | Ollama local model management |
| /api/health | GET | Health check |

### Database Models
1. **HedgeFundFlow**: Stores node graph configurations (nodes, edges, viewport, data as JSON)
2. **HedgeFundFlowRun**: Execution records with status tracking (IDLE→IN_PROGRESS→COMPLETE/ERROR)
3. **HedgeFundFlowRunCycle**: Per-cycle details (signals, decisions, trades, portfolio snapshots)
4. **ApiKey**: Provider-specific API key storage

### SSE Event System
```python
BaseEvent → StartEvent | ProgressUpdateEvent | ErrorEvent | CompleteEvent
```
Each event serializes to SSE format: `event: {type}\ndata: {json}\n\n`

## Service Layer

### AgentService
- Wraps `run_hedge_fund()` with web-specific adaptations
- Resolves agent models from graph node configurations
- Streams progress via SSE events
- Handles API key injection from database

### BacktestService
- Runs BacktestEngine with SSE progress streaming
- Converts results to BacktestResponse schema

### GraphService
- Builds LangGraph workflow from web UI node configurations
- Maps node IDs to agent functions
- Supports per-agent model selection

## Error Philosophy
- HTTP 404 for missing resources (flows, runs)
- HTTP 500 with error message for agent failures
- SSE ErrorEvent for streaming failures
- Database session cleanup via dependency injection (get_db)

## Evolution Clues
- Alembic migrations show incremental schema additions (flow → flow_run → flow_run_cycle → api_keys)
- `services/portfolio.py` exists but is thin — web portfolio management is still developing
- `routes/storage.py` suggests file upload capability was planned
- Ollama integration suggests local/offline support was a priority
