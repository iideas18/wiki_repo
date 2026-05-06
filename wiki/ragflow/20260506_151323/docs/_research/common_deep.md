# COMMON Module Deep-Dive

## Existence Rationale

RAGFlow's 91-file utility layer eliminates duplication. Without common/, every module would reimplement HTTP clients (with retry logic), crypto (AES-256), token counting (LLM-specific), and data source adapters. By centralizing these, common/ becomes the glue that lets RAGFlow scale elastically—adding new LLM providers, parsers, or data connectors requires only plugging into enums (LLMType, ParserType, TaskType), not rewriting boilerplate.

### Real-World Analogy
Think of common/ as the electrical wiring in a building. You don't re-run cables for each room; you wire once, then plug devices in. Similarly, common/ wires up crypto, HTTP, settings, and adapters so each module plugs in cleanly.

## Core Design Decisions

| Decision | Choice | Alternative | Why |
|----------|--------|-------------|-----|
| Centralized enum registry | LLMType, ParserType, TaskType enums in constants.py | Scattered definitions across modules, string literals | Single source of truth prevents typos; easy to add new provider. Alternatives would scatter config logic. |
| Pydantic BaseSettings for config | Type-safe environment variable binding | Dict-based config, manual parsing | Validation + IDE autocompletion reduce errors at startup, not runtime. |
| Async HTTP client (httpx) | Concurrent requests, connection pooling | Sequential requests (requests lib), sync I/O | Eliminates thread overhead; integrates with async event loop. Critical for throughput on I/O-bound data ingestion. |
| AES-256-GCM for secrets | AEAD (authenticated encryption) | Plain AES, unencrypted secrets | Prevents tampering + detects corruption. Auth tag catch modifications that plain modes miss. |
| Universal data source adapter pattern | Pluggable connectors via BaseSource | Hardcoded if/else for each type | New source (Jira, Slack) requires only implementing BaseSource contract, zero duplication. |
| Token counting per-LLM | Separate counter for each provider's tokenizer | One generic token approximation | Prevents over-billing. Qwen 14B uses different tokenizer than GPT-4; guessing wastes API quota. |


## Algorithm Spotlight

### SSRF Guard (ssrf_guard.py)
**Problem:** Blocks requests to private IP ranges (127.0.0.0/8, 10.0.0.0/8, etc.) even if DNS-rebind attack tries localhost. Validates against a static blocklist before HTTP client executes.
**Approach:** Prevents accidental data exfiltration via web scraping or webhook callbacks.
**Why:** O(1) set lookup per URL. Alternatives: runtime DNS check (slow), or naive IP parsing (incomplete CIDR math). This is fast + comprehensive.

## Failure Modes & Recovery

| Failure | Trigger | Detection | Recovery |
|---------|---------|-----------|----------|
| Crypto key not set | AES encryption called without KEY env var | ValueError at encrypt time | Caught early via Pydantic validation; app fails to start if keys missing. |
| Token counter unavailable for new LLM | Unknown LLMType used, but no tokenizer | Estimation fallback (0.25 tokens per word) | Logged as warn; fallback prevents crashes but may undercount. Admin adds tokenizer to registry. |
| Data source adapter error | S3 bucket not accessible, GCS auth expires | Caught in connector.fetch(); propagates up | Retry loop in SDK layer; user sees 'Data fetch failed' with reason (auth / timeout). |


## Performance Notes

- ('HTTP client connection pooling', 'Reuses TCP sockets across requests. Default pool size 10.', '~100ms per request (no pooling) vs ~5ms (warm pool)')
- ('Token counting cache', 'Memoized tokenizer results per LLM', 'Prevents re-instantiating tokenizer on every chunk (~1-2ms per init)')
- ('Data source streaming', 'Reads large files in chunks, not memory', 'S3 downloads: 4MB chunks avoid full-buffer OOM')


## Key Files & Modules

- settings.py — Global config (Pydantic BaseSettings)
- constants.py — Enums: LLMType, ParserType, TaskType, RetCode
- crypto_utils.py — AES-256-GCM encryption, key derivation
- token_utils.py — Token counting for OpenAI/Claude/Qwen
- string_utils.py — Text normalization, regex helpers
- http_client.py — Async HTTP with retries & redirect limits
- mcp_tool_call_conn.py — Model Context Protocol integration
- data_source/ — Adapters for S3, SharePoint, Gitlab, RSS
- doc_store/ — ES & OceanBase connection pooling
- exceptions.py — Custom exception hierarchy
