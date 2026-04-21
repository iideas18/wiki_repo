# agent/ — Core Agent Engine

## 1. Purpose

The `agent/` module is Hermes Agent's core orchestration and utility layer extracted from a 3,600-line `run_agent.py`. It provides pluggable context management (compression, external memory), smart model routing, API error classification, credential lifecycle management, rate-limiting tracking, token estimation, prompt caching, and domain-specific utilities (skills parsing, title generation, secret redaction). This modular design enables Nous Research's self-improving AI agent to maintain long conversations, gracefully degrade across providers, and intelligently allocate computational resources across multiple backends.

## 2. Key Classes/Functions

| Class/Function | File | Role |
|---|---|---|
| `ContextEngine` | `context_engine.py` | Abstract base for pluggable context management engines (compress, external DAGs, etc.) |
| `ContextCompressor` | `context_compressor.py` | Default context engine; compresses conversations via lossy LLM summarization with iterative updates |
| `MemoryManager` | `memory_manager.py` | Orchestrates built-in + at most one external memory provider; enforces single external provider limit |
| `MemoryProvider` | `memory_provider.py` | Abstract base for persistent recall backends (Honcho, Hindsight, Mem0, built-in) |
| `classify_api_error()` | `error_classifier.py` | Priority-ordered taxonomy mapping exceptions → recovery actions (retry, rotate, fallback, compress, abort) |
| `jittered_backoff()` | `retry_utils.py` | Decorrelated exponential backoff to prevent thundering-herd retry spikes |
| `RateLimitState` | `rate_limit_tracker.py` | Captures x-ratelimit-* headers from responses; tracks RPM/TPM buckets |
| `CredentialPool` | `credential_pool.py` | Multi-credential failover for same-provider load balancing and round-robin rotation |
| `call_llm()` | `auxiliary_client.py` | Unified resolution chain for side-task LLM calls (compression, title gen, vision); automatic fallback on 402 |
| `SubdirectoryHintTracker` | `subdirectory_hints.py` | Lazily loads AGENTS.md/.cursorrules from subdirectories as agent navigates; injects via tool results |
| `build_system_prompt()` | `prompt_builder.py` | Assembles system prompt: identity, platform hints, skills index, context files with injection detection |
| `generate_title()` | `title_generator.py` | Async background title generation from first exchange; uses auxiliary client |
| `apply_anthropic_cache_control()` | `prompt_caching.py` | Injects cache_control breakpoints (system + last 3 non-system messages) for Anthropic 75% cost reduction |
| `estimate_messages_tokens_rough()` | `model_metadata.py` | 4 chars/token heuristic + provider-specific adjustments for pre-flight context checks |
| `InsightsEngine` | `insights.py` | Analyzes session DB for token consumption, costs, tool usage, trends, platform breakdowns |
| `redact_secrets()` | `redact.py` | Regex-based secret masking (API keys, tokens, credentials) before logs/output |

## 3. Representative Snippets

**Snippet 1: Context Compression Decision Loop**
```python
# context_compressor.py line 177-180
def should_compress(self, prompt_tokens: int = None) -> bool:
    """Check if context exceeds the compression threshold."""
    tokens = prompt_tokens if prompt_tokens is not None else self.last_prompt_tokens
    return tokens >= self.threshold_tokens
```

**Snippet 2: Jittered Backoff for Concurrent Retries**
```python
# retry_utils.py lines 19-57
def jittered_backoff(
    attempt: int,
    *, base_delay: float = 5.0, max_delay: float = 120.0, jitter_ratio: float = 0.5,
) -> float:
    global _jitter_counter
    with _jitter_lock:
        _jitter_counter += 1
        tick = _jitter_counter
    exponent = max(0, attempt - 1)
    if exponent >= 63 or base_delay <= 0:
        delay = max_delay
    else:
        delay = min(base_delay * (2 ** exponent), max_delay)
    seed = (time.time_ns() ^ (tick * 0x9E3779B9)) & 0xFFFFFFFF
    rng = random.Random(seed)
    jitter = rng.uniform(0, jitter_ratio * delay)
    return delay + jitter
```

**Snippet 3: Error Classification Priority Pipeline**
```python
# error_classifier.py lines 233-251
def classify_api_error(
    error: Exception, *, provider: str = "", model: str = "",
    approx_tokens: int = 0, context_length: int = 200000, num_messages: int = 0,
) -> ClassifiedError:
    """Classify an API error into a structured recovery recommendation.
    Priority-ordered pipeline:
      1. Special-case provider-specific patterns (thinking sigs, tier gates)
      2. HTTP status code + message-aware refinement
      3. Error code classification (from body)
      4. Message pattern matching (billing vs rate_limit vs context vs auth)
      5. Transport error heuristics
      6. Server disconnect + large session → context overflow
      7. Fallback: unknown (retryable with backoff)
    """
```

**Snippet 4: Prompt Caching Strategy (system_and_3)**
```python
# prompt_caching.py lines 41-72
def apply_anthropic_cache_control(
    api_messages: List[Dict[str, Any]], cache_ttl: str = "5m", native_anthropic: bool = False,
) -> List[Dict[str, Any]]:
    """Apply system_and_3 caching strategy to messages for Anthropic models.
    Places up to 4 cache_control breakpoints: system prompt + last 3 non-system messages.
    Returns: Deep copy of messages with cache_control breakpoints injected.
    """
    messages = copy.deepcopy(api_messages)
    if not messages:
        return messages
    marker = {"type": "ephemeral"}
    if cache_ttl == "1h":
        marker["ttl"] = "1h"
    breakpoints_used = 0
    if messages[0].get("role") == "system":
        _apply_cache_marker(messages[0], marker, native_anthropic=native_anthropic)
        breakpoints_used += 1
    remaining = 4 - breakpoints_used
    non_sys = [i for i in range(len(messages)) if messages[i].get("role") != "system"]
    for idx in non_sys[-remaining:]:
        _apply_cache_marker(messages[idx], marker, native_anthropic=native_anthropic)
    return messages
```

**Snippet 5: Memory Manager Single-External-Provider Constraint**
```python
# memory_manager.py lines 85-107
def add_provider(self, provider: MemoryProvider) -> None:
    """Register a memory provider. Built-in provider (name ``"builtin"``) is always accepted.
    Only **one** external (non-builtin) provider is allowed — a second attempt is rejected.
    """
    is_builtin = provider.name == "builtin"
    if not is_builtin:
        if self._has_external:
            existing = next((p.name for p in self._providers if p.name != "builtin"), "unknown")
            logger.warning("Rejected memory provider '%s' — external provider '%s' is already registered.", ...)
            return
        self._has_external = True
    self._providers.append(provider)
```

