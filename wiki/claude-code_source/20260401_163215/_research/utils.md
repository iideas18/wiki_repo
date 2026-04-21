Agent completed. agent_id: research-utils, agent_type: explore, status: completed, description: Research utils module, elapsed: 160s, total_turns: 0, duration: 140s

Now I have enough information to provide a comprehensive research report. Let me compile it:

---

# COMPREHENSIVE RESEARCH REPORT: Utils Module Analysis
## Claude Code Sourcemap - TypeScript Utilities Library

---

## 1. PURPOSE

The **utils module** is a comprehensive, modular system of 300+ utility functions and classes providing foundational abstractions for the Claude Code desktop application. It encapsulates domain-specific operations across file system management, configuration, authentication, shell execution, permissions, messaging, memory management, cryptography, and telemetry. The module serves as the critical infrastructure layer between the core application logic and external systems (Node.js APIs, filesystems, shells, APIs), enabling consistent, testable, and maintainable abstractions throughout the codebase.

---

## 2. SUB-MODULE LISTING (36 Primary Directories)

### **FILE SYSTEM & I/O** (9 subdirs, 68 files)
- **`filePersistence/`** (2 files) - Persistent file storage layer abstractions
- **`file.ts`** (1519 lines) - Core file operations (read, write, pathExists, safety checks)
- **`fsOperations.ts`** (770 lines) - Abstracted filesystem implementation (platform-aware fs layer)
- **`fileRead.ts`** - Encoding detection, line-ending normalization
- **`fileReadCache.ts`** - LRU-bounded cache for file reads
- **`fileStateCache.ts`** - File stat caching
- **`readFileInRange.ts`** - Efficient partial file reads
- **`path.ts`** - Path normalization, expansion, resolution
- **`xdg.ts`** (65 lines) - XDG directory standards (Linux/Unix config paths)

### **SHELL & PROCESS EXECUTION** (20 subdirs, 88 files)
- **`Shell.ts`** (1530 lines) - Shell initialization, execution, session management
- **`ShellCommand.ts`** (14k lines) - Command wrapping, streaming, exit code handling
- **`bash/`** (15 files + specs/) - Bash-specific specs (aliases, nohup, pyright, sleep, time, timeout)
- **`shell/`** (10 files) - Shell provider abstraction, PowerShell/Bash detection, output limits
- **`powershell/`** (3 files) - PowerShell provider, detection, validation
- **`process.ts`** (69 lines) - EPIPE handling, stdin/stdout management
- **`execFileNoThrow.ts`** - Non-throwing exec wrapper (returns error objects)
- **`execSyncWrapper.ts`** - Synchronous execution with defaults
- **`which.ts`** (82 lines) - Executable lookup (PATH resolution)
- **`genericProcessUtils.ts`** - Generic process utilities
- **`subprocessEnv.ts`** (99 lines) - Subprocess environment setup

### **CONFIGURATION & SETTINGS** (18 subdirs, 74 files)
- **`config.ts`** (1817 lines) - Global/project config reading/writing, structured history
- **`settings/`** (16 files + mdm/) - Settings loader, managed device management (MDM), per-source tracking
- **`env.ts`** (10k lines) - Environment variable access, resolution, validation
- **`envUtils.ts`** - Env value parsing, truthy checks, home directory logic
- **`envValidation.ts`** - Environment schema validation
- **`envDynamic.ts`** - Dynamic environment lookup
- **`cliArgs.ts`** (2k lines) - CLI argument parsing
- **`cliHighlight.ts`** - CLI syntax highlighting configuration
- **`configConstants.ts`** - Configuration constant definitions
- **`caCertsConfig.ts`** (3.6k lines) - CA certificate configuration
- **`caCerts.ts`** (4.4k lines) - Certificate loading and validation

### **AUTHENTICATION & SECURITY** (18 subdirs, 84 files)
- **`auth.ts`** (2002 lines) - OAuth/API key management, token refresh, verification
- **`secureStorage/`** (6 files) - Platform-specific secure storage (macOS Keychain, fallback, plaintext)
- **`authFileDescriptor.ts`** (6.8k lines) - File-based auth credential access
- **`authPortable.ts`** - Cross-platform auth normalization
- **`permissions/`** (24 files) - Permission rules, mode enforcement, pattern matching, classifier
- **`aws.ts`** (2.3k lines) - AWS STS caller identity verification
- **`awsAuthStatusManager.ts`** - AWS authentication status tracking
- **`crypto.ts`** (763 lines) - Cryptographic utilities
- **`mtls.ts`** - Mutual TLS support

