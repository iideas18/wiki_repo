Agent completed. agent_id: research-services-utils, agent_type: explore, status: completed, description: Research services & utils, elapsed: 237s, total_turns: 0, duration: 237s

# COMPREHENSIVE RESEARCH REPORT
## Claude Code Source Map - Services & Utils Directories

---

## PART 1: SERVICES DIRECTORY (/src/services/)

### SERVICES DIRECTORY STRUCTURE
```
services/
├── analytics/           (Event logging and analytics sinks)
├── api/                 (API client, session management, logging)
├── autoDream/           (Background memory consolidation)
├── SessionMemory/       (Session notes extraction)
├── teamMemorySync/      (Team memory synchronization)
├── plugins/             (Plugin installation management)
├── tips/                (Tip scheduling and history)
├── oauth/               (OAuth authentication)
├── lsp/                 (Language Server Protocol integration)
├── mcp/                 (Model Context Protocol client)
├── compact/             (Context compaction)
├── tools/               (Tool management)
```

---

## 1. ANALYTICS SERVICE (/src/services/analytics/)

**PURPOSE:**
Analytics service provides a unified event logging pipeline for Claude Code. It routes events to multiple backends (Datadog, first-party event logging) with sampling capabilities and metadata enrichment. The service is designed with no dependencies to avoid import cycles, queuing events until the sink is attached.

**KEY FILES & STRUCTURE:**
- `index.ts` - Public API entry point (zero-dependency)
- `firstPartyEventLogger.ts` - 1P event logging (OpenTelemetry/OTel-based)
- `sink.ts` - Analytics routing logic (Datadog + 1P routing)
- `datadog.ts` - Datadog integration
- `config.ts` - Analytics configuration/gates
- `sinkKillswitch.ts` - Kill switch mechanism for sinks
- `growthbook.ts` - Dynamic config from GrowthBook
- `metadata.ts` - Event metadata enrichment

**KEY CLASSES/FUNCTIONS:**
1. `logEvent(eventName, metadata)` [index.ts:133]
2. `logEventAsync(eventName, metadata)` [index.ts:154]
3. `attachAnalyticsSink(newSink)` [index.ts:95]
4. `stripProtoFields<V>(metadata)` [index.ts:45] - PII filtering
5. `logEventTo1P(eventName, metadata)` [firstPartyEventLogger.ts:216]
6. `initialize1PEventLogging()` [firstPartyEventLogger.ts:312]
7. `reinitialize1PEventLoggingIfConfigChanged()` [firstPartyEventLogger.ts:407]
8. `initializeAnalyticsSink()` [sink.ts:109]
9. `shouldSampleEvent(eventName)` [firstPartyEventLogger.ts:57]
10. `getEventSamplingConfig()` [firstPartyEventLogger.ts:43]
11. `logGrowthBookExperimentTo1P(data)` [firstPartyEventLogger.ts:255]
12. `isSinkKilled(sinkName)` [sinkKillswitch.ts - external]

**REPRESENTATIVE CODE SIGNATURES:**
```typescript
type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = never
type AnalyticsSink = {
  logEvent: (eventName: string, metadata: LogEventMetadata) => void
  logEventAsync: (eventName: string, metadata: LogEventMetadata) => Promise<void>
}
function stripProtoFields<V>(metadata: Record<string, V>): Record<string, V>
export async function initialize1PEventLogging(): Promise<void>
```

**DATA FLOW:**
1. Applications call `logEvent`/`logEventAsync` early in execution
2. Events queue in memory if sink not yet attached (eventQueue array)
3. `initializeAnalyticsSink()` attaches sink during app startup (setupBackend)
4. Queued events drain asynchronously via `queueMicrotask` to avoid blocking
5. Events are sampled based on `tengu_event_sampling_config` (dynamic from GrowthBook)
6. Sampled events routed to: Datadog (with `_PROTO_*` fields stripped), 1P (full payload)
7. 1P events batched by FirstPartyEventLoggingExporter, exported to `/api/event_logging/batch`

**INTERACTIONS:**
- **Depends on:** GrowthBook (dynamic config), Datadog client, OpenTelemetry SDK
- **Called from:** All modules logging analytics events (>100+ call sites)
- **Interactions:** auth.ts, SessionMemory.ts, autoDream.ts, plugins/PluginInstallationManager.ts, hooks.ts

**KEY ALGORITHMS/MECHANISMS:**
- **Event Sampling:** Random sampling based on per-event `sample_rate` config (0-1)
- **PII Protection:** `_PROTO_*` prefix marks values destined for privileged BQ columns only
- **Queue Drain:** Uses `queueMicrotask` to avoid blocking startup path
- **Reinitialize on Config Change:** Flushes old pipeline, swaps to new config at runtime
- **Idempotent Initialization:** `attachAnalyticsSink` is a no-op if sink already attached

---

## 2. AUTO-DREAM SERVICE (/src/services/autoDream/)

**PURPOSE:**
Background memory consolidation service that automatically triggers the /dream prompt as a forked subagent when conditions are met (time elapsed, sessions accumulated). Uses multi-gate filtering to avoid unnecessary processing and prevent concurrent consolidations.

**KEY FILES:**
- `autoDream.ts` - Main consolidation orchestrator
- `config.ts` - Feature flags and thresholds
- `consolidationLock.ts` - File-based locking for coordination
- `consolidationPrompt.ts` - Consolidation prompt builder