## 4. Data Flow

**Turn Lifecycle:**

1. **Pre-turn**: User message → `SubdirectoryHintTracker.check_tool_call()` extracts paths → `MemoryManager.prefetch_all()` recalls context from all providers → `build_memory_context_block()` fences recalled context
2. **System Prompt Assembly**: `prompt_builder._build_system_prompt()` combines identity + skills index + context files (AGENTS.md, .cursorrules) + injected-threat scans → `MemoryManager.build_system_prompt()` adds provider blocks → `ContextEngine.get_status()` for display
3. **API Call Preparation**: Messages + system prompt → optional `apply_anthropic_cache_control()` (Anthropic) → `estimate_messages_tokens_rough()` pre-flight check → `ContextEngine.should_compress_preflight()` (cheap estimate)
4. **API Call & Response**: `call_llm()` resolves auxiliary client (OpenRouter → Nous Portal → Codex → Anthropic fallback chain) → response includes `x-ratelimit-*` headers → `parse_rate_limit_headers()` → `ContextEngine.update_from_response(usage)`
5. **Post-turn**: `ContextEngine.should_compress()` checks threshold → if true, `compress(messages)` → `MemoryManager.sync_all(user_msg, asst_response)` writes to providers → `MemoryManager.queue_prefetch_all()` background recall for next turn
6. **Error Recovery**: Exception → `classify_api_error()` → if `should_rotate_credential`: `CredentialPool.select_next()` → retry; if `should_compress`: manual trigger; if `should_fallback`: switch model; if `retryable`: `jittered_backoff()` then retry

**Context Compression Algorithm:**

1. Input: full message list, compression trigger
2. `_prune_old_tool_results()`: replace old tool outputs with placeholder (cheap pre-pass, no LLM)
3. `should_compress()`: check `tokens >= threshold_tokens`
4. `compress(messages)`: 
   - Protect first N messages (system + opening exchange)
   - Protect last M tokens (recent context)
   - Summarize middle turns via `_generate_summary()`
   - On subsequent compressions, iteratively update `_previous_summary`
5. Output: compacted message list with summary injection + tail

## 5. Config/Knobs

| Parameter | File | Default | What It Controls |
|---|---|---|---|
| `context.engine` | config.yaml | "compressor" | Which context engine active (plugin override possible) |
| `context.threshold_percent` | ContextCompressor.__init__ | 0.75 | When to trigger compression (% of max context) |
| `context.protect_first_n` | ContextCompressor.__init__ | 3 | System + opening messages to keep uncompressed |
| `context.protect_last_n` | ContextCompressor.__init__ | 20 | Tail token budget (instead of fixed message count) |
| `context.summary_target_ratio` | ContextCompressor.__init__ | 0.20 | Summary size as % of compressed content |
| `model.context_length` | context_engine.py | auto-detect | Override model's context window (forces validation) |
| `memory.provider` | config.yaml | "builtin" | External memory backend (Honcho, Hindsight, Mem0, etc.) |
| `smart_model_routing.enabled` | smart_model_routing.py | False | Enable cheap-model route for simple queries |
| `smart_model_routing.cheap_model` | config.yaml | N/A | Model dict {provider, model} for simple turns |
| `smart_model_routing.max_simple_chars` | smart_model_routing.py | 160 | Max input length to qualify for cheap route |
| `smart_model_routing.max_simple_words` | smart_model_routing.py | 28 | Max word count for cheap route |
| `auxiliary.compression.provider` | config.yaml | "auto" | LLM provider for compression summaries |
| `auxiliary.compression.model` | config.yaml | "auto" | Model for compression (defaults to cheapest) |
| `auxiliary.vision.provider` | config.yaml | "auto" | Multimodal provider override |
| `prompt_caching.ttl` | prompt_caching.py | "5m" | Anthropic cache TTL ("5m" or "1h") |
| `rate_limit.capture_headers` | rate_limit_tracker.py | True | Whether to parse x-ratelimit-* headers |
| `redact.enabled` | redact.py | True (via env) | HERMES_REDACT_SECRETS env var |

## 6. Interactions

| Module | How It Integrates | Via What Interface |
|---|---|---|
| `run_agent.py` (AIAgent orchestrator) | Primary consumer; instantiates ContextEngine, MemoryManager, calls prompt_builder | `ContextEngine.compress()`, `MemoryManager.prefetch_all()`, `prompt_builder._build_system_prompt()` |
| `tools/` (skill execution) | Skills are indexed in system prompt via `skill_commands.py`, injected from SKILLS_DIR via frontmatter parsing | `skill_utils.parse_frontmatter()`, `skill_commands._load_skill_payload()` |
| `hermes_cli/config.py` | Config values for thresholds, model overrides, provider selection | `load_config()` called by auxiliary_client resolution |
| `hermes_cli/auth.py` | Credential lifecycle (OAuth refresh, token expiry, provider state) | `CredentialPool` reads/writes via `read_credential_pool()`, `write_credential_pool()` |
| `hermes_cli/runtime_provider.py` | Resolves actual runtime (OpenRouter, Nous Portal, Anthropic, custom endpoint) | `auxiliary_client._resolve_auxiliary_client()` calls `resolve_runtime_provider()` |
| `tools/registry.py` | Tool schemas, error reporting | Memory tools registered via `MemoryProvider.get_tool_schemas()` |
| `tools/skills_tool.py` | Skill loading and validation | `skill_commands._load_skill_payload()` imports and calls `skill_view()` |
| `gateway/` | Multi-session gateway server | Uses same `ContextCompressor`, `MemoryManager`, error classification |
| External memory backends (Honcho, Mem0, Hindsight) | Plugin system: `plugins/memory/<name>/` | Abstract `MemoryProvider` class with standardized lifecycle |

## 7. Terminology