### **GIT & VERSION CONTROL** (6 subdirs, 21 files)
- **`git.ts`** (926 lines) - Git root detection, branch/commit operations, worktree support
- **`git/`** (3 files) - Git filesystem operations (cached reads, worktree paths)
- **`gitDiff.ts`** - Git diff generation
- **`gitSettings.ts`** - Git configuration reading
- **`github/`** (1 file) - GitHub-specific utilities
- **`worktree.ts`** (1519 lines) - Git worktree management, activation/deactivation
- **`getWorktreePaths.ts`** - Worktree path resolution

### **MESSAGE & CONTEXT PROCESSING** (11 subdirs, 88 files)
- **`messages.ts`** (5512 lines) - Message normalization, content block handling, format conversion
- **`messages/`** (2 files) - Message mappers, utilities
- **`attachments.ts`** (3997 lines) - File/image attachment processing, tool integration
- **`analyzeContext.ts`** (1382 lines) - Context window analysis, token counting, compaction logic
- **`tokens.ts`** (261 lines) - Token usage parsing, budget calculations
- **`tokenBudget.ts`** (73 lines) - Token budget tracking
- **`contextAnalysis.ts`** - Context analysis utilities
- **`contextSuggestions.ts`** - Context suggestion generation
- **`queryHelpers.ts`** - Query processing helpers
- **`queryProfiler.ts`** - Query performance profiling

### **MEMORY & STORAGE** (9 subdirs, 41 files)
- **`memory/`** (2 files) - Memory type definitions (User, Project, Local, Managed, AutoMem, TeamMem)
- **`claudemd.ts`** (1479 lines) - Claude memory file loading, parsing, hierarchy, includes
- **`sessionStorage.ts`** (5105 lines) - Session data persistence, recovery, log serialization
- **`sessionStoragePortable.ts`** (793 lines) - Cross-platform session storage
- **`filePersistence/`** (2 files) - File persistence abstractions
- **`todo/`** (1 file) - Todo management
- **`task/`** (5 files) - Task persistence, output directory management
- **`fileHistory.ts`** (1115 lines) - File edit history tracking

### **TELEMETRY & ANALYTICS** (9 subdirs, 40 files)
- **`telemetry/`** (9 files) - Event logging, tracing (Perfetto), session tracing, BigQuery export
- **`telemetryAttributes.ts`** (71 lines) - Telemetry attribute definitions
- **`stats.ts`** (1061 lines) - Statistics collection and reporting
- **`statsCache.ts`** - Statistics caching

### **UI/DISPLAY RENDERING** (12 subdirs, 52 files)
- **`ansiToPng.ts`** (214k lines) - ANSI escape sequence to PNG rendering
- **`ansiToSvg.ts`** (8.2k lines) - ANSI escape sequence to SVG rendering
- **`markdown.ts`** - Markdown rendering to CLI (marked.js integration)
- **`theme.ts`** (639 lines) - Theme/color management, syntax highlighting configuration
- **`truncate.ts`** (179 lines) - String truncation with ANSI support
- **`textHighlighting.ts`** (166 lines) - Text selection/highlighting utilities
- **`hyperlink.ts`** - Hyperlink creation for terminal output
- **`highlightMatch.tsx`** - Highlight matched text in React
- **`imageResizer.ts`** (880 lines) - Image downsampling and resizing
- **`imageValidation.ts`** - Image format/size validation
- **`imageStore.ts`** - Image storage and retrieval
- **`imagePaste.ts`** - Image paste handling

### **MODEL & API INTEGRATION** (16 subdirs, 58 files)
- **`model/`** (16 files) - Model options, capabilities, costs, providers, validation
- **`modelCost.ts`** - Cost estimation for models
- **`api.ts`** (718 lines) - Tool schema conversion, API request/response handling
- **`http.ts`** - HTTP client abstractions
- **`apiPreconnect.ts`** (2.8k lines) - API preconnection logic