**KEY CLASSES/FUNCTIONS:**
1. `initAutoDream()` [autoDream.ts:122]
2. `executeAutoDream(context, appendSystemMessage)` [autoDream.ts:319]
3. `isGateOpen()` [autoDream.ts:95]
4. `getConfig()` [autoDream.ts:73]
5. `makeDreamProgressWatcher(taskId, setAppState)` [autoDream.ts:281]
6. `tryAcquireConsolidationLock()` [consolidationLock.ts - external]
7. `readLastConsolidatedAt()` [consolidationLock.ts - external]
8. `listSessionsTouchedSince(lastAt)` [consolidationLock.ts - external]
9. `rollbackConsolidationLock(priorMtime)` [consolidationLock.ts - external]

**REPRESENTATIVE CODE SIGNATURES:**
```typescript
type AutoDreamConfig = {
  minHours: number
  minSessions: number
}
export async function executeAutoDream(
  context: REPLHookContext,
  appendSystemMessage?: AppendSystemMessageFn
): Promise<void>
```

**DATA FLOW:**
1. `initAutoDream()` called at startup from backgroundHousekeeping
2. `executeAutoDream()` invoked per-turn from stopHooks (after each assistant turn)
3. Multi-gate checks (cheapest first):
   - **Time gate:** hours since lastConsolidatedAt >= minHours (default 24)
   - **Session gate:** count of transcripts with mtime > lastConsolidatedAt >= minSessions (default 5)
   - **Lock gate:** acquire consolidation lock (no other process mid-consolidation)
4. Build consolidation prompt with session hints and read-only tool restrictions
5. `runForkedAgent` with restricted tool permissions (read-only bash)
6. Progress watcher extracts text blocks and file paths touched
7. On completion: register dream task, emit analytics, append to main transcript
8. On failure: rollback lock for retry, emit failed event

**INTERACTIONS:**
- **Uses:** runForkedAgent, forkedAgent.ts, extractMemories (createAutoMemCanUseTool)
- **Emits:** logEvent (analytics: `tengu_auto_dream_fired`, `completed`, `failed`)
- **Depends on:** GrowthBook config (`tengu_onyx_plover`), lock file system
- **Called from:** SessionMemory service (via stopHooks), backgroundHousekeeping

**KEY ALGORITHMS/MECHANISMS:**
- **Scan Throttle:** When time-gate passes but session-gate doesn't, prevents repeated lock file checks (SESSION_SCAN_INTERVAL_MS = 10 minutes)
- **Multi-gate Filtering:** Cheap checks first (time 1 stat, session scan, lock acquire)
- **Closure-scoped State:** lastSessionScanAt stored in closure for persistence across turns
- **Lock-based Coordination:** File mtime tracks last consolidation, prevents overlaps via kernel-level file locking
- **Force Mode:** Bypasses all gates except lock (for testing), still scans sessions for prompt hints

---

## 3. SESSION MEMORY SERVICE (/src/services/SessionMemory/)

**PURPOSE:**
Automatically maintains a markdown file with notes about the current conversation. Runs periodically in the background via forked subagent to extract key info without interrupting main conversation flow. Triggers based on token count and tool call thresholds.

**KEY FILES:**
- `sessionMemory.ts` - Main extraction orchestrator and hooks
- `sessionMemoryUtils.ts` - State tracking and config management
- `prompts.ts` - Memory update prompt builder

**KEY CLASSES/FUNCTIONS:**
1. `initSessionMemory()` [sessionMemory.ts:357]
2. `shouldExtractMemory(messages)` [sessionMemory.ts:134]
3. `manuallyExtractSessionMemory(messages, context)` [sessionMemory.ts:387]
4. `createMemoryFileCanUseTool(memoryPath)` [sessionMemory.ts:460]
5. `extractSessionMemory(context)` [sessionMemory.ts:272]
6. `setupSessionMemoryFile(toolUseContext)` [sessionMemory.ts:183]
7. `isSessionMemoryGateEnabled()` [sessionMemory.ts:80]
8. `getSessionMemoryRemoteConfig()` [sessionMemory.ts:88]

**REPRESENTATIVE CODE SIGNATURES:**
```typescript
export function shouldExtractMemory(messages: Message[]): boolean

async function extractSessionMemory(context: REPLHookContext): Promise<void>

export async function manuallyExtractSessionMemory(
  messages: Message[],
  toolUseContext: ToolUseContext
): Promise<ManualExtractionResult>
```

**DATA FLOW:**
1. `initSessionMemory()` registers post-sampling hook
2. `extractSessionMemory` hook runs after each turn (via registerPostSamplingHook)
3. Gate check: `isSessionMemoryGateEnabled()` (cached, non-blocking)
4. `shouldExtractMemory()` evaluates thresholds:
   - **Init threshold:** tokenCountWithEstimation >= minimumMessageTokensToInit
   - **Update threshold:** token growth since last extraction >= minimumTokensBetweenUpdate
   - **Tool calls threshold:** countToolCallsSince >= toolCallsBetweenUpdates
   - **Safe point:** no tool calls in last assistant turn (avoids tool_result orphans)