- **Context Window**: Maximum token capacity of a model (e.g. 200k for Claude 3.5 Sonnet, 1M for Claude Opus 4.6)
- **Compression / Compaction**: Lossy conversion of middle conversation turns into a structured summary to stay within context budget
- **Threshold**: Token count at which compression triggers (e.g. 75% of max context = 150k for 200k model)
- **Preflight Check**: Cheap token estimate before API call to avoid context overflow
- **Tail Protection**: Keeping recent messages in full detail; prevents discarding user's current work
- **Head Protection**: Keeping system prompt and opening exchange uncompressed for consistency
- **Summary Iterative Update**: Updating a previous compaction summary with new turns (vs. summarizing from scratch)
- **Prefetch / Recall**: Background retrieval of relevant memory context before each API call
- **Memory Provider**: Pluggable backend for persistent recall (built-in file-based, or external Honcho/Mem0)
- **Auxiliary Client**: Fallback LLM chain for side tasks (compression, title generation, vision analysis)
- **Provider Fallback Chain**: Auto-detection order: OpenRouter → Nous Portal → Codex → Anthropic (for auxiliary tasks)
- **Credential Pool**: Multi-credential round-robin or least-used selector for same-provider failover
- **Jittered Backoff**: Exponential delay with random jitter to decorrelate concurrent retries across sessions
- **Rate Limit State**: Parsed x-ratelimit-* headers tracking RPM/TPM buckets, remaining capacity, reset times
- **Context Overflow**: Exception indicating input tokens exceed model's max context; triggers compression
- **Skillfront-matter**: YAML metadata block in skill markdown (config overrides, platform conditions)
- **Subdirectory Hints**: Lazy discovery of AGENTS.md/.cursorrules as agent navigates into new directories
- **Prompt Injection Detection**: Regex scanning of context files (AGENTS.md, .cursorrules) for "ignore instructions", exfil patterns
- **Prompts Caching**: Anthropic feature reducing input cost ~75% by caching system prompt + last 3 messages

## 8. Architectural Patterns

1. **Pluggable Engine Pattern** (`ContextEngine`, `MemoryProvider`)
   - Abstract base class defines lifecycle (init, session_start, compress, sync, shutdown)
   - Concrete implementations (ContextCompressor, BuiltinMemoryProvider, external plugins) swap transparently
   - **Rationale**: Enables future context engines (external DAG-based LCM, vector DB retrieval) without modifying core run_agent.py

2. **Provider Fallback Chain** (`auxiliary_client.py`)
   - Ordered resolution: OpenRouter → Nous Portal → Codex → Anthropic → direct API keys
   - Each provider tested for credentials/availability; first working one selected
   - On 402 (billing), automatically retry next in chain
   - **Rationale**: Graceful degradation when primary auxiliary provider runs out of credits; no user intervention needed

3. **Error Classification Pipeline** (`error_classifier.py`)
   - Priority-ordered matchers (provider-specific → HTTP status → message patterns → transport heuristics)
   - Maps each error class to recovery action (retry, rotate, fallback, compress, abort)
   - **Rationale**: Centralized, deterministic error handling; replaces scattered inline string matching across codebase

4. **Single-External-Provider Limit** (`memory_manager.py`)
   - Built-in provider always active; at most one external provider allowed
   - Prevents tool schema bloat, conflicting backends, user confusion
   - **Rationale**: Simplifies mental model; avoids ambiguity about which backend "owns" a piece of memory

5. **Lazy Subdirectory Discovery** (`subdirectory_hints.py`)
   - Tool results checked for new directories; hints loaded on first access
   - Preserves prompt caching (no system prompt edits per tool call)
   - **Rationale**: Agent gains context-sensitive guidance as it navigates without cache invalidation

6. **Iterative Summary Pattern** (`context_compressor.py`)
   - Previous summary preserved; new turns incorporated incrementally
   - Prevents information loss across multiple compressions
   - **Rationale**: On very long conversations with repeated compressions, preserves facts that might be discarded in fresh summarization

7. **Credential Pool Abstraction** (`credential_pool.py`)
   - Multiple keys per provider; round-robin/least-used selection
   - Tracks exhaustion status, error codes, reset times
   - **Rationale**: Distributes load; allows rotating creds when one hits rate limit or quota

8. **Jittered Backoff with Process-Level Uniqueness** (`retry_utils.py`)
   - Uses time.time_ns() XOR'd with counter + random seed
   - Even on coarse clocks, decorrelates concurrent retries across sessions
   - **Rationale**: Prevents thundering herd (all sessions retrying at same instant) on rate-limited provider

## 9. Algorithms & Mechanisms

### A. Context Compression with Iterative Summary Updates

**Mechanism**: When conversation grows beyond threshold tokens, ContextCompressor summarizes middle turns with structured LLM prompt, iteratively updating previous summary on subsequent compressions.

**Steps**:
1. **Prune tool results**: Walk backward from message tail, accumulate token counts. Replace old tool results (>200 chars) with placeholder. Protects recent messages by token budget.
2. **Compute summary budget**: `budget = max(2000, min(0.20 * compressed_content_tokens, 12000))` — scales with input size but capped at 12K tokens.
3. **Serialize turns for summarizer**: Truncate each message (6K chars max), keeping head + tail. Include tool call arguments and results.
4. **Generate or update summary**: First time: summarize from scratch. Subsequent times: update previous summary, preserving info, moving items from "In Progress" → "Done", answered questions → "Resolved Questions".
5. **Merge into tail**: Insert summary message at compression point; tail messages follow (most recent ~20K tokens uncompressed).

**Why this works**: Lossy; sacrifices full accuracy but preserves actionable facts (file paths, decisions, error messages, pending work). Iterative updates prevent cascading information loss.

### B. Error Classification & Recovery Priority Pipeline

**Mechanism**: Exception flows through priority matchers; each stage refines classification. Recovery action determined deterministically by `ClassifiedError` fields.

**Pipeline**:
1. **Transport errors** (ConnectionError, Timeout, ServerDisconnected): Set `reason=timeout`, `retryable=true`, `should_compress=false` (not context issue)
2. **HTTP status codes**:
   - 401/403: `auth` or `auth_permanent` (depends on prior refresh attempts)
   - 402/429 + billing patterns: `billing`, `should_rotate_credential=true`
   - 429 + transient patterns ("try again", "retry after"): `rate_limit`, `should_rotate_credential=true`
   - 503/529: `overloaded`, `retryable=true` (no credential rotation)
   - 400: `format_error` (may abort after strip + retry)
   - 413/context patterns: `context_overflow`, `should_compress=true`
3. **Message pattern matching**: If status missing, check body for billing/rate-limit/auth/context keywords
4. **Server disconnect + large session**: If disconnected + session > 80% of context, infer context_overflow
5. **Fallback**: Unknown, retryable with backoff

**Why this works**: Prevents retry storms on billing errors; routes context errors to compression instead of wasting retries; handles providers with missing/inconsistent HTTP status codes.

### C. Auxiliary Client Provider Fallback Chain

**Mechanism**: For side tasks (compression, title generation, vision), resolve LLM via priority-ordered chain. On 402, automatically skip to next provider.

**Resolution order (text tasks)**:
1. OpenRouter (cheapest; OPENROUTER_API_KEY)
2. Nous Portal (~/.hermes/auth.json active provider)
3. Custom endpoint (config.yaml base_url + OPENAI_API_KEY)
4. Codex OAuth (Responses API wrapper)
5. Native Anthropic (api.anthropic.com)
6. Direct API-key providers (z.ai, Kimi, MiniMax, etc.)
7. None

