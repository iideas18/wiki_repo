# Web Application — Deep Analysis

## Existence Rationale
The web application (app/) provides a visual, interactive interface for the hedge fund system. The CLI requires coding knowledge and has no persistence. The web app adds: visual workflow building (drag-and-drop agent composition), persistent flow configurations, execution history tracking, and real-time streaming output. Without it, the system is a command-line tool for developers only.

## Design Decisions
| Decision | Choice Made | Alternatives | Rationale |
|----------|------------|-------------|-----------|
| Backend framework | FastAPI | Flask, Django, Express | Async support, built-in OpenAPI docs, Pydantic integration |
| Frontend framework | React + TypeScript | Vue, Svelte, Angular | Ecosystem maturity, React Flow library availability |
| Visual editor | React Flow | D3.js, GoJS, custom canvas | Purpose-built for node-based editors, excellent API |
| Streaming | Server-Sent Events (SSE) | WebSocket, Long polling | One-way streaming is sufficient, simpler than WebSocket |
| Database | SQLite via SQLAlchemy | PostgreSQL, MongoDB | Zero-config, sufficient for educational prototype |
| State management | React hooks + Context | Redux, Zustand, MobX | Simpler, fewer dependencies, sufficient for app size |

## Backend Architecture
- **Repository Pattern**: Data access abstracted through repository classes
- **Service Layer**: Business logic in services/ (graph construction, backtesting, portfolio)
- **Route Layer**: API endpoints in routes/ (REST + SSE streaming)
- **SSE Event Flow**: Start → Progress (per-agent) → Complete/Error

## Frontend Architecture
- **6 Node Types**: AgentNode, PortfolioManager, PortfolioStart, StockInput, JsonOutput, InvestmentReport
- **12 Custom Hooks**: Flow management, node state, connections, keyboard shortcuts
- **Dynamic Agent Loading**: Agents discovered from backend at runtime
- **Per-Agent Model Selection**: Each agent node can override the global LLM model

## Error Philosophy
Backend: HTTP error codes + structured error responses. Frontend: Toast notifications for user-facing errors, console logging for debug. SSE streams include error events for graceful degradation.