5. `setupSessionMemoryFile()` creates/reads memory file with template
6. `buildSessionMemoryUpdatePrompt()` generates extraction prompt with current memory
7. `runForkedAgent` with memory file edit restrictions (FILE_EDIT_TOOL_NAME only)
8. Log analytics: `tengu_session_memory_extraction` with token usage
9. `updateLastSummarizedMessageIdIfSafe()` for next threshold tracking

**INTERACTIONS:**
- **Uses:** FileReadTool, forkedAgent (runForkedAgent), messages utilities
- **Emits:** logEvent (analytics: `tengu_session_memory_extraction`, `gate_disabled`)
- **Depends on:** GrowthBook (tengu_session_memory gate), auto-compact enablement
- **Called from:** registerPostSamplingHook in stopHooks
- **Interacts with:** SessionMemoryUtils state, config.ts

**KEY ALGORITHMS/MECHANISMS:**
- **Dual-threshold Triggers:** Extraction requires BOTH token growth AND (tool calls OR no-tool-calls-in-last-turn) for safe extraction points
- **Memoized Config Init:** initSessionMemoryConfigIfNeeded() ensures single init per session
- **Token-based Tracking:** Uses tokenCountWithEstimation for consistent metrics (same as autocompact)
- **Cached Gate Checks:** Uses getFeatureValue_CACHED_MAY_BE_STALE for non-blocking checks
- **File Dedup:** Drops cached FileReadTool entry before read to get fresh content

---

## 4. TEAM MEMORY SYNC SERVICE (/src/services/teamMemorySync/)

**PURPOSE:**
Manages team-wide memory synchronization with security scanning for secrets and credentials. Includes watcher for file changes and validation of team memory integrity.

**KEY FILES:**
- `index.ts` - Main sync orchestrator
- `watcher.ts` - File system watcher for changes
- `secretScanner.ts` - Secret detection and scanning
- `teamMemSecretGuard.ts` - Security validation layer
- `types.ts` - Type definitions

**KEY CLASSES/FUNCTIONS:**
1. File watching mechanism for team memory changes
2. Secret scanning on file updates
3. Guard validation for PII/credentials
4. Sync orchestration with error handling and rollback

**KEY ALGORITHMS/MECHANISMS:**
- File system watching with debouncing
- Regex-based secret pattern detection
- Validation before sync operations
- Error handling and logging with rollback on failure

---

## 5. PLUGINS SERVICE (/src/services/plugins/)

**PURPOSE:**
Manages background plugin and marketplace installations without blocking startup. Handles marketplace reconciliation, auto-refresh on new installations, and progress tracking via AppState updates.

**KEY FILES:**
- `PluginInstallationManager.ts` - Main installation orchestrator
- `pluginOperations.ts` - Plugin operations
- `pluginCliCommands.ts` - CLI command integration

**KEY CLASSES/FUNCTIONS:**
1. `performBackgroundPluginInstallations(setAppState)` [PluginInstallationManager.ts:60]
2. `updateMarketplaceStatus(setAppState, name, status, error)` [PluginInstallationManager.ts:30]
3. `reconcileMarketplaces({onProgress})` [external - pluginReconciler]
4. `refreshActivePlugins(setAppState)` [external - pluginRefresh]
5. `diffMarketplaces(declared, materialized)` [external - pluginReconciler]

**REPRESENTATIVE CODE SIGNATURE:**
```typescript
export async function performBackgroundPluginInstallations(
  setAppState: SetAppState
): Promise<void>
```

**DATA FLOW:**
1. `performBackgroundPluginInstallations()` called at startup
2. `getDeclaredMarketplaces()` and `loadKnownMarketplacesConfig()` fetch configs
3. `diffMarketplaces()` computes diff (missing, sourceChanged, etc.)
4. Initialize AppState with pending status for each marketplace
5. `reconcileMarketplaces({onProgress})` performs installation:
   - Emits 'installing', 'installed', 'failed' events
   - `updateMarketplaceStatus()` syncs to AppState on each event
6. Log metrics: installed_count, updated_count, failed_count, up_to_date_count
7. If new installs: `refreshActivePlugins()` clears caches, reloads, bumps reconnectKey
8. If updates only: Set needsRefresh flag for user manual `/reload-plugins`
9. Catch and fallback: If auto-refresh fails, set needsRefresh and emit logError

**INTERACTIONS:**
- **Uses:** reconcileMarketplaces, refreshActivePlugins, clear cache functions
- **Emits:** logEvent (tengu_marketplace_background_install), logForDebugging
- **Depends on:** Plugin infrastructure (marketplace config, loader)
- **Called from:** Background housekeeping during startup

**KEY ALGORITHMS/MECHANISMS:**
- **Diff-based Reconciliation:** Only installs missing or changed marketplaces
- **Progress Callback Pattern:** onProgress events map to AppState UI updates
- **Two-level Fallback:** Auto-refresh with manual reload fallback
- **Cache Clearing:** Ensures fresh plugin loading after installation

---

## 6. TIPS SERVICE (/src/services/tips/)

**PURPOSE:**
Manages tip display scheduling, history tracking, and registry. Shows contextual tips on spinners based on cooldown periods and relevance.

**KEY FILES:**
- `tipScheduler.ts` - Tip selection and display scheduling
- `tipRegistry.ts` - Tip definitions and context matching
- `tipHistory.ts` - History tracking and session counting