**Vision task chain** (reordered for multimodal support):
1. Primary model if supports vision (Claude, Gemini, GPT-5.3, etc.)
2. OpenRouter
3. Nous Portal
4. Codex OAuth
5. Anthropic
6. Custom endpoint (local vision models: Qwen-VL, LLaVA, Pixtral)

**Failure handling**: On HTTP 402, log and retry with next provider. On all failures after chain exhaustion, return error to caller (context compression fails gracefully, title generation silently skipped).

**Why this works**: Reduces external LLM cost (uses cheapest available); handles credit exhaustion transparently; supports user with multiple provider credentials.

### D. Smart Model Routing (Cheap-Model Route Detection)

**Mechanism**: Before API call, check if user message is "simple" (short, no code, no tools needed). If so, route to configured cheap model; else use primary.

**Criteria for "simple" message**:
- Text ≤160 chars
- ≤28 words
- ≤1 newline
- No backticks or code blocks
- No URLs
- No complex keywords (debug, refactor, implement, test, docker, kubernetes, etc.)

**Outcome**: Dict with {model, provider, routing_reason: "simple_turn"} or None (use primary).

**Why this works**: Saves ~80% cost on common messages ("thanks", "what time is it?", "recap"); conservative by design (any sign of complexity keeps primary model).

## 10. State Machines

### Context Compressor Session Lifecycle

```
[INIT] 
  ↓ (on_session_start)
[READY] 
  ↓ (update_from_response with usage)
[TRACKING] 
  ↓ (should_compress checks threshold)
  ├→ [NO_COMPRESS] (tokens < threshold) → loop back to TRACKING
  └→ [COMPRESSING] (tokens >= threshold)
    ↓ (compress() called)
  [COMPRESSED] 
    ↓ (on_session_reset on /new or /reset)
  [INIT]
    ↓ (on_session_end on CLI exit or gateway timeout)
  [CLOSED]
```

### Memory Provider Initialization Sequence

```
[UNREGISTERED]
  ↓ (add_provider called)
[REGISTERED]
  ├→ built-in provider always accepted; _has_external = false
  └→ external provider: if _has_external = false, accept + set flag
      else reject with warning
  ↓ (prefetch_all called)
[PREFETCHING]
  ├→ success: return context text
  └→ failure: log debug, skip provider, merge others' results
  ↓ (sync_all called post-turn)
[SYNCING]
  ├→ success: store in backend
  └→ failure: log debug, non-fatal
```

### Credential Pool Exhaustion & Recovery

```
[OK] (pool entry ready)
  ↓ (API call succeeds)
[IN_USE] (request_count++)
  ├→ success: back to OK
  └→ HTTP 429 or 402: set last_error_code, mark last_error_at
    ↓
  [EXHAUSTED] (cooldown until last_error_at + EXHAUSTED_TTL)
    ↓ (time passes, reset triggered, or provider reset header received)
  [OK]
```

### Error Classification & Recovery State

```
[EXCEPTION]
  ↓ (classify_api_error)
[CLASSIFIED: reason=X, retryable=Y, should_rotate=Z, ...]
  ├→ retryable=false → [ABORT]
  ├→ should_compress=true → [COMPRESS_REQUESTED]
  ├→ should_rotate_credential=true → [ROTATE_CREDENTIAL]
  │   ├→ success: [RETRY_WITH_NEW_CRED]
  │   └→ no alt cred: fall through to next step
  ├→ should_fallback=true → [FALLBACK_REQUESTED]
  ├→ retryable=true → [BACKOFF] 
  │   ↓ (jittered_backoff computed)
  │   [WAIT] → [RETRY]
  └→ [RETRY]
```

## 11. Error/Edge Cases & Fallback Paths

| Edge Case | Detection | Fallback | Code Reference |
|---|---|---|---|
| Context window exceeded | HTTP error contains "context", "token limit", "too many tokens" | Trigger `ContextEngine.compress()` manually or automatically on next turn | `error_classifier.py` line 146-174 (_CONTEXT_OVERFLOW_PATTERNS) |
| Credential exhausted (402 billing) | HTTP 402 or "insufficient credits" message | `CredentialPool.select_next()` rotates to next credential; if none available, fallback provider chain in `auxiliary_client.py` | `credential_pool.py` lines 192-196, `error_classifier.py` line 89-100 (_BILLING_PATTERNS) |
| Rate limit (429) | HTTP 429 or "too many requests" message | `jittered_backoff()` computes delay with counter-based jitter; retry same credential after cooldown or rotate if repeated | `retry_utils.py` line 41, `rate_limit_tracker.py` lines 31-76 |
| Timeout (ReadTimeout, ConnectTimeout) | Transport layer exception in _TRANSPORT_ERROR_TYPES | Rebuild client (new connection pool) and retry with backoff; if repeated, fallback to different provider | `error_classifier.py` lines 207-217 |
| Model not found | HTTP 404 or "model not found" in message | Switch to fallback model via `model_metadata.py` context probe (step down from 128K → 64K → 32K) or user-configured fallback | `error_classifier.py` line 177-186 |
| Anthropic thinking block signature invalid | Error contains "thinking" + "signature" | Retry without thinking budget; reduce `THINKING_BUDGET` or disable thinking on next model switch | `error_classifier.py` lines 201-204 |
| Anthropic long-context tier gate | 413 or "extra usage" error | Truncate context or fallback to model without tier gate; gate typically applies after 1M tokens used | `anthropic_adapter.py` (dynamic tier checks) |
| Memory provider fails during prefetch | Exception in `provider.prefetch()` | Log debug (non-fatal), continue with other providers; merged result may be partial | `memory_manager.py` lines 173-183 |
| Subdirectory hint file malformed YAML | Exception in `yaml.load()` | Fallback to simple key:value parsing; if both fail, skip hint injection | `skill_utils.py` line 79 |
| Tool output too large for context | Content > CONTENT_MAX | Truncate with head + "...[truncated]..." + tail in `_serialize_for_summary()`; full output already pruned by `_prune_old_tool_results()` | `context_compressor.py` lines 261-315 |
| Auxiliary LLM fails (compression summary fails) | Exception from `call_llm(task="compression")` | Enter cooldown (600s); drop middle turns without summary rather than retry immediately; accept slightly lower context budget | `context_compressor.py` lines 57, 337-342 |
| API key redaction regex misses secret | New token format not in _PREFIX_PATTERNS | Falls through to ENV patterns or JSON patterns; if still missed, logged verbatim (potential security gap) | `redact.py` lines 21-57 |
| Prompt cache miss on Anthropic (context changed) | Cache not hit; full tokens charged | Graceful degradation — still works, just higher cost; next turn cache hit resumes savings | `prompt_caching.py` (no error path; transparent) |
| Provider doesn't return x-ratelimit headers | Header parsing finds no "x-ratelimit-*" keys | `parse_rate_limit_headers()` returns None; `RateLimitState` not captured for that response | `rate_limit_tracker.py` lines 92-129 |