### **ADVANCED UTILITIES** (44 subdirs, 156 files)
- **`plugins/`** (44 files) - Plugin system, loading, validation, sandboxing
- **`permissions/`** (24 files) - Permission rule engine, classifier, mode tracking
- **`mcp/`** (2 files) - Model Context Protocol support, validation
- **`skills/`** (1 file) - Skill/agent tool management
- **`computerUse/`** (15 files) - Computer use tool integration, locking
- **`swarm/`** (13 files + backends/) - Agent swarm management, multi-backend execution
- **`sandbox/`** (2 files) - Sandbox adapter for secure execution
- **`background/`** (0 files, remote/ subdir) - Background task management
- **`teleport/`** (4 files) - Session teleporting, deep linking
- **`deepLink/`** (6 files) - Deep link parsing and handling
- **`ultraplan/`** (2 files) - Ultra planning utilities
- **`dxt/`** (2 files) - DevX toolkit utilities
- **`nativeInstaller/`** (5 files) - Native dependency installation
- **`claudeInChrome/`** (7 files) - Chrome extension support

### **UTILITY PRIMITIVES & HELPERS** (91 miscellaneous files)
- **`array.ts`** - Array operations, grouping, counting
- **`stringUtils.ts`** - String escaping, case conversion, plural handling
- **`intl.ts`** - Internationalization, grapheme/word segmentation
- **`json.ts`** - JSONC parsing, safe JSON parsing with LRU cache
- **`jsonRead.ts`** - JSON file reading with BOM handling
- **`memoize.ts`** - TTL-based memoization, LRU caching, async memoization
- **`sleep.ts`** - Promise-based delays
- **`uuid.ts`** - UUID generation
- **`hash.ts`** - Hashing utilities
- **`set.ts`** - Set operations
- **`sequential.ts`** - Sequential operation queuing
- **`stream.ts`** - Stream utilities
- **`treeify.ts`** - Tree structure formatting
- **`words.ts`** (800 lines) - Word tokenization, stemming, semantic analysis
- **`xml.ts`** - XML utilities
- **`yaml.ts`** - YAML parsing
- **`glob.ts`** - File glob pattern matching
- **`ripgrep.ts`** (679 lines) - Ripgrep integration (system/builtin/embedded modes)
- **`diff.ts`** (4.8k lines) - Structured diff generation using diff library

---

## 3. KEY CLASSES/FUNCTIONS (15 Representative Utilities)

| # | Function/Class | File | Role |
|---|---|---|---|
| 1 | **`Shell`** | `Shell.ts` | Manages shell initialization, command execution, session configuration, shell provider selection |
| 2 | **`Cursor`** | `Cursor.ts` | Kill ring (cut/paste buffer), yank operations, grapheme-aware text manipulation |
| 3 | **`getConfig()`** | `config.ts` | Loads global/project config with re-entrancy guards, returns structured config objects |
| 4 | **`normalizeMessagesForAPI()`** | `messages.ts` | Converts internal message format to Anthropic SDK format, handles tool results |
| 5 | **`analyzeContextWindow()`** | `analyzeContext.ts` | Estimates token usage, manages context compaction, calculates tool overhead |
| 6 | **`getSecureStorage()`** | `secureStorage/index.ts` | Platform-adaptive secure storage (macOS Keychain, plaintext fallback) |
| 7 | **`findGitRoot()`** | `git.ts` | Cached git root detection, handles worktrees and submodules |
| 8 | **`parseClaudeMarkdown()`** | `claudemd.ts` | Parses memory files with include directives, handles hierarchy and priority |
| 9 | **`applyMarkdown()`** | `markdown.ts` | Converts markdown to ANSI-colored CLI output using marked.js |
| 10 | **`loadSessionState()`** | `sessionStorage.ts` | Recovers session data from persistent storage, deserialization |
| 11 | **`findExecutable()`** | `findExecutable.ts` | Locates executables in PATH with platform-specific logic |
| 12 | **`ripgrepCommand()`** | `ripgrep.ts` | Resolves ripgrep executable (system/builtin/embedded), returns spawn args |
| 13 | **`memoizeWithTTL()`** | `memoize.ts` | Write-through cache with TTL and background refresh |
| 14 | **`safeParseJSON()`** | `json.ts` | LRU-bounded JSON parsing with error handling (50 entry limit) |
| 15 | **`getMemoryFiles()`** | `claudemd.ts` | Discovers and loads all memory files in project hierarchy |