**KEY CLASSES/FUNCTIONS:**
1. `selectTipWithLongestTimeSinceShown(availableTips)` [tipScheduler.ts:10]
2. `getTipToShowOnSpinner(context)` [tipScheduler.ts:32]
3. `recordShownTip(tip)` [tipScheduler.ts:48]
4. `getRelevantTips(context)` [tipRegistry.ts - external]
5. `getSessionsSinceLastShown(tipId)` [tipHistory.ts - external]
6. `recordTipShown(tipId)` [tipHistory.ts - external]

**REPRESENTATIVE CODE SIGNATURE:**
```typescript
export async function getTipToShowOnSpinner(
  context?: TipContext
): Promise<Tip | undefined>

export function recordShownTip(tip: Tip): void
```

**DATA FLOW:**
1. `getTipToShowOnSpinner()` called when spinner displayed
2. Check if tips are enabled (spinnerTipsEnabled setting)
3. `getRelevantTips(context)` filters tips by context (tool, mode, etc.)
4. `selectTipWithLongestTimeSinceShown()` picks tip not shown recently
5. `recordShownTip()` updates history and emits analytics
6. Tip rotates based on cooldownSessions threshold

**INTERACTIONS:**
- **Uses:** Settings, TipRegistry, TipHistory
- **Emits:** logEvent (tengu_tip_shown with cooldownSessions)
- **Called from:** Spinner display logic

**KEY ALGORITHMS/MECHANISMS:**
- **LRU Rotation:** Selects tip with longest time since last shown
- **Cooldown Tracking:** Sessions counted since last display
- **Context Filtering:** Tips filtered by relevance context

---

## 7. MCP SERVICE (/src/services/mcp/)

**PURPOSE:**
Model Context Protocol (MCP) client implementation providing resource browsing, tool execution, and prompt management. Handles MCP server connections, authentication, elicitation, and error handling.

**KEY FILES:**
- `client.ts` - Main MCP client (119KB, comprehensive protocol implementation)
- `auth.ts` - OAuth and authentication (88KB)
- `config.ts` - Configuration and validation
- `channelPermissions.ts` - Channel-level permissions
- `elicitationHandler.ts` - Elicitation support
- `MCPConnectionManager.tsx` - Connection lifecycle management
- Multiple transport implementations (StdioClientTransport, SSEClientTransport, StreamableHTTPClientTransport)

**KEY ALGORITHMS/MECHANISMS:**
- **Lazy Server Initialization:** Resources prefetched on demand
- **Permission Scoping:** Channel-level, server-level permission checks
- **Error Recovery:** Connection management with reconnection logic
- **Elicitation Flow:** User approval for resource access
- **OAuth Flow:** Third-party authentication with token refresh

---

## 8. API SERVICE (/src/services/api/)

**PURPOSE:**
Provides Claude API client implementation with session management, prompt caching, error handling, logging, and billing integration.

**KEY FILES:**
- `claude.ts` - Main API client (125KB)
- `client.ts` - HTTP client abstraction
- `errors.ts` - Error definitions and handling (41KB)
- `logging.ts` - Detailed logging/telemetry (24KB)
- `promptCacheBreakDetection.ts` - Cache invalidation tracking
- `sessionIngress.ts` - Session initialization
- `filesApi.ts` - File upload/handling (21KB)
- `metricsOptOut.ts` - Metrics opt-out handling
- `referral.ts` - Referral program integration

**KEY ALGORITHMS/MECHANISMS:**
- **Prompt Cache Management:** Tracks cache hits/misses/breaks
- **Session Ingress:** Initializes sessions with proper context
- **Error Mapping:** Maps API errors to user-friendly messages
- **Logging Pipeline:** Structured logging with privacy controls
- **Billing Integration:** Tracks usage metrics and optional telemetry

---

## SERVICES SUMMARY

**Layered Architecture:**
- **Analytics Layer:** Event logging and telemetry routing
- **API Layer:** Claude API client with caching and error handling
- **Background Tasks:** autoDream and SessionMemory using stopHooks + forkedAgent
- **Permission Model:** MCP and plugins have explicit permission checks
- **Configuration:** Dynamic config from GrowthBook with local caching
- **Event Logging:** Centralized event emission with multi-backend routing

---

## PART 2: UTILS DIRECTORY (/src/utils/)

**UTILS DIRECTORY STRUCTURE (198 files):**
```
utils/
├── bash/                (Bash parsing, execution, completion)
├── background/          (Background task management)
├── settings/            (Settings management and persistence)
├── git/                 (Git operations and caching)
├── mcp/                 (MCP utilities)
├── hooks/               (Hook implementation and management)
├── permissions/         (Permission checking)
├── telemetry/           (Telemetry and tracing)
├── secureStorage/       (Secure credential storage)
├── model/               (Model selection and info)
├── shell/               (Shell detection and management)
└── [~150+ individual utility files]
```

---

## 1. BASH UTILITIES (/src/utils/bash/)

**PURPOSE:**
Comprehensive bash command parsing, execution, and analysis. Includes shell quoting, command registry, completion, and tree-sitter AST parsing for security analysis.