## 12. Design Decisions Visible in Code

1. **Iterative Summary Updates Instead of Fresh Summarization** (`context_compressor.py` lines 406-420)
   - **Decision**: Store `_previous_summary` and update on each compression (merge new turns, move "In Progress" → "Done")
   - **Visible in**: `if self._previous_summary: ... Update the summary ...` branch
   - **Rationale**: On long conversations with multiple compressions, preserves facts that might otherwise be forgotten; creates a durable handoff artifact for subagents or session resumption

2. **Credential Pool Single-External-Provider Limit** (`memory_manager.py` lines 94-107)
   - **Decision**: Reject second external memory provider with warning; only built-in + one external allowed
   - **Visible in**: `if self._has_external: logger.warning("Rejected...")` + return early
   - **Rationale**: Prevents tool schema bloat, conflicting backends, confusing users about which store "owns" memory; forces explicit choice via config

3. **Jittered Backoff via Process Counter XOR Random** (`retry_utils.py` lines 41-57)
   - **Decision**: Seed random with `(time.time_ns() ^ (tick * 0x9E3779B9)) & 0xFFFFFFFF` instead of just time
   - **Visible in**: Global `_jitter_counter` with lock, unique seed formula
   - **Rationale**: Even on coarse clocks or highly correlated timing across sessions, decorrelates concurrent retries; prevents thundering herd