---

## 4. REPRESENTATIVE SNIPPETS

### Snippet 1: Cursor Kill Ring (Emacs-style cut/paste)
```typescript
// From Cursor.ts (lines 26-48)
export function pushToKillRing(
  text: string,
  direction: 'prepend' | 'append' = 'append',
): void {
  if (text.length > 0) {
    if (lastActionWasKill && killRing.length > 0) {
      // Accumulate with the most recent kill
      if (direction === 'prepend') {
        killRing[0] = text + killRing[0]
      } else {
        killRing[0] = killRing[0] + text
      }
    } else {
      // Add new entry to front of ring
      killRing.unshift(text)
      if (killRing.length > KILL_RING_MAX_SIZE) {
        killRing.pop()
      }
    }
    lastActionWasKill = true
    lastActionWasYank = false
  }
}
```

### Snippet 2: Token Budget Calculation (Context Window Analysis)
```typescript
// From analyzeContext.ts (lines 46-53)
export const TOOL_TOKEN_COUNT_OVERHEAD = 500

async function countTokensWithFallback(
  messages: Anthropic.Beta.Messages.BetaMessageParam[],
  tools: Anthropic.Beta.Messages.BetaToolUnion[],
): Promise<number | null> {
  const result = await countMessagesTokensWithAPI(messages, tools)
  if (result !== null) {
    return result
  }
  // Fallback to haiku estimation
  return await countTokensViaHaikuFallback(messages, tools)
}
```

### Snippet 3: Safe JSON Parsing with LRU Cache
```typescript
// From json.ts (lines 42-58)
const parseJSONCached = memoizeWithLRU(parseJSONUncached, json => json, 50)

export const safeParseJSON = Object.assign(
  function safeParseJSON(
    json: string | null | undefined,
    shouldLogError: boolean = true,
  ): unknown {
    if (!json) return null
    const result =
      json.length > PARSE_CACHE_MAX_KEY_BYTES
        ? parseJSONUncached(json, shouldLogError)
        : parseJSONCached(json, shouldLogError)
    return result.ok ? result.value : null
  },
  { cache: parseJSONCached.cache },
)
```

### Snippet 4: TTL-Based Memoization with Background Refresh
```typescript
// From memoize.ts (lines 40-82)
export function memoizeWithTTL<Args extends unknown[], Result>(
  f: (...args: Args) => Result,
  cacheLifetimeMs: number = 5 * 60 * 1000,
): MemoizedFunction<Args, Result> {
  const cache = new Map<string, CacheEntry<Result>>()

  const memoized = (...args: Args): Result => {
    const key = jsonStringify(args)
    const cached = cache.get(key)
    const now = Date.now()

    if (!cached) {
      const value = f(...args)
      cache.set(key, { value, timestamp: now, refreshing: false })
      return value
    }

    if (cached && now - cached.timestamp > cacheLifetimeMs && !cached.refreshing) {
      cached.refreshing = true
      Promise.resolve().then(() => {
        const newValue = f(...args)
        if (cache.get(key) === cached) {
          cache.set(key, { value: newValue, timestamp: Date.now(), refreshing: false })
        }
      })
    }
    return cached.value
  }
  return Object.assign(memoized, { cache: { clear: () => cache.clear() } })
}
```

### Snippet 5: Platform-Adaptive Secure Storage
```typescript
// From secureStorage/index.ts (lines 1-14)
import { createFallbackStorage } from './fallbackStorage.js'
import { macOsKeychainStorage } from './macOsKeychainStorage.js'
import { plainTextStorage } from './plainTextStorage.js'

export function getSecureStorage(): SecureStorage {
  if (process.platform === 'darwin') {
    return createFallbackStorage(macOsKeychainStorage, plainTextStorage)
  }
  // TODO: add libsecret support for Linux
  return plainTextStorage
}
```

---

## 5. DATA FLOW & IMPORT PATTERNS