**KEY FILES:**
- `parser.ts` - Command parsing orchestrator
- `bashParser.ts` - Pure TypeScript bash parser (tree-sitter-bash compatible)
- `bashPipeCommand.ts` - Pipe command handling
- `ParsedCommand.ts` - Parsed command data structure
- `commands.ts` - Command registry and specs
- `registry.ts` - Command information registry
- `shellQuoting.ts` - Shell quoting utilities
- `shellCompletion.ts` - Shell completion logic
- `ast.ts` - AST walking and security analysis
- `treeSitterAnalysis.ts` - Tree-sitter analysis

**KEY CLASSES/FUNCTIONS:**
1. `parseCommand(command)` [parser.ts:56]
2. `parseCommandRaw(command)` [parser.ts - external]
3. `ensureInitialized()` [parser.ts:50]
4. `bashParser.parseSource(source, timeoutMs)` [bashParser.ts]
5. Shell quote/unquote functions [shellQuoting.ts]
6. Command registry lookups [registry.ts]
7. Completion generation [shellCompletion.ts]

**REPRESENTATIVE CODE SIGNATURE:**
```typescript
export interface ParsedCommandData {
  rootNode: Node
  envVars: string[]
  commandNode: Node | null
  originalCommand: string
}

export async function parseCommand(command: string): Promise<ParsedCommandData | null>

export type TsNode = {
  type: string
  text: string
  startIndex: number
  endIndex: number
  children: TsNode[]
}
```

**DATA FLOW:**
1. `parseCommand(command)` with UTF-8 length validation (MAX_COMMAND_LENGTH = 10000)
2. If TREE_SITTER_BASH feature enabled: `await ensureParserInitialized()`
3. `mod.parse(command)` produces TsNode tree from Rust parser
4. `findCommandNode(rootNode, null)` extracts main command
5. `extractEnvVars(commandNode)` identifies environment variables
6. Return ParsedCommandData with root node, env vars, command node

**INTERACTIONS:**
- **Uses:** Bun feature flags for conditional compilation
- **Emits:** logEvent (tengu_tree_sitter_load with success boolean)
- **Used by:** Bash tool, security analysis, completion logic
- **Depends on:** Optional tree-sitter WASM module

**KEY ALGORITHMS/MECHANISMS:**
- **Tree-sitter Integration:** WASM-based parsing with 50ms timeout + 50K node budget
- **Graceful Fallback:** Non-tree-sitter builds fall back to legacy regex/shell-quote
- **Environment Variable Extraction:** Walks AST for declaration_command nodes
- **Security Sentinel:** PARSE_ABORTED symbol for parser abort vs. null (module not loaded)
- **UTF-8 Byte Offsets:** startIndex/endIndex are byte offsets, not JS string indices

---

## 2. MESSAGES UTILITIES (/src/utils/messages.ts - 5512 lines)

**PURPOSE:**
Core message construction, manipulation, and analysis. Handles creation of user, assistant, and system messages with proper attachment and content block handling.

**KEY CLASSES/FUNCTIONS:**
1. `createUserMessage(input)` - Create user message with attachments
2. `createAssistantMessage(content)` - Create assistant response
3. `createSystemMessage(content, level, tag)` - Create system message
4. `hasToolCallsInLastAssistantTurn(messages)` - Safety check
5. `countToolCallsSince(messages, sinceUuid)` - Token counting
6. `extractTag(message)` - Extract system tags
7. `isCompactBoundaryMessage(message)` - Compaction marker detection
8. `createMemorySavedMessage(filesTouched)` - Memory operation feedback
9. Message normalization functions
10. Content block creation and manipulation
11. Hook attachment creation (HookAttachment types)

**REPRESENTATIVE CODE SIGNATURE:**
```typescript
export function createUserMessage(input: {
  content: string | ContentBlockParam[]
  attachments?: Attachment[]
}): UserMessage

export function hasToolCallsInLastAssistantTurn(messages: Message[]): boolean

export function createMemorySavedMessage(
  filesTouched: string[]
): {title: string, verb: 'Saved' | 'Improved'}
```

**DATA FLOW:**
1. Messages created via factory functions
2. Content blocks validated and normalized
3. Attachments (files, images, memory) attached
4. Messages tagged for system boundaries (compact, etc.)
5. Messages stored with UUID for later reference
6. Analysis functions walk message arrays for patterns

**INTERACTIONS:**
- **Used by:** All code generating messages (tools, hooks, agents)
- **Uses:** Anthropic SDK types, attachment utilities
- **Emits:** logEvent for attachment counts, memory operations
- **Core to:** Message history, compaction, summarization

**KEY ALGORITHMS/MECHANISMS:**
- **Content Normalization:** Converts string/ContentBlockParam[] to consistent format
- **Lazy Content Block Creation:** Factory functions for different types
- **Message Tagging:** XML tags mark boundaries (COMMAND_NAME_TAG, TICK_TAG)
- **UUID Tracking:** Each message gets UUID for position tracking across operations
- **Hook Attachment Wrapping:** Wraps hook outputs in consistent attachment structure

---

## 3. HOOKS UTILITIES (/src/utils/hooks.ts - 5022 lines)

**PURPOSE:**
User-defined shell commands executed at various lifecycle points (startup, tool use, session end, etc.). Provides hook execution engine with JSON output parsing, async/sync variants, and TTY/non-TTY handling.

