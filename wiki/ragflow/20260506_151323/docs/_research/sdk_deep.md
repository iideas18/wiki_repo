# SDK Module Deep-Dive

## Existence Rationale

RAGFlow's REST API is feature-complete but verbose: every chat requires auth headers, URL construction, JSON marshalling. Without the SDK, users write boilerplate. The SDK layer wraps the REST protocol so users call kb.search('query') instead of constructing HTTP requests, while maintaining the full flexibility of the API.

### Real-World Analogy
The SDK is like Anthropic's python-sdk for Claude. Anthropic could just document the REST API, but the SDK makes it idiomatic Python (context managers, exception classes, dataclass models) instead of raw HTTP.

## Core Design Decisions

| Decision | Choice | Alternative | Why |
|----------|--------|-------------|-----|
| Dataclass models for responses | Type-safe Pydantic models | Dict responses (no validation) | IDE autocompletion, runtime validation prevent silent bugs. |
| Async/await support | Concurrent requests | Sync-only | Enables fast batch operations (upload 100 docs in parallel). |
| Context manager pattern | Resource cleanup (close HTTP pool) | Manual close() | Prevents connection leaks. |
| Token refresh on 401 | Automatic retry after token refresh | Manual re-auth | Transparent to user; long-lived clients work seamlessly. |


## Algorithm Spotlight

N/A — straightforward data flow, no complex algorithms.

## Failure Modes & Recovery

| Failure | Trigger | Detection | Recovery |
|---------|---------|-----------|----------|
| Invalid API key | 401 from server | SDK raises AuthenticationError | User catches and logs in. |
| Rate limit hit | 429 response | SDK retries with exponential backoff | Eventually succeeds or raises RateLimitError after max retries. |
| Network timeout | No response within timeout | Raises TimeoutError | User retries or escalates. |


## Performance Notes

- ('Connection pooling (httpx)', 'Reuses TCP sockets; ~5ms vs ~100ms per request')
- ('Batch operations', 'Async allows uploading multiple documents in parallel')


## Key Files & Modules

- python/ragflow/client.py — Main RAGFlowClient class
- python/ragflow/modules/ — KB, Chat, Document, Agent submodules