### Inbound Dependencies (Consumers of Utils)
- **Tool execution**: `BashTool`, `FileEditTool`, `SkillTool` depend heavily on `Shell.ts`, `permissions/`, `attachments.ts`
- **Session management**: `sessionStorage.ts` is imported by bootstrap and recovery services
- **Message processing**: `messages.ts` and `attachments.ts` are core to message normalization pipeline
- **Authentication**: `auth.ts` is used by OAuth client, API key management, subscription checking
- **Configuration**: `config.ts` imported by 60+ files for global/project settings

### Internal Cross-Imports (Utils → Utils)
- **`file.ts`** → `fsOperations.ts`, `fileRead.ts`, `path.ts`
- **`config.ts`** → `env.ts`, `json.ts`, `auth.ts`
- **`messages.ts`** → `attachments.ts`, `markdown.ts`, `tokens.ts`
- **`Shell.ts`** → `ShellCommand.ts`, `process.ts`, `permissions/`
- **`sessionStorage.ts`** → `json.ts`, `file.ts`, `messages.ts`
- **`analyzeContext.ts`** → `tokens.ts`, `messages.ts`, `model/modelOptions.ts`

### Export Patterns
- **Index-based barrels**: `bash/specs/index.ts` exports command specs array
- **Object assignment**: `safeParseJSON` attached with `.cache` property
- **Factory functions**: `getSecureStorage()`, `getShellProvider()`, `getCronScheduler()`

---

## 6. UTILITY CATEGORIES & FUNCTIONAL GROUPING

### **A. File System Operations (Category: `fs`)**
- **Core**: `file.ts`, `fsOperations.ts`, `path.ts`
- **Specialized**: `readFileInRange.ts`, `fileRead.ts`, `fileReadCache.ts`, `glob.ts`
- **Purpose**: Abstract Node.js fs, handle encoding, cache, path normalization

### **B. Process/Shell Execution (Category: `shell`)**
- **Core**: `Shell.ts`, `ShellCommand.ts`, `process.ts`
- **Providers**: `shell/bashProvider.ts`, `shell/powershellProvider.ts`
- **Support**: `which.ts`, `execFileNoThrow.ts`, `genericProcessUtils.ts`
- **Purpose**: Execute commands, manage subprocess lifecycle, handle streams

### **C. Configuration & Environment (Category: `config`)**
- **Core**: `config.ts`, `env.ts`, `settings/`
- **Specialized**: `envUtils.ts`, `caCerts.ts`, `cliArgs.ts`
- **Purpose**: Load/persist config, resolve environment variables, manage per-source settings

### **D. Authentication & Security (Category: `auth`)**
- **Core**: `auth.ts`, `secureStorage/`
- **Specialized**: `authFileDescriptor.ts`, `permissions/`, `crypto.ts`
- **Purpose**: Manage credentials, permissions enforcement, secure storage

### **E. Message & Content Processing (Category: `message`)**
- **Core**: `messages.ts`, `attachments.ts`, `analyzeContext.ts`
- **Specialized**: `markdown.ts`, `tokens.ts`, `diff.ts`
- **Purpose**: Normalize messages, process attachments, analyze token usage

### **F. Memory & Persistence (Category: `memory`)**
- **Core**: `claudemd.ts`, `sessionStorage.ts`, `memory/`
- **Specialized**: `task/`, `todo/`, `fileHistory.ts`
- **Purpose**: Load memory files, persist session state, track edits

### **G. Model & API Integration (Category: `api`)**
- **Core**: `api.ts`, `model/`
- **Specialized**: `http.ts`, `apiPreconnect.ts`, `modelCost.ts`
- **Purpose**: Convert schemas, manage model options, cost estimation

### **H. Utility Primitives (Category: `util`)**
- **String**: `stringUtils.ts`, `intl.ts`, `truncate.ts`
- **Data**: `array.ts`, `json.ts`, `hash.ts`, `set.ts`
- **Control**: `memoize.ts`, `sleep.ts`, `sequential.ts`, `stream.ts`
- **Purpose**: Common data operations, caching, scheduling

### **I. Display & Rendering (Category: `ui`)**
- **ANSI/SVG**: `ansiToPng.ts`, `ansiToSvg.ts`
- **Markdown**: `markdown.ts`, `hyperlink.ts`
- **Images**: `imageResizer.ts`, `imageValidation.ts`
- **Theme**: `theme.ts`, `textHighlighting.ts`
- **Purpose**: Terminal output rendering, theme application