**KEY FILES:**
- `hooks.ts` - Main hook execution engine
- `hooks/hooksConfigSnapshot.ts` - Hook configuration snapshots
- `hooks/postSamplingHooks.ts` - Post-sampling hook registry

**KEY CLASSES/FUNCTIONS:**
1. `executeHook(event, config, permissions)` - Main hook executor
2. `executeSetupHook()` - Startup hook
3. `executeSessionStartHook()` - Session initialization
4. `executeSessionEndHook()` - Session cleanup
5. `executeStopHook()` - Turn completion hook
6. `executePostSamplingHook()` - Post-turn extraction
7. `parseHookOutput(output, schema)` - JSON/text parsing
8. `formatHookCommand(hook)` - Command formatting
9. `substituteUserConfigVariables(hook)` - Variable substitution

**REPRESENTATIVE CODE SIGNATURE:**
```typescript
export async function executeHook(
  event: HookEvent,
  config: HookConfig,
  permissions?: ToolPermissionContext
): Promise<HookResultMessage | undefined>

export function registerPostSamplingHook(hook: PostSamplingHookFn): void
```

**DATA FLOW:**
1. Hook event triggered (e.g., post-tool-use)
2. Retrieve hook configuration from settings or plugin
3. Format hook command with variable substitution ({session_id}, {project_dir}, etc.)
4. Spawn hook process with proper environment
5. Capture stdout/stderr with optional JSON output parsing
6. Validate output against hook schema (sync/async variant)
7. Create HookResultMessage with hook name, status, output
8. Return to caller for further processing

**INTERACTIONS:**
- **Uses:** Shell execution (spawn, ShellCommand), environment setup
- **Reads:** Settings, plugin options, hook configuration
- **Emits:** logEvent (hook execution metrics)
- **Telemetry:** startHookSpan/endHookSpan for tracing
- **Called from:** Tool use, session management, permission handling

**KEY ALGORITHMS/MECHANISMS:**
- **TTY Detection:** Allocates pseudo-terminal for interactive hooks
- **JSON Parsing:** Attempts JSON parse on hook output, falls back to text
- **Schema Validation:** Validates output against sync/async hook schemas
- **Variable Substitution:** Replaces {session_id}, {project_dir}, etc. from context
- **Error Handling:** Graceful failures don't block main execution
- **Async Hook Support:** Fire-and-forget execution for background operations

---

## 4. AUTH UTILITIES (/src/utils/auth.ts - 2002 lines)

**PURPOSE:**
Authentication handling for API keys, OAuth tokens, AWS STS, and credential management. Includes token refresh, validation, caching, and secure storage.

**KEY CLASSES/FUNCTIONS:**
1. `isAnthropicAuthEnabled()` - Check 1P auth support
2. `getAuthToken()` - Get current auth token
3. `isOAuthTokenExpired(token)` - Token validation
4. `refreshOAuthToken(token)` - OAuth refresh flow
5. `shouldUseClaudeAIAuth()` - Auth method selection
6. `checkHasTrustDialogAccepted()` - Trust check
7. `getMacOsKeychainStorageServiceName()` - Keychain name
8. `getUsername()` - Get system username
9. `getApiKeyFromFileDescriptor()` - API key reading
10. `getOAuthTokenFromFileDescriptor()` - OAuth token reading
11. `checkStsCallerIdentity()` - AWS STS validation
12. `AwsAuthStatusManager` (class) - AWS auth state management

**REPRESENTATIVE CODE SIGNATURES:**
```typescript
export function isAnthropicAuthEnabled(): boolean

export async function getAuthToken(): Promise<string | null>

export async function refreshOAuthToken(
  token: OAuthTokens
): Promise<OAuthTokens>
```

**DATA FLOW:**
1. Determine auth source priority:
   - First-party Anthropic: if `isAnthropicAuthEnabled()`
   - OAuth: if `shouldUseClaudeAIAuth()` or CCR/Claude Desktop
   - API Key: from env, keychain, or settings
   - AWS STS: if configured
2. Cache results with TTL (5 minutes for API key helper)
3. Validate token expiration
4. Refresh if needed (OAuth)
5. Return token or null if all sources fail

**INTERACTIONS:**
- **Uses:** Secure storage (keychain), lockfile, AWS STS
- **Stores:** OAuth tokens, API keys in config/keychain
- **Called from:** API client initialization
- **Emits:** logEvent (auth success/failure)

**KEY ALGORITHMS/MECHANISMS:**
- **Auth Source Priority:** Cascade through multiple sources in order
- **Token TTL Caching:** 5-minute cache for expensive key operations
- **OAuth Token Refresh:** Automatic refresh before expiration
- **Managed Context Guard:** CCR/Claude Desktop bypass local settings API keys
- **AWS STS Integration:** For AWS-hosted credential chain
- **Secure Storage:** macOS Keychain, Windows Credential Manager, Linux Secret Service

---

## 5. CONFIG UTILITIES (/src/utils/config.ts - 1817 lines)

**PURPOSE:**
Global configuration management with file-based persistence, watched updates, and re-entrancy protection. Handles project config, user config, billing info, and model selections.

**KEY CLASSES/FUNCTIONS:**
1. `getGlobalConfig()` - Read config
2. `saveGlobalConfig(config)` - Write config
3. `getProjectConfig()` - Project-specific config
4. `saveProjectConfig(config)` - Save project config
5. `watchGlobalConfig(callback)` - Watch file changes
6. `getOrCreateUserID()` - User ID generation/caching
7. `getSettings_DEPRECATED()` - Legacy settings
8. `checkHasTrustDialogAccepted()` - Trust check

