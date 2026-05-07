# TOOLS Module Deep-Dive

## Existence Rationale

tools/ collects integrations that don't fit the core engine: WeChat bot adapter (enterprise messaging), database migration (operational task), web scraper (optional enrichment). Without tools/, these would either clutter the main codebase or be external, hard to maintain.

### Real-World Analogy
tools/ is like a carpenter's toolbelt: hammer, screwdriver, level. Each tool solves a specific job, but you don't need all of them every day.

## Core Design Decisions

| Decision | Choice | Alternative | Why |
|----------|--------|-------------|-----|
| Separate from core | tools/ excluded from SDK | Tools bundled with SDK (unused overhead) | Users only install what they need. |
| Standalone executables | Each tool can be used independently | Tightly coupled to core | Easy to debug, version independently. |


## Algorithm Spotlight

N/A — straightforward data flow, no complex algorithms.

## Failure Modes & Recovery

| Failure | Trigger | Detection | Recovery |
|---------|---------|-----------|----------|
| ES cluster down during migration | Extract phase times out | Caught and logged; user can retry with checkpoint | Migration is resumable from last successful batch. |
| Web scraper hits rate limit | Firecrawl 429 response | Backoff + retry with exponential delay | Eventually succeeds or raises if limit persists. |


## Performance Notes

- ('Batch insert for migrations', '1000-row chunks vs single rows: 100x faster')


## Key Files & Modules

- chatgpt-on-wechat/ — WeChat bot integration
- es-to-oceanbase-migration/ — Data migration utilities
- firecrawl/ — Web scraper adapter
- scripts/ — Deployment, testing, utility scripts