### **J. Advanced Features (Category: `advanced`)**
- **Git**: `git.ts`, `worktree.ts`, `gitDiff.ts`
- **Plugins**: `plugins/` (44 files)
- **Permissions**: `permissions/` (24 files)
- **Swarms**: `swarm/`, `computerUse/`
- **Telemetry**: `telemetry/` (9 files), `stats.ts`
- **Purpose**: Domain-specific integrations and analytics

---

## 7. MODULE INTERACTIONS & DEPENDENCIES

### **Highest-Impact Utilities (Most Frequently Imported)**
1. **`messages.ts`** (5512 lines) - Imported by 40+ files (message normalization bottleneck)
2. **`config.ts`** (1817 lines) - Imported by 60+ files (settings access everywhere)
3. **`auth.ts`** (2002 lines) - Imported by 20+ files (credential management)
4. **`claudemd.ts`** (1479 lines) - Imported by 15+ files (memory file processing)
5. **`Shell.ts`** (1530 lines) - Imported by command execution pipeline

### **Dependency Chains**
```
API Calls
  ↓
→ messages.ts (normalize)
→ tokens.ts (estimate cost)
→ analyzeContext.ts (check budget)
→ config.ts (get model)

Tool Execution
  ↓
→ permissions/ (check rules)
→ Shell.ts (execute)
→ ShellCommand.ts (stream output)
→ process.ts (handle errors)

Session Recovery
  ↓
→ sessionStorage.ts (load state)
→ json.ts (parse data)
→ file.ts (read files)
→ path.ts (resolve paths)
```

### **Module Clusters with High Cohesion**
- **Auth Cluster**: `auth.ts`, `secureStorage/`, `authFileDescriptor.ts`, `authPortable.ts`
- **Git Cluster**: `git.ts`, `worktree.ts`, `gitDiff.ts`, `git/gitFilesystem.ts`
- **Shell Cluster**: `Shell.ts`, `ShellCommand.ts`, `bash/`, `shell/`, `powershell/`
- **Permissions Cluster**: `permissions/` (24 files, internal DAG of permissions rules)
- **Telemetry Cluster**: `telemetry/`, `stats.ts`, `logger.ts`

---

## 8. KEY TERMINOLOGY & PATTERNS

### **Terminology**

| Term | Definition | Examples |
|------|-----------|----------|
| **Memory Files** | User/project-level instructions loaded into context window | `CLAUDE.md`, `.claude/rules/*.md`, `CLAUDE.local.md` |
| **Permission Rule** | Declarative allow/deny pattern for tools/operations | Bash redirection rules, file access rules |
| **Kill Ring** | Buffer storing cut text with Alt+Y cycling (Emacs idiom) | `Cursor.ts` implementation |
| **TTL Memoization** | Cache with time-to-live that refreshes in background | `memoizeWithTTL()` pattern |
| **Write-Through Cache** | Return stale cache while refreshing async | `memoizeWithTTL()` behavior |
| **Structured Patch** | Diff hunks with context lines for display | `diff.ts` output format |
| **Content Block** | Message content unit (text, image, tool_use, tool_result) | Anthropic SDK format |
| **Tool Token Overhead** | Fixed ~500 token cost when tools are present | `TOOL_TOKEN_COUNT_OVERHEAD` constant |
| **Context Compaction** | Automatic message history compression to fit budget | `analyzeContext.ts` logic |
| **Shallow Clone** | Git clone with limited history depth (fs detection) | `isShallowCloneFs()` |
| **Worktree** | Git sparse checkout directory (linked to main repo) | `worktree.ts` management |
| **Ripgrep Mode** | System/builtin/embedded variants of `rg` | `ripgrepCommand()` resolution |

### **Design Patterns**