**REPRESENTATIVE CODE SIGNATURE:**
```typescript
export function getGlobalConfig(): GlobalConfig

export function saveGlobalConfig(updates: Partial<GlobalConfig>): void

export function watchGlobalConfig(callback: (config: GlobalConfig) => void): void
```

**DATA FLOW:**
1. Read config from ~/.claude/config.json (or equivalent platform path)
2. Parse with error handling (corrupted files → empty config)
3. Cache in memory with optional file watcher
4. Apply defaults for missing fields
5. On write: merge updates, write atomically with lockfile
6. Notify watchers of changes

**INTERACTIONS:**
- **Uses:** File I/O, JSON parsing, lockfile for atomic writes
- **Watched by:** Settings sync, auth refresh, theme changes
- **Called from:** Most modules reading persistent config
- **Emits:** logEvent for config errors/validation

**KEY ALGORITHMS/MECHANISMS:**
- **Re-entrancy Guard:** insideGetConfig flag prevents recursive logEvent calls
- **Atomic Writes:** Uses lockfile for multi-process safety
- **File Watching:** watchFile with debounce for rapid changes
- **Lazy Initialization:** Memoized config read until first write
- **Error Resilience:** Corrupted files fall back to empty config + logging

---

## 6. ATTACHMENTS UTILITIES (/src/utils/attachments.ts - 3997 lines)

**PURPOSE:**
Attachment handling for files, images, and memory context. Validates attachment types, manages file references, and constructs content blocks.

**KEY CLASSES/FUNCTIONS:**
1. `parseAttachments(input)` - Parse attachment spec
2. `validateAttachment(attachment)` - Validation
3. `getAttachmentSize(attachment)` - Size calculation
4. `createFileAttachment(filePath)` - File attachment
5. `createImageAttachment(imagePath)` - Image attachment
6. `createMemoryAttachment(memoryFile)` - Memory attachment
7. `getAttachmentContent(attachment)` - Content reading
8. `AttachmentValidator` (class)

**REPRESENTATIVE CODE SIGNATURE:**
```typescript
export interface Attachment {
  type: 'file' | 'image' | 'memory'
  path: string
  size?: number
}

export function parseAttachments(input: unknown): Attachment[]
```

**DATA FLOW:**
1. Parse attachment specification from user input
2. Validate each attachment (type, path, access)
3. Calculate size for memory tracking
4. Create appropriate content block (file, image, or memory)
5. Attach to message

**INTERACTIONS:**
- **Uses:** FileReadTool, image utilities, memory paths
- **Used by:** Message creation, user prompt handling
- **Validates:** File access, image dimensions, memory file locations

**KEY ALGORITHMS/MECHANISMS:**
- **Type Detection:** Infers attachment type from file extension/path
- **Size Calculation:** For quota tracking
- **Image Handling:** May resize/downsample for API limits
- **Memory Injection:** Merges memory file content with user attachments

---

## 7. SESSION STORAGE UTILITIES (/src/utils/sessionStorage.ts - 5105 lines)

**PURPOSE:**
Persistent storage of session transcripts, file history, and context snapshots. Handles JSONL persistence, loading, compaction, and recovery.

**KEY CLASSES/FUNCTIONS:**
1. `getTranscriptPathForSession(sessionId)` - Transcript location
2. `getAgentTranscriptPath(sessionId, agentId)` - Agent transcript
3. `saveSessionTranscript(messages)` - Persist messages
4. `loadSessionTranscript(sessionId, options)` - Load with options
5. `listSessionsImpl()` - List all sessions
6. `getCurrentBatchFilePath()` - Batch file path
7. `getPersistedWorktreeSession(sessionId)` - Get worktree session
8. `commitContextCollapse(entries)` - Compact boundary

**REPRESENTATIVE CODE SIGNATURE:**
```typescript
export function getTranscriptPathForSession(
  sessionId: SessionId | string
): string

export async function loadSessionTranscript(
  sessionId: SessionId,
  options: LoadOptions
): Promise<TranscriptMessage[]>
```

**DATA FLOW:**
1. Each session stores transcript in JSONL format
2. Each message/entry is one JSON line
3. On save: append entry to session transcript
4. On load: read head + tail for efficient startup
5. Compaction: periodically consolidate files
6. Recovery: scan for orphaned transcripts

**INTERACTIONS:**
- **Uses:** File I/O, JSONL parsing
- **Stores:** Message history, file snapshots, compaction boundaries
- **Called from:** Main loop on each turn, compaction logic
- **Depends on:** sessionId, projectDir

**KEY ALGORITHMS/MECHANISMS:**
- **JSONL Format:** One entry per line for streaming/recovery
- **Head + Tail Read:** Efficient startup without loading entire file (LITE_READ_BUF_SIZE)
- **Lazy Compaction:** Consolidates after size threshold (SKIP_PRECOMPACT_THRESHOLD)
- **Context Collapse:** Marks boundaries for memory-efficient loading
- **Atomic Append:** Ensures single-turn entries are atomic

---

## 8. GIT UTILITIES (/src/utils/git.ts - 926 lines)

