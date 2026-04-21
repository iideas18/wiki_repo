# Phase 1B — Data & Orchestration Module Deep Analysis

## Existence Rationale
The data module (data/, tools/, graph/, llm/) serves as the connective tissue of the system. It exists because the trading agents need three things that aren't their responsibility: (1) fetching financial data from external APIs, (2) managing shared state as data flows between agents, and (3) abstracting away which LLM provider is being used. Without this layer, every agent would need its own API client, its own caching logic, and its own LLM initialization — a maintenance nightmare.

## Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|----------|------------|----------------------|-------------------|
| In-memory cache (Cache class) | Dict-based cache with dedup merging | Redis, SQLite, file-based | Simplicity — no external dependencies; cache is session-scoped |
| Pydantic models for API responses | Strongly typed response parsing | Raw dicts, dataclasses | Validation, serialization, IDE support |
| Single API provider | financialdatasets.ai for all financial data | Multiple providers (Alpha Vantage, Yahoo, etc.) | Consistent API, single API key |
| LangGraph StateGraph | TypedDict with merge-dict reducers | Custom event bus, message queue | LangGraph provides parallel execution, state management, graph compilation |
| AgentState as TypedDict | messages + data + metadata with operator.add/merge_dicts | Class-based state, Redis-backed | TypedDict is lightweight and works natively with LangGraph |
| Factory pattern for LLMs | get_model() returns provider-specific client | Abstract base class hierarchy | Simplicity — one function, 13 elif branches |
| Rate limiting with linear backoff | 60s, 90s, 120s delays on 429 responses | Exponential backoff, token bucket | Conservative — financial API rate limits are strict |
| Cache key includes all params | f"{ticker}_{start}_{end}" composite key | Ticker-only keys with range overlap detection | Exact match is simpler and avoids stale data from partial overlaps |

## Algorithm Deep-Dives

### 1. Cache Merge Strategy (Cache._merge_data)
- **Problem**: Multiple API calls may return overlapping data (e.g., overlapping date ranges)
- **Approach**: Set-based dedup using a key field (e.g., "time" for prices, "report_period" for metrics)
- **Steps**: Build set of existing keys → extend with new items not in set
- **Complexity**: O(n+m) where n=existing, m=new
- **Why not replace**: Preserves data from earlier, wider date range queries

### 2. LangGraph Fan-Out/Fan-In Workflow
- **Problem**: Run 19 agents in parallel, collect results, feed to risk manager then portfolio manager
- **Graph structure**: start_node → [all analysts in parallel] → risk_management_agent → portfolio_manager → END
- **State merge**: operator.add for messages (append), merge_dicts for data (shallow merge)
- **Why LangGraph**: Built-in parallel execution, state persistence, graph visualization

### 3. LLM Provider Abstraction (get_model)
- **Problem**: Support 13 different LLM providers with different SDKs
- **Approach**: Factory function with provider enum → specific LangChain chat class
- **Providers**: OpenAI, Anthropic, Google, Groq, DeepSeek, Ollama, OpenRouter, xAI, GigaChat, Azure OpenAI, Alibaba, Meta, Mistral
- **Why factory over class hierarchy**: Most providers need just 2-3 lines of setup; OOP would be over-engineering

## API Functions
| Function | Endpoint | Cache | Returns |
|----------|----------|-------|---------|
| get_prices | /prices/ | ✓ | list[Price] |
| get_financial_metrics | /financial-metrics/ | ✓ | list[FinancialMetrics] |
| search_line_items | /financials/search/line-items (POST) | ✗ | list[LineItem] |
| get_insider_trades | /insider-trades/ | ✓ | list[InsiderTrade] |
| get_company_news | /news/ | ✓ | list[CompanyNews] |
| get_market_cap | /company/facts/ or /financial-metrics/ | via metrics | float |
| prices_to_df | (local transform) | ✗ | pd.DataFrame |

## Pydantic Data Models
- Price: open, close, high, low, volume, time
- FinancialMetrics: 40+ financial ratios and metrics
- LineItem: ticker, period + dynamic extra fields
- InsiderTrade: transaction details, shares, filing date
- CompanyNews: title, source, date, url, sentiment
- CompanyFacts: company metadata (industry, sector, market_cap, employees)
- AnalystSignal: signal, confidence, reasoning, max_position_size

## Error Philosophy
- API failures → return empty list (never raise)
- Parse failures → log warning, return empty
- Cache misses → fetch from API, populate cache
- Rate limits → linear backoff with retry (max 3 attempts)