4. **Anthropic Cache Control Marker Count: 4 Maximum** (`prompt_caching.py` lines 61-70)
   - **Decision**: Place cache control on system + last 3 non-system messages (exactly 4 breakpoints, Anthropic's limit)
   - **Visible in**: `remaining = 4 - breakpoints_used; for idx in non_sys[-remaining:]`
   - **Rationale**: 4 is Anthropic's maximum; system cache ~stable, last 3 messages cover recent context for best hit rate; balances cache efficiency vs staleness

5. **Provider Fallback Chain Hardcoded Ordering** (`auxiliary_client.py` lines 7-24, 57-73)
   - **Decision**: OpenRouter → Nous Portal → Codex → Anthropic for text; vision chain reordered
   - **Visible in**: Sequential provider resolution with try/except fallthrough
   - **Rationale**: OpenRouter cheapest & most flexible; Nous Portal available to existing users; Codex OAuth as fallback for GitHub users; Anthropic most reliable but priciest; ensures deterministic behavior

---

# agent/ — Deep Analysis

## 1. Existence Rationale

The `agent/` module exists as a separate codebase layer because the original `run_agent.py` had grown to 3,600 lines, mixing orchestration logic with utility functions. Extracting pure, self-contained utilities enables:

- **Testing in isolation**: Compression, error classification, credential management can be unit-tested without spinning up a full agent
- **Plugin compatibility**: Abstract base classes (`ContextEngine`, `MemoryProvider`) allow third parties to swap implementations (external DAG compressors, Honcho/Mem0 backends) without modifying core agent logic
- **Reusability across platforms**: Same utilities (prompt_builder, error_classifier, redact) work in CLI, gateway, cron jobs, and future frontends
- **Cognitive load reduction**: run_agent.py focuses on the orchestration loop; agent/ utilities are consulted as needed
- **Maintenance**: When Anthropic releases a new caching strategy or error signature, updates localize to `prompt_caching.py` or `error_classifier.py`, not scattered across run_agent.py

## 2. Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|----------|-------------|------------------------|--------------------|
| **Context compression strategy** | Lossy LLM summarization with iterative updates | (A) Retrieve-augmented generation (vector DB); (B) Sliding window (drop oldest N turns); (C) Lossless DAG construction | Lossy is simplest & works well for typical agent workflows; RAG requires external infra; sliding window loses decision context; DAG is complex to implement and maintain. Iterative updates prevent cascading loss on repeated compressions. |
| **Single external memory provider limit** | Only one non-builtin provider at a time | (A) Multiple simultaneous providers (union schema); (B) Switchable per-turn provider | Prevents tool schema bloat (20+ memory tools is confusing); avoids ambiguous ownership (which provider "owns" a fact?); forces explicit config choice. Single provider is mental model winner. |
| **Error classification priority pipeline** | Status code → message patterns → transport heuristics | (A) Machine-learned error classifier; (B) Provider-specific error maps (manual per provider); (C) Simple regex-based catch-all | Deterministic and debuggable; no ML training overhead; centralized logic vs scattered per-provider mapping; provider-specific patterns folded in as low-priority fallback. |
| **Jittered backoff with counter XOR seed** | `time.time_ns() ^ (counter * 0x9E3779B9)` | (A) Pure random.Random(); (B) Fixed exponential backoff; (C) Adaptive based on rate-limit headers | Pure random can collide on coarse clocks; fixed backoff causes herd; adaptive requires parsing headers first (slower). Counter-based seed ensures diversity even if multiple sessions start simultaneously. Magic constant 0x9E3779B9 is FNV offset basis (well-distributed). |
| **Auxiliary client fallback chain ordering** | OpenRouter → Nous Portal → Codex → Anthropic → direct keys | (A) Reverse (Anthropic first); (B) User-configurable priority; (C) Random selection | OpenRouter has most models, lowest latency setup; Nous Portal for existing users; Codex for GitHub Copilot users; Anthropic most reliable last resort; direct keys as final option. Nous Research's own backend (Nous Portal) in 2nd position reflects product affinity. User-configurable would add complexity. |
| **Prompt caching breakpoint count: 4** | System + last 3 non-system messages | (A) All messages cached; (B) System only; (C) Last N dynamic | Anthropic enforces 4-max; system ~always stable (highest cache hit probability); last 3 cover recent context without churn. Balances effectiveness vs staleness. |
| **Subdirectory hints lazy-loaded, not in system prompt** | Check tool results for new dirs → inject via tool result | (A) Scan filesystem upfront (startup latency); (B) Batch inject all hints in system prompt | Lazy preserves prompt caching (no system prompt edits per turn); upfront scan adds startup delay; tool result injection is transparent to model. Tradeoff: first access to new dir has latency, but subsequent accesses hit memory. |

## 3. Algorithm Deep-Dives

### A. Context Compression: Lossy Summarization with Iterative Updates

**Step-by-step execution:**

1. **Trigger check**: `ContextCompressor.should_compress()` compares `last_prompt_tokens` vs `threshold_tokens` (e.g., 750k tokens vs 75% of 1M = 750k threshold met).

2. **Tool pruning (cheap pre-pass)**:
   ```
   For i in range(len(messages) - 1, -1, -1):  # backward
     if messages[i].role == "tool" and len(content) > 200:
       if not in protected tail (by token budget):
         replace content with "[Old tool output cleared]"
   ```
   Protects recent messages by token budget (`protect_tail_tokens`), not fixed count. Example: on 1M context model, protect last ~200k tokens (recent messages stay full-text).

3. **Head/tail protection boundary**:
   - Head: first `protect_first_n` messages (system + 2 user/assistant exchanges) never compressed
   - Tail: accumulate tokens backward from end; when accumulated exceeds `tail_token_budget` (e.g., 20K tokens), mark boundary
   - Middle: between head and tail — summarization target

4. **Serialize middle turns for summarizer**:
   ```python
   for msg in turns_to_summarize:
     if msg.role == "tool":
       text += f"[TOOL RESULT {id}]: {msg.content[:6000]}..."
     elif msg.role == "assistant":
       text += f"[ASSISTANT]: {msg.content[:6000]}..."
       # Include tool call names + args (truncated)
   ```
   Preserves enough detail for summarizer to extract file paths, commands, decisions.

5. **Compute summary budget**:
   ```python
   content_tokens = estimate_messages_tokens_rough(turns_to_summarize)
   budget = max(2000, min(content_tokens * 0.20, 12000))
   # Example: 50k tokens of content → 10k token summary budget
   ```

6. **Determine prompt path**:
   - **If `_previous_summary` exists**: Use iterative update prompt
     ```
     "You are updating a context compaction summary. A previous compaction produced:
      {self._previous_summary}
      
      New turns:
      {content_to_summarize}
      
      Update the summary. PRESERVE all relevant info. ADD new progress. Move items from In Progress → Done."
     ```
   - **Else**: Use fresh summarization prompt
     ```
     "Create a structured handoff summary for a different assistant continuing this conversation.
      
      Turns to summarize:
      {content_to_summarize}
      
      Use this structure: ## Goal, ## Progress, ## Decisions, ## Resolved Questions, ## Pending Asks, ..."
     ```

7. **Call auxiliary LLM**:
   ```python
   response = call_llm(
       task="compression",
       main_runtime={model, provider, base_url, api_key},
       messages=[{role: "user", content: prompt}],
       max_tokens=summary_budget,
       temperature=0.3,
   )
   ```
   Falls back through OpenRouter → Nous Portal → Codex → Anthropic chain if primary exhausted.

8. **Construct output message list**:
   ```python
   output = []
   output.extend(head_messages)  # system + opening
   output.append({role: "assistant", content: f"{SUMMARY_PREFIX}\n\n{summary}"})
   output.extend(tail_messages)  # recent uncompressed
   return output
   ```
   Store summary in `_previous_summary` for next compression.

9. **Failure recovery**: If LLM call fails, enter cooldown (600s), drop middle turns without summary; accept slightly reduced budget rather than crash.

**Trace example** (simplified):
- Initial: 1200 messages, 850k tokens (above 750k threshold)
- Protect first 3 (system + 2 exchanges): 1.2k tokens
- Protect last 20k tokens (recent ~80 messages): 20k tokens
- Middle to compress: messages 3–1120, ~800k tokens
- Summary budget: `min(0.20 * 800k, 12k) = 12k tokens`
- Summarizer preamble (100 tokens) + content (800k trunc'd to ~1M chars / 4 = 250k chars ≈ 62.5k chars → 15.6k tokens) = exceeds budget
- Truncate to CONTENT_HEAD + CONTENT_TAIL strategy: keep first 4k, last 1.5k chars per message
- Summarizer output: ~10k tokens (within budget)
- Output list: 3 head + 1 summary + 80 tail = 84 messages, ~30k tokens total
- Compression ratio: 1200 → 84 messages (7% of original); 850k → 30k tokens (3.5%)

### B. Error Classification Priority Pipeline

**Execution flow** (from `classify_api_error`):

1. **Extract error components**:
   ```python
   status_code = _extract_status_code(error)  # HTTP status or None
   error_type = type(error).__name__         # e.g. "APIStatusError"
   body = _extract_error_body(error)         # parsed JSON or None
   error_code = _extract_error_code(body)    # "invalid_request_body" etc.
   
   _raw_msg = str(error).lower()
   _body_msg = body.get("error", {}).get("message", "").lower()
   # Also check OpenRouter wrapping: body.error.metadata.raw → inner error
   ```

2. **Stage 1: Provider-specific pattern matching** (highest priority):
   ```python
   if provider == "anthropic":
     if "thinking" in error_msg and "signature" in error_msg:
       return ClassifiedError(reason=FailoverReason.thinking_signature, ...)
     if "extra usage tier" in error_msg or "long context" in error_msg:
       return ClassifiedError(reason=FailoverReason.long_context_tier, ...)
   ```

3. **Stage 2: HTTP status code**:
   ```python
   if status_code == 401:
     return ClassifiedError(reason=FailoverReason.auth, retryable=True, should_rotate_credential=True, ...)
   elif status_code == 402:
     return ClassifiedError(reason=FailoverReason.billing, should_rotate_credential=True, ...)
   elif status_code == 413:
     return ClassifiedError(reason=FailoverReason.payload_too_large, should_compress=True, ...)
   elif status_code == 429:
     # Refinement: check if "try again" pattern suggests transient
     if any(p in _body_msg for p in ["try again", "retry after"]):
       return ClassifiedError(reason=FailoverReason.rate_limit, should_rotate_credential=True, ...)
   elif status_code == 503 or 529:
     return ClassifiedError(reason=FailoverReason.overloaded, retryable=True, ...)
   elif status_code == 404 or "not found" in _body_msg:
     return ClassifiedError(reason=FailoverReason.model_not_found, should_fallback=True, ...)
   ```

4. **Stage 3: Message pattern matching** (if status code absent or ambiguous):
   ```python
   # Billing check
   if any(p in _body_msg for p in _BILLING_PATTERNS):  # "insufficient credits", etc.
     return ClassifiedError(reason=FailoverReason.billing, ...)
   
   # Rate limit vs usage limit disambiguation
   if any(p in _body_msg for p in _USAGE_LIMIT_PATTERNS):  # "quota", "limit exceeded"
     # Is it transient (rate) or permanent (billing)?
     if any(p in _body_msg for p in _USAGE_LIMIT_TRANSIENT_SIGNALS):  # "try again", "retry"
       return ClassifiedError(reason=FailoverReason.rate_limit, ...)
     else:
       # Could be billing; check for billing signals
       if any(p in _body_msg for p in _BILLING_PATTERNS):
         return ClassifiedError(reason=FailoverReason.billing, ...)
   
   # Context overflow
   if any(p in _body_msg for p in _CONTEXT_OVERFLOW_PATTERNS):  # "context length", "too many tokens"
     return ClassifiedError(reason=FailoverReason.context_overflow, should_compress=True, ...)
   
   # Auth
   if any(p in _body_msg for p in _AUTH_PATTERNS):  # "invalid api key", "unauthorized"
     return ClassifiedError(reason=FailoverReason.auth, ...)
   ```

5. **Stage 4: Transport error heuristics**:
   ```python
   if error_type in _TRANSPORT_ERROR_TYPES:  # ReadTimeout, ConnectError, etc.
     if "server disconnected" in _raw_msg or any(p in _raw_msg for p in _SERVER_DISCONNECT_PATTERNS):
       # Could be context overflow on disconnect + large session
       if approx_tokens > context_length * 0.8:
         return ClassifiedError(reason=FailoverReason.context_overflow, ...)
       else:
         return ClassifiedError(reason=FailoverReason.timeout, retryable=True, ...)
     return ClassifiedError(reason=FailoverReason.timeout, retryable=True, ...)
   ```

6. **Stage 5: Fallback**:
   ```python
   return ClassifiedError(reason=FailoverReason.unknown, retryable=True, ...)
   ```

**Trace example**: Anthropic returns error
```
APIStatusError(status_code=400, message="Invalid thinking_budget_tokens value", body={"error": {"type": "invalid_request_error", ...}})
```
- Extract: status=400, type="APIStatusError", msg="invalid thinking_budget..."
- Stage 1 (provider-specific): provider="anthropic" → check patterns → "thinking" in msg? YES → "signature" in msg? NO → skip thinking_signature
- Stage 2 (HTTP 400): → `format_error`, retryable=True, but could be more specific
- Stage 3 (patterns): "invalid_request_error" → check _FORMAT_ERROR_PATTERNS → match "invalid" → already classified as format_error
- Result: `ClassifiedError(reason=format_error, retryable=True, should_rotate_credential=False, should_fallback=False)` → run_agent.py will retry after stripping thinking or reducing budget

### C. Jittered Backoff with Counter-Based Decorrelation

**Function signature**:
```python
def jittered_backoff(
    attempt: int,
    base_delay: float = 5.0,
    max_delay: float = 120.0,
    jitter_ratio: float = 0.5,
) -> float:
```

**Execution**:

1. **Global counter increment** (with lock):
   ```python
   global _jitter_counter
   with _jitter_lock:
       _jitter_counter += 1
       tick = _jitter_counter
   ```
   Ensures each retry in the process has a unique tick; prevents collisions even on coarse clocks.

2. **Exponential delay**:
   ```python
   exponent = max(0, attempt - 1)
   if exponent >= 63 or base_delay <= 0:
       delay = max_delay  # Floor at max to prevent overflow
   else:
       delay = min(base_delay * (2 ** exponent), max_delay)
   ```
   Attempt 1: `delay = min(5 * 2^0, 120) = 5s`
   Attempt 2: `delay = min(5 * 2^1, 120) = 10s`
   Attempt 3: `delay = min(5 * 2^2, 120) = 20s`
   Attempt 4: `delay = min(5 * 2^3, 120) = 40s`
   Attempt 5: `delay = min(5 * 2^4, 120) = 80s`
   Attempt 6: `delay = min(5 * 2^5, 120) = 120s` (capped)

3. **Jitter seed with XOR**:
   ```python
   seed = (time.time_ns() ^ (tick * 0x9E3779B9)) & 0xFFFFFFFF
   rng = random.Random(seed)
   jitter = rng.uniform(0, jitter_ratio * delay)
   ```
   - `time.time_ns()`: nanosecond precision (if available)
   - `tick * 0x9E3779B9`: Each increment of tick produces very different output (FNV hash constant ensures avalanche effect)
   - XOR combines both: if two sessions start at same time but different ticks, seeds differ
   - Example: Session A at tick=100, time=1000000, → seed = (1000000 ^ (100 * 2654435769)) & MASK = unique seed A
   - Example: Session B at tick=101, time=1000000, → seed = (1000000 ^ (101 * 2654435769)) & MASK = very different seed B
   - Even if time is identical, ticks differ → seeds differ → jitter differs

4. **Return total delay**:
   ```python
   return delay + jitter
   ```
   Example: attempt=2, delay=10, jitter_ratio=0.5 → jitter ∈ [0, 5] → total ∈ [10, 15] seconds

**Why it works**: On coarse clocks (millisecond precision), multiple sessions hitting rate limit simultaneously would all compute similar delays. Counter XOR ensures each session gets unique seed; even without precise timing, decorrelation is high. Exponential backoff prevents immediate retry spam; max_delay prevents runaway.

---

## 4. Error Philosophy

**Core principle**: Errors are **classified, not assumed**. Recovery action is **determined deterministically**, not guessed.

**Three failure modes**:

1. **Retryable transient failures** (HTTP 429, 503, Timeout)
   - Example: `jittered_backoff(attempt=N)` → sleep → retry same cred
   - Rationale: These resolve with time; no state change needed
   - Limit: Max 3-5 retries (per run_agent.py caller logic) before giving up

2. **Provider/credential failures** (HTTP 402 billing, 401 auth expired)
   - Example: mark credential exhausted, rotate to next in pool
   - If no alternatives exist in pool: try fallback provider via `auxiliary_client` chain (for side tasks)
   - Rationale: User has multiple creds; distribute load / recover from credit exhaustion
   - Limit: Exhaust all creds before aborting

3. **Context-level failures** (HTTP 413 or "context too large" pattern)
   - Example: `should_compress=True` in ClassifiedError → manual trigger compression
   - Don't retry same message; shrink context, then retry
   - Rationale: The request itself is valid but too large; solve by reducing size
   - Limit: May compress 2-3 times before giving up (prevents compress loop)

**Non-failures** (graceful degradation):
- Title generation fails → silently skip (cosmetic feature)
- Subdirectory hint loading fails → continue without hints (not critical)
- Memory provider prefetch fails → use other providers; no error raised
- Rate limit headers missing → track-less (no visibility, but doesn't break)

**Visibility**:
- Errors are logged at appropriate levels: `logger.debug()` for transient, `logger.warning()` for state changes (rotate credential, enter cooldown), `logger.error()` rarely (usually fatal)
- Redaction applies automatically to logs via `RedactionFormatter` (no secrets leak)

**Why this approach**:
- Deterministic: Same error always triggers same recovery (no randomness)
- Debuggable: Error classifications are explicit enums, patterns are documented
- Safe: Defaults conservative (retry rather than abort unless clear reason to abort)
- User-friendly: Recovers from common transient issues without user intervention

## 5. Performance Characteristics

| Subsystem | What's Optimized | Trade-offs |
|-----------|------------------|-----------|
| **Context Compression** | Tail protection by token budget (not message count); iterative summary updates preserve info across multiple compressions | Lossy (discards middle detail); summary LLM call adds latency (~2-5s for 50k token input); if compression fails, accept worse budget |
| **Auxiliary Client** | Fallback chain reuses credentials (no OAuth refresh per call); Nous Portal pool selection avoids re-resolving auth; caches resolved client | If primary provider exhausted, chain fallthrough has latency (try OpenRouter, fail on 402, try Nous, etc.); no async pre-warming |
| **Prompt Caching** | System prompt pinned (stable across all turns); last 3 non-system messages cached → ~75% cost reduction on subsequent turns | Cache misses silently (no error); if context changes significantly, cache invalidated; Anthropic-only (other providers don't support) |
| **Error Classification** | Priority pipeline is O(n) string matching (n = # patterns); but short-circuits on first match (status 401 = auth, done) | If status code absent, must scan all message patterns (worst case ~20 pattern checks); no caching of prior classifications |
| **Rate Limit Tracking** | Parse headers once per response; store state in dataclasses; no DB writes | If provider doesn't emit headers, zero visibility; state per session (not persisted across sessions) |
| **Credential Pool** | O(1) lookup by provider; round-robin selection via index (lightweight) | Full pool load from disk on first call; no pooling of loaded pools (fresh read each time) |
| **Subdirectory Hints** | Lazy load on first tool call to new directory; memoize discovered dirs (don't re-scan) | First access to new dir has file I/O latency; regex scanning for hint files is O(# dirs * # filenames) |

**Token estimation**:
- `estimate_messages_tokens_rough()`: ~4 chars/token heuristic (fast, within ±15% for English); provider-specific adjustments (Anthropic Claude messages have higher overhead)
- No actual tokenization (would require provider SDK loading)

**Memory usage**:
- `ContextCompressor._previous_summary` stores last summary in memory (typically <20k tokens = <100KB)
- `MemoryProvider` prefetch cached between turns (user-specific, typically <10KB)
- No unbounded growth (summaries replace old content, prefetch is fresh each turn)

## 6. Evolution Clues

**Layers of evolution** visible in code:

1. **v0 → v1: Modularization**
   - Evidence: `agent/__init__.py` states "extracted modules from run_agent.py" and module docstrings reference when they were split out
   - Change: Was all in run_agent.py; now pluggable + testable

2. **v1 → v2: Summarization improvements** (context_compressor.py comments lines 7-17)
   - Evidence: `SUMMARY_PREFIX` references "[CONTEXT COMPACTION — REFERENCE ONLY]" vs legacy `LEGACY_SUMMARY_PREFIX = "[CONTEXT SUMMARY]:"`
   - Features added: Structured template (Goal, Progress, Decisions, Resolved/Pending Questions, Files, Remaining Work), iterative updates, "do not respond" preamble
   - Origin: Comments cite "from OpenCode", "from Codex" — learned from sister projects
   - Change: Less lossy; better framing; prevents model from re-answering questions

3. **v1 → v2: Error classification professionalization** (error_classifier.py structure)
   - Evidence: Enum `FailoverReason` (not string-based); priority-ordered pipeline; provider-specific patterns
   - Previous approach: Likely scattered `if "rate limit" in str(error)` checks across codebase
   - Change: Centralized, deterministic, extensible

4. **v2 → v3: Credential pool sophistication** (credential_pool.py)
   - Evidence: `EXHAUSTED_TTL_429_SECONDS`, `last_error_code`, `last_error_at` tracking
   - Features: HTTP 429/402 cool-down, exponential backoff-aware TTL, pool entry states (OK, EXHAUSTED)
   - Previous: Likely rotated on any failure; now respects provider's reset times
   - Change: Fewer unnecessary rotations; respects rate-limit headers when present

5. **v2 → v3: Auxiliary client chain maturation** (auxiliary_client.py hardcoded models)
   - Evidence: `_PROVIDER_MODELS` dict with fallback models per provider (Nous, OpenAI, Anthropic, etc.)
   - Previous: Likely single hardcoded auxiliary model; no provider diversity
   - Change: Supports multi-provider deployments; users with multiple credentials get grace ful fallback

6. **Anthropic-specific additions** (anthropic_adapter.py, error_classifier.py thinking patterns)
   - Evidence: `THINKING_BUDGET`, `ADAPTIVE_EFFORT_MAP`, thinking signature error patterns, long-context tier gate handling
   - Timeline: Claude 4 released thinking; later tier system added; error patterns follow
   - Change: Agent gains access to Anthropic reasoning; handles new failure modes

7. **Prompt caching opportunism** (prompt_caching.py)
   - Evidence: Simple `apply_anthropic_cache_control()` function added (not core to agent)
   - Timing: Anthropic released prompt caching; code added to leverage it
   - Change: Auxiliary LLM calls (compression) benefit from cache hits; cost savings

8. **Security hardening** (prompt_builder._scan_context_content, redact.py)
   - Evidence: Threat patterns in AGENTS.md/CLAUDE.md (_CONTEXT_THREAT_PATTERNS); comprehensive secret regexes
   - Previous: Likely less scrutiny of user-provided context files
   - Change: Blocks prompt injection; redacts secrets from logs (response to security audits or incidents)

9. **Multi-platform broadening** (skill_utils.PLATFORM_MAP, subdirectory_hints)
   - Evidence: Platform conditionals (macos/linux/windows); tool results hooked for hints
   - Previous: Single-platform (likely Linux) or hardcoded paths
   - Change: Supports Windows (WSL), macOS, Linux; CI/CD integration; multi-backend orchestration

---

This completes the comprehensive research report on Hermes Agent's `agent/` module. The module is architecturally elegant: pluggable engines, priority-ordered error classification, graceful degradation across providers, iterative summarization, and security-hardened context handling — all designed to keep a self-improving AI agent productive and cost-effective across long sessions, multiple backends, and diverse failure modes.