**PURPOSE:**
Git operations including repo detection, branch tracking, diff analysis, and commit information retrieval.

**KEY CLASSES/FUNCTIONS:**
1. `findGitRoot(startPath)` - Find .git directory
2. `getBranch(repoPath)` - Current branch name
3. `getDiffStats(repoPath, files)` - Diff statistics
4. `getCommitInfo(repoPath, ref)` - Commit metadata
5. `getWorktreeCount(repoPath)` - Worktree counting
6. `isShallowClone(repoPath)` - Shallow detection
7. `getRemoteUrl(repoPath)` - Remote URL

**REPRESENTATIVE CODE SIGNATURE:**
```typescript
export const findGitRoot: {
  (startPath: string): string | null
  reset(): void
}

export async function getBranch(repoPath: string): Promise<string | null>
```

**DATA FLOW:**
1. `findGitRoot`: walk directory tree up until .git found
2. `getBranch`: read .git/HEAD or .git/refs/
3. `getDiffStats`: parse git diff --stat output
4. `getCommitInfo`: parse git log output
5. Cache results with LRU for repeated calls

**INTERACTIONS:**
- **Uses:** File I/O, git commands (spawn)
- **Used by:** Context analysis, file tracking, compaction
- **Caching:** LRU (50 entries for git root), per-turn for diff

**KEY ALGORITHMS/MECHANISMS:**
- **LRU Memoization:** findGitRoot cached with LRU (max 50 entries)
- **Filesystem Stat:** Optimized path walk using stat, not spawn git
- **Shallow Clone Detection:** Checks .git/shallow file
- **Worktree Support:** Handles .git files (worktrees/submodules)

---

## 9. PERMISSIONS UTILITIES (/src/utils/permissions/)

**PURPOSE:**
File system permission checking, glob pattern validation, and access control for tools and read operations.

**KEY FILES:**
- `filesystem.ts` - File system access permissions
- `fileOperations.ts` - Specific operation validation

**KEY CLASSES/FUNCTIONS:**
1. `getFileReadIgnorePatterns()` - Read ignore patterns
2. `normalizePatternsToPath()` - Pattern normalization
3. `validateFileAccess(filePath, context)` - Access check
4. `isPathAllowed(filePath, allowedPatterns)` - Pattern match
5. `getPermissionContext()` - Context extraction

**REPRESENTATIVE CODE SIGNATURE:**
```typescript
export function getFileReadIgnorePatterns(): string[]

export function validateFileAccess(
  filePath: string,
  context: ToolPermissionContext
): ValidationResult
```

**DATA FLOW:**
1. Retrieve ignore patterns from settings/policy
2. Normalize patterns for comparison
3. Check file path against allowed patterns
4. Return allow/deny decision
5. Log permission decisions for audit trail

**INTERACTIONS:**
- **Uses:** Settings, glob pattern library
- **Used by:** FileReadTool, bash execution, attachment validation
- **Logs:** Permission denials for analytics/audit

**KEY ALGORITHMS/MECHANISMS:**
- **Glob Pattern Matching:** Supports * ? ** patterns
- **Path Normalization:** Handles relative/absolute paths
- **Pattern Priority:** First match wins (allow/deny order matters)
- **Caching:** Minimal caching to avoid stale permission updates

---

## UTILITIES SUMMARY

**EXECUTION LAYER:**
- **bash/:** Shell command parsing, execution, completion
- **hooks.ts:** Hook orchestration and output parsing

**PERSISTENCE LAYER:**
- **sessionStorage.ts:** Transcript and state persistence
- **config.ts:** Global configuration management
- **settings/:** User settings and validation

**SECURITY LAYER:**
- **auth.ts:** Authentication and credential management
- **permissions/:** File and tool access control

**ANALYSIS LAYER:**
- **git.ts:** Repository information and diff analysis
- **attachments.ts:** Content validation and attachment handling
- **messages.ts:** Message construction and analysis

**INFRASTRUCTURE LAYER:**
- **model utilities:** Model selection and configuration
- **telemetry:** Event logging and tracing
- **secureStorage:** Credential encryption and management

---

## CRITICAL INTERACTIONS & DATA FLOWS

### 1. MESSAGE PIPELINE
```
createUserMessage() → messages.ts → Message type → sessionStorage.ts
→ Persistent JSONL transcript → Analysis/Compaction
```

### 2. HOOK EXECUTION
```
User prompt → hooks.ts (executeHook) → spawn shell → parseHookOutput()
→ HookResultMessage → messages.ts
```

### 3. AUTHENTICATION
```
API call needed → auth.ts (getAuthToken) → checkOAuth/getApiKey
→ Refresh if needed → Cache with TTL → Return token
```

### 4. ANALYTICS
```
logEvent() → services/analytics/index.ts → queue if no sink
→ attachAnalyticsSink() → route to Datadog/1P → batched export
```

### 5. SESSION PERSISTENCE
```
Main loop → Message created → sessionStorage.ts (saveSessionTranscript)
→ Append to JSONL → Load on recovery → Compaction threshold check
```

### 6. GIT CONTEXT
```
Tool execution → context.ts → git.ts (findGitRoot, getDiffStats)
→ Cache with LRU → Update on cwd change
```

---

**END OF COMPREHENSIVE RESEARCH REPORT**