| Pattern | Example | Purpose |
|---------|---------|---------|
| **Factory Function** | `getSecureStorage()`, `getConfig()`, `Shell.create()` | Platform/context-dependent object creation |
| **LRU Cache** | `memoizeWithLRU()` in `memoize.ts`, `fileReadCache.ts` | Bounded memory caching |
| **Memoization with TTL** | `memoizeWithTTL()` for OAuth tokens, config | Stale-while-revalidate pattern |
| **Provider Pattern** | `ShellProvider`, `SecureStorage` interfaces | Pluggable implementations |
| **Fallback Storage** | Keychain→plaintext in `secureStorage/` | Graceful degradation |
| **Re-entrancy Guard** | `insideGetConfig` flag in `config.ts` | Prevent infinite recursion |
| **LRU-Bounded JSON** | 50-entry cache in `json.ts` | Prevent unbounded memory growth |
| **Discriminated Union** | `{ ok: true, value }` vs `{ ok: false }` | Type-safe error handling |
| **Lazy Schema** | `lazySchema.ts` | Defer validation until needed |
| **Stream Wrapping** | `wrapSpawn()` in `ShellCommand.ts` | Unified stream handling |

### **Constant Conventions**
- **`MEMORY_TYPE_VALUES`** - Tuple of valid memory types
- **`PARSE_CACHE_MAX_KEY_BYTES`** - LRU cache key size limit (8KB)
- **`CHECK_INTERVAL_MS`** - Cron scheduler check frequency (1s)
- **`DEFAULT_TIMEOUT`** - Shell execution timeout (30 min)
- **`MAX_OUTPUT_SIZE`** - File output size limit (0.25MB)

---

## 9. ALGORITHMS & MECHANISMS

### **Algorithm 1: Git Root Finding with Memoization**
```
Input: startPath (current directory)
Output: Git root directory or NOT_FOUND symbol

Algorithm:
1. Memoize result (LRU cache ~100 entries)
2. Start from startPath, walk up directory tree
3. At each level, stat `.git` (directory or file)
4. If found (and isDirectory or isFile), normalize and return
5. If reach filesystem root without finding, return NOT_FOUND
6. Log diagnostics: stat count, duration, found flag
```
**Purpose**: Fast repository detection for every command (heavily called)

---

### **Algorithm 2: Token Budget Analysis**
```
Input: messages[], tools[], currentModel
Output: { totalTokens, toolTokens, remaining, compactionNeeded }

Algorithm:
1. For each tool, call token counting API (with ~500 token overhead)
2. Accumulate tool tokens, subtract overhead
3. Call countMessagesTokensWithAPI(messages, tools)
4. If fails, fallback to haiku-based rough estimation
5. Calculate: remaining = contextWindowSize - totalTokens
6. If remaining < AUTOCOMPACT_BUFFER_TOKENS (12%), trigger compaction
7. Return breakdown with category names for display
```
**Purpose**: Prevent context window overflow, trigger auto-compaction

---

### **Algorithm 3: Cron Task Scheduler**
```
Input: scheduled_tasks.json (file), check interval = 1s
Output: Fire matching tasks at scheduled time

Algorithm:
1. Load tasks from .claude/scheduled_tasks.json
2. Watch file for changes with chokidar (300ms stability)
3. Parse cron expressions (e.g., "0 * * * *" = hourly)
4. Calculate next run: nextRunMs = jitteredNextCronRunMs(cron, jitterConfig)
5. Every 1s, check if now >= nextRunMs
6. On fire:
   - Mark as fired in file
   - Delete if aged out (recurring + timeout)
   - Call onFire(prompt)
   - Acquire lock to prevent duplicate firing
7. Handle missed tasks on startup (replay if overdue)
8. Cascade through sessions: session A owns lock, others probe every 5s
```
**Purpose**: Reliable scheduled task execution without background daemon

---

### **Algorithm 4: Memory File Loading with Includes**
```
Input: projectDir, cwd
Output: Array of MemoryFileInfo[] (priority-ordered)

Algorithm:
1. Load managed (global) memory from /etc/claude-code/CLAUDE.md
2. Load user memory from ~/.claude/CLAUDE.md
3. Traverse from cwd → root:
   - Discover CLAUDE.md, .claude/CLAUDE.md, .claude/rules/*.md
   - Files closer to cwd have higher priority
4. Load local memory CLAUDE.local.md (if exists)
5. Parse @includes (@./path, @~/path, @/abs/path)
   - Recursively resolve (prevent circular refs)
   - Non-existent files silently ignored
   - Included files added before includer in priority
6. Return reverse-priority array (latest = highest priority)
```
**Purpose**: Hierarchical context injection into model

---

### **Algorithm 5: TTL Memoization with Background Refresh**
```
Input: f(args) function, cacheLifetimeMs
Output: Memoized function with stale-while-revalidate

Algorithm:
1. Cache entry: { value, timestamp, refreshing: bool }
2. On call(args):
   - key = jsonStringify(args)
   - If no cache entry:
     · Compute value = f(args)
     · Store with now timestamp
     · Return immediately
   - If cache entry exists:
     · If (now - timestamp) < TTL:
       - Return cached value (fresh)
     · If (now - timestamp) >= TTL AND !refreshing:
       - Set refreshing = true
       - Schedule async refresh (Promise.then)
       - Return stale value immediately (fast path)
     · If refreshing in progress:
       - Return stale value (no double-fetch)
3. Background refresh:
   - newValue = f(args)
   - If cache.get(key) still points to old entry:
     · Update with newValue, now timestamp, refreshing = false
```
**Purpose**: Always return instantly (cached value), keep data fresh async

---

### **Algorithm 6: Permission Rule Matching**
```
Input: toolName, commandString, ruleSet[]
Output: { allowed, reason, source }

Algorithm:
1. Iterate rule priority (highest first)
2. For each rule:
   - Match toolName pattern (exact or wildcard)
   - Match operation (e.g., bash redirection: ">" pattern)
   - Match path pattern (if file rule)
3. First matching rule determines outcome
4. Classify confidence:
   - If matches dangerous pattern (e.g., `rm -rf /`): BLOCK
   - If classifier enabled: run ML classifier on transcript
   - Else: ASK user or ALLOW (per permission mode)
5. Return decision + reason + source (settings/managed/default)
```
**Purpose**: Fine-grained operation control, audit trail

---

### **Algorithm 7: Diff Generation with Context**
```
Input: oldContent, newContent, contextLines = 3
Output: StructuredPatchHunk[]

Algorithm:
1. Escape special chars (& and $ confuse diff library)
2. Call structuredPatch(oldContent, newContent)
3. For each hunk:
   - oldStart, oldCount (lines in original)
   - newStart, newCount (lines in new)
   - lines[] with +/- prefixes + contextLines before/after
4. Unescape special chars in output
5. Count additions/removals
6. Update analytics: logEvent('tengu_file_changed', { lines_added, lines_removed })
```
**Purpose**: Human-readable patch for diffs and analytics

---

### **Algorithm 8: Shell Provider Selection**
```
Input: Platform (darwin/linux/win32), env vars
Output: ShellProvider (bash/zsh/powershell)

Algorithm:
1. Check CLAUDE_CODE_SHELL override (if bash/zsh and executable)
2. Check $SHELL environment variable (if bash/zsh)
3. Use which() to find: [zsh, bash] in order
4. Prefer bash if available (more predictable)
5. Fallback to default system shell
6. Validate with --version flag (timeout 1s)
7. Return selected shell + provider instance
```
**Purpose**: Consistent command execution across platforms

---

## 10. SUMMARY: Integration Architecture

The **utils module** operates as a **multi-layered abstraction pyramid**:

```
┌─────────────────────────────────────────────────┐
│ Application Layer (Commands, Tools, Services)  │
├─────────────────────────────────────────────────┤
│ Domain Layer (Git, Auth, Permissions, Memory) │
├─────────────────────────────────────────────────┤
│ Processing Layer (Messages, Tokens, Diff)      │
├─────────────────────────────────────────────────┤
│ Infrastructure Layer (Shell, FS, HTTP, Config) │
├─────────────────────────────────────────────────┤
│ Primitive Layer (String, JSON, Cache, Stream)  │
├─────────────────────────────────────────────────┤
│ Node.js Runtime (fs, child_process, crypto)    │
└─────────────────────────────────────────────────┘
```

**Critical Properties**:
- **Modularity**: 36 directories with clear separation of concerns
- **Caching**: LRU-bounded, TTL-based, with write-through semantics
- **Platform Adaptation**: Darwin (Keychain), Linux, Windows (PowerShell)
- **Type Safety**: Heavy use of discriminated unions, strict nullability
- **Performance**: Memoization, streaming, async-first patterns
- **Testability**: Pure functions, injectable dependencies, factory patterns
- **Observability**: Structured logging, telemetry, diagnostics

**~88,000 lines of TypeScript** providing foundational abstractions that enable the Claude Code application to operate reliably across file systems, shells, authentication systems, and API boundaries.