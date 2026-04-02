Agent completed. agent_id: research-tools, agent_type: explore, status: completed, description: Research tools module, elapsed: 193s, total_turns: 0, duration: 193s

Now I have comprehensive information. Let me compile the report:

---

# COMPREHENSIVE RESEARCH REPORT: Tools Module

## 1. PURPOSE
The tools module (`/mnt/disk1/zy/internal_wiki/.git-clones/claude-code-sourcemap/restored-src/src/tools/`) is the core execution framework for Claude Agent operations. It defines a plugin architecture where each tool represents a discrete capability (file operations, bash execution, web search, etc.) that the AI model can invoke. The module manages tool registration, discovery, permission checking, progress tracking, and UI rendering for ~45+ built-in tools plus MCP (Model Context Protocol) integrations.

---

## 2. SUB-MODULE LISTING (42 subdirectories)

| Directory | File Count | Purpose |
|-----------|-----------|---------|
| **AgentTool** | 3 | Nested agent invocation; spawns sub-agents for task decomposition |
| **AskUserQuestionTool** | 2 | Interactive prompts; requests user input with custom UI |
| **BashTool** | 18 | Shell command execution with security validation, sandboxing, git tracking |
| **BriefTool** | 4 | Structured data attachment & upload handling |
| **ConfigTool** | 3 | Configuration management (Ant-only) |
| **EnterPlanModeTool** | 2 | Mode transition; enables planning-focused interaction |
| **EnterWorktreeTool** | 2 | Git worktree management; isolated working directories |
| **ExitPlanModeTool** | 2 | Mode exit; returns to normal interaction |
| **ExitWorktreeTool** | 3 | Worktree cleanup and exit |
| **FileEditTool** | 6 | File modification with diff tracking, undo support, skill activation |
| **FileReadTool** | 5 | File content retrieval with permission checks, size limits |
| **FileWriteTool** | 3 | New file creation with git diff output |
| **GlobTool** | 2 | File pattern matching using glob syntax |
| **GrepTool** | 2 | Text search in files using ripgrep with regex support |
| **LSPTool** | 3 | Language Server Protocol integration for IDE-like features |
| **ListMcpResourcesTool** | 2 | MCP resource enumeration |
| **MCPTool** | 2 | Generic MCP protocol bridge |
| **McpAuthTool** | 1 | MCP server authentication |
| **NotebookEditTool** | 2 | Jupyter/notebook cell manipulation |
| **PowerShellTool** | 3 | PowerShell execution (Windows-specific) |
| **REPLTool** | 2 | Interactive REPL environment (Ant-only) |
| **ReadMcpResourceTool** | 2 | MCP resource fetching |
| **RemoteTriggerTool** | 2 | Remote task triggering (feature-gated) |
| **ScheduleCronTool** | 3 | Cron job creation, listing, deletion |
| **SendMessageTool** | 2 | Async messaging to teammates |
| **SkillTool** | 3 | Custom plugin/extension execution |
| **SleepTool** | 1 | Deliberate execution pause (PROACTIVE/KAIROS mode) |
| **SyntheticOutputTool** | 1 | Synthetic result generation |
| **TaskCreateTool** | 2 | Task creation in task system (Todo v2) |
| **TaskGetTool** | 2 | Task retrieval |
| **TaskListTool** | 3 | Task enumeration with filtering |
| **TaskOutputTool** | 2 | Background task output streaming |
| **TaskStopTool** | 2 | Task cancellation |
| **TaskUpdateTool** | 3 | Task status/metadata modification |
| **TeamCreateTool** | 2 | Agent swarm team creation |
| **TeamDeleteTool** | 2 | Team deletion |
| **TodoWriteTool** | 3 | Quick todo item creation |
| **ToolSearchTool** | 3 | Deferred tool discovery via keyword search |
| **WebFetchTool** | 4 | HTTP URL fetching with preapproved domain checking |
| **WebSearchTool** | 1 | Internet search via Anthropic API |
| **shared** | 2 | Git operation tracking, multi-agent spawning |
| **testing** | 1 | Test utilities |

**Total: 143 .ts files across 42 subdirectories + 1 top-level utils.ts file**

---

## 3. KEY CLASSES/TYPES (15 exports)

| Name | File Path | Role |
|------|-----------|------|
| **Tool<Input, Output, Progress>** | `Tool.ts:362` | Core interface defining all tool capabilities—schema, execution, permissions, rendering |
| **ToolDef** | `Tool.ts:721` | Partial tool definition; accepts omitted methods that `buildTool()` fills with defaults |
| **ToolUseContext** | `Tool.ts:158` | Runtime execution context; passes tools, app state, permission context, abort signal |
| **ToolResult<T>** | `Tool.ts:321` | Return value wrapping data, new messages, context modifiers, MCP metadata |
| **ToolProgress<P>** | `Tool.ts:307` | In-flight progress update: `{ toolUseID, data }` |
| **ToolPermissionContext** | `Tool.ts:123` | Permission rules, mode (default/bypass), working directories, denial tracking |
| **ValidationResult** | `Tool.ts:95` | Sync validation outcome: `{ result: true }` or `{ result: false, message, errorCode }` |
| **BashTool** | `BashTool/BashTool.tsx:1` | Shell execution with operators, pipes, security checks, sandbox support |
| **FileEditTool** | `FileEditTool/FileEditTool.ts:1` | Unified diff-based file editing with undo, file history, LSP integration |
| **GrepTool** | `GrepTool/GrepTool.ts:1` | Ripgrep wrapper with context lines, output modes (content/files/count) |
| **WebSearchTool** | `WebSearchTool/WebSearchTool.ts:1` | Anthropic web search v20250305 with domain filtering |
| **ToolSearchTool** | `ToolSearchTool/ToolSearchTool.ts:1` | Keyword search over deferred tools; enables lazy tool loading |
| **TaskListTool** | `TaskListTool/TaskListTool.ts:1` | Todo v2 task enumeration with filtering by resolved status |
| **buildTool()** | `Tool.ts:783` | Factory function: merges definition with TOOL_DEFAULTS, returns complete Tool |
| **getTools()** | `tools.ts:271` | Runtime tool pool builder; respects mode, permission rules, feature flags |

---

## 4. REPRESENTATIVE SNIPPETS

### 4.1 Tool Interface Definition
```typescript
// Tool.ts:362-450
export type Tool<
  Input extends AnyObject = AnyObject,
  Output = unknown,
  P extends ToolProgressData = ToolProgressData,
> = {
  aliases?: string[]
  searchHint?: string
  call(
    args: z.infer<Input>,
    context: ToolUseContext,
    canUseTool: CanUseToolFn,
    parentMessage: AssistantMessage,
    onProgress?: ToolCallProgress<P>,
  ): Promise<ToolResult<Output>>
  description(
    input: z.infer<Input>,
    options: {
      isNonInteractiveSession: boolean
      toolPermissionContext: ToolPermissionContext
      tools: Tools
    },
  ): Promise<string>
  readonly inputSchema: Input
  readonly inputJSONSchema?: ToolInputJSONSchema
  outputSchema?: z.ZodType<unknown>
  isConcurrencySafe(input: z.infer<Input>): boolean
  isEnabled(): boolean
  isReadOnly(input: z.infer<Input>): boolean
  readonly name: string
  maxResultSizeChars: number
  readonly strict?: boolean
}
```

### 4.2 buildTool Factory
```typescript
// Tool.ts:783-792
export function buildTool<D extends AnyToolDef>(def: D): BuiltTool<D> {
  return {
    ...TOOL_DEFAULTS,
    userFacingName: () => def.name,
    ...def,
  } as BuiltTool<D>
}
```

### 4.3 Tool Definition Example (TaskListTool)
```typescript
// TaskListTool/TaskListTool.ts:33-90
export const TaskListTool = buildTool({
  name: TASK_LIST_TOOL_NAME,
  searchHint: 'list all tasks',
  maxResultSizeChars: 100_000,
  async description() {
    return DESCRIPTION
  },
  async prompt() {
    return getPrompt()
  },
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  get outputSchema(): OutputSchema {
    return outputSchema()
  },
  shouldDefer: true,
  isEnabled() {
    return isTodoV2Enabled()
  },
  isConcurrencySafe() {
    return true
  },
  isReadOnly() {
    return true
  },
  async call() {
    const taskListId = getTaskListId()
    const allTasks = (await listTasks(taskListId)).filter(
      t => !t.metadata?._internal,
    )
    return { data: { tasks } }
  },
})
```

### 4.4 Tool Registration (tools.ts)
```typescript
// tools.ts:193-251
export function getAllBaseTools(): Tools {
  return [
    AgentTool,
    TaskOutputTool,
    BashTool,
    ...(hasEmbeddedSearchTools() ? [] : [GlobTool, GrepTool]),
    ExitPlanModeV2Tool,
    FileReadTool,
    FileEditTool,
    FileWriteTool,
    NotebookEditTool,
    WebFetchTool,
    TodoWriteTool,
    WebSearchTool,
    TaskStopTool,
    ...(isTodoV2Enabled() ? [TaskCreateTool, TaskGetTool, TaskUpdateTool, TaskListTool] : []),
    ...(isToolSearchEnabledOptimistic() ? [ToolSearchTool] : []),
  ]
}
```

### 4.5 Git Operation Tracking Types
```typescript
// shared/gitOperationTracking.ts:35-43
export type CommitKind = 'committed' | 'amended' | 'cherry-picked'
export type BranchAction = 'merged' | 'rebased'
export type PrAction =
  | 'created'
  | 'edited'
  | 'merged'
  | 'commented'
  | 'closed'
  | 'ready'
```

---

## 5. DATA FLOW: Tool Registration, Discovery & Invocation

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. REGISTRATION (Build Time / Startup)                          │
├─────────────────────────────────────────────────────────────────┤
│ · Individual tool modules export Tool via buildTool({...})      │
│ · tools.ts aggregates all exports into getAllBaseTools()        │
│ · Conditional logic filters by:                                 │
│   - Feature flags (PROACTIVE, KAIROS, AGENT_TRIGGERS, etc.)     │
│   - Environment (USER_TYPE=ant, NODE_ENV=test, ENABLE_LSP)     │
│   - Runtime checks (isTodoV2Enabled(), isPowerShellToolEnabled) │
│ · Result: ~45+ base tools available each session               │
└─────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. PERMISSION FILTERING (Request Start)                         │
├─────────────────────────────────────────────────────────────────┤
│ · getTools(permissionContext) called                            │
│ · Filters by deny rules: getDenyRuleForTool(ctx, tool)         │
│ · REPL mode hides REPL_ONLY_TOOLS from direct invocation       │
│ · isEnabled() gate: tool.isEnabled() ? keep : drop             │
│ · Adds MCP tools: assembleToolPool(builtIn, mcpTools)           │
│ · Result: ~30-40 tools in prompt (deferred tools hidden)        │
└─────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. DEFERRED TOOL DISCOVERY (Optional Mid-Query)                 │
├─────────────────────────────────────────────────────────────────┤
│ · Model calls ToolSearchTool with keyword query                 │
│ · isDeferredTool(tool) checks: shouldDefer=true && !alwaysLoad │
│ · Keyword match via description prompt (memoized)               │
│ · Returns top-N matching deferred tools by relevance            │
│ · Model then calls discovered tool normally                    │
└─────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. INVOCATION & PERMISSION GATE                                 │
├─────────────────────────────────────────────────────────────────┤
│ A. Validation (sync): tool.validateInput(input, context)       │
│    Returns { result: true } or { result: false, message, code} │
│    Example: BashTool checks mode validity, path safety          │
│                                                                  │
│ B. Permission Check (async): tool.checkPermissions(i, ctx)     │
│    Returns { behavior: 'allow'|'deny'|'ask', updatedInput }    │
│    Example: Bash checks command against shell rules             │
│                                                                  │
│ C. Hook Inspection (canUseTool callback):                       │
│    Pre/Post tool hooks can modify or reject                     │
│                                                                  │
│ D. User Confirmation (if permission=ask):                       │
│    Show permission dialog; user approves/denies                 │
└─────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. EXECUTION                                                    │
├─────────────────────────────────────────────────────────────────┤
│ · tool.call(input, context, canUseTool, parentMsg, onProgress) │
│ · onProgress(toolUseID, data) emitted during execution          │
│ · Returns ToolResult<Output>: { data, newMessages?, mcpMeta? } │
│ · Error thrown → mapToolResultToToolResultBlockParam() wraps   │
└─────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. RESULT RENDERING                                             │
├─────────────────────────────────────────────────────────────────┤
│ · mapToolResultToToolResultBlockParam(data, id) → API shape     │
│ · renderToolResultMessage(data, progress, opts) → React JSX     │
│ · extractSearchText(data) → transcript indexing string          │
│ · Collapse logic: isSearchOrReadCommand? reduce verbosity       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. CONFIGURATION & KNOBS

### Environment Variables (Process.env)
- `USER_TYPE='ant'` → Ant-only tools (REPLTool, ConfigTool, TungstenTool)
- `NODE_ENV='test'` → Enable TestingPermissionTool
- `ENABLE_LSP_TOOL='true'` → LSP integration
- `CLAUDE_CODE_SIMPLE='true'` → Simple mode (Bash/Read/Edit only)
- `CLAUDE_CODE_VERIFY_PLAN='true'` → VerifyPlanExecutionTool

### Bun Feature Flags (feature() function)
- `PROACTIVE`, `KAIROS` → SleepTool
- `AGENT_TRIGGERS` → Cron tools (Create/Delete/List)
- `AGENT_TRIGGERS_REMOTE` → RemoteTriggerTool
- `MONITOR_TOOL`, `OVERFLOW_TEST_TOOL`, `CONTEXT_COLLAPSE`, `TERMINAL_PANEL`
- `WEB_BROWSER_TOOL`, `WORKFLOW_SCRIPTS`, `UDS_INBOX`, `HISTORY_SNIP`
- `COORDINATOR_MODE` → Task coordination
- `KAIROS`, `KAIROS_PUSH_NOTIFICATION`, `KAIROS_GITHUB_WEBHOOKS`

### Tool-Specific Config
- **BashTool**: `modeValidation.ts` (async/sync/interactive), `shouldUseSandbox()`, timeout (default 60s, max configurable)
- **FileEditTool**: `constants.ts` – file size limits (1GB max), max line count
- **GrepTool**: ripgrep flags (–type, -i, -A, -B, -C, –glob)
- **Task tools**: `isTodoV2Enabled()` toggle for v2 task system
- **ToolSearchTool**: `maxResults` default 5, keyword scoring via memoized description fetch
- **Permission defaults**: `TOOL_DEFAULTS` in Tool.ts (fail-closed: isEnabled=true, isConcurrencySafe=false, isReadOnly=false)

---

## 7. INTERACTIONS WITH OTHER MODULES

### Services
- **analytics** (`services/analytics/index.js`): `logEvent()` for git operations, tool usage telemetry
- **LSP** (`services/lsp/`): `getLspServerManager()`, diagnostic clearing, file change notifications
- **MCP** (`services/mcp/`): `notifyVscodeFileUpdated()`, resource listing/fetching
- **API** (`services/api/claude.js`): `queryModelWithStreaming()` for Web Search
- **Task Management** (`utils/tasks.js`): Task CRUD, list filtering, status tracking

### Utils & Infrastructure
- **Permissions** (`utils/permissions/`): `checkReadPermissionForTool()`, `checkWritePermissionForTool()`, `matchWildcardPattern()`
- **File Operations** (`utils/file.js`, `utils/fsOperations.js`): read, write, stat, path resolution
- **Bash/Shell** (`utils/bash/`, `utils/Shell.js`): command parsing, AST analysis, execution via `exec()`
- **Skills** (`skills/loadSkillsDir.js`): Skill activation on file edits
- **Git** (`utils/gitDiff.js`, `shared/gitOperationTracking.ts`): Diff generation, commit/PR tracking
- **Sandbox** (`utils/sandbox/sandbox-adapter.js`): Container-based execution for risky commands

### Hooks
- **useCanUseTool** (`hooks/useCanUseTool.js`): Pre-invocation tool authorization
- **Pre/Post Tool Use**: Modifies input, rejects calls, tracks denials

---

## 8. DOMAIN-SPECIFIC TERMINOLOGY

| Term | Definition |
|------|-----------|
| **Deferred Tool** | Tool with `shouldDefer: true`; hidden from initial prompt, discovered via ToolSearchTool |
| **MCP Tool** | Tool from Model Context Protocol server; integrated via `mcp__<server>__<tool>` naming |
| **Tool Result Size Limit** | `maxResultSizeChars` threshold; exceeds → persisted to disk, model gets preview + path |
| **Concurrency Safe** | `isConcurrencySafe()=true` → tool can run in parallel with others; false → queued solo |
| **Destructive** | `isDestructive()=true` → operations that cannot be undone (delete, overwrite, send) |
| **Permission Behavior** | `'allow'` (auto-approve), `'deny'` (reject), `'ask'` (user dialog), `'skip'` (defer) |
| **Search/Read Collapsible** | Tools/commands marked as search/read can collapse to single-line summary in UI |
| **Tool Use ID** | UUID for tool invocation; tracks progress, matches results to calls |
| **ToolUseContext** | Runtime environment: abort signal, app state, permission context, tool list |
| **Prompt Caching** | System prompt frozen at turn start; reused across tool calls in same session |
| **Auto Classifier** | Security classifier; `toAutoClassifierInput()` serializes tool for risk assessment |

---

## 9. ALGORITHMS & MECHANISMS

### 9.1 Bash Command Security Validation
**File**: `BashTool/bashPermissions.ts`, `BashTool/sedValidation.ts`

```
Input: bash command string
├─ Parse AST via parseForSecurity()
├─ Check 1: Mode validation (async vs sync vs interactive)
├─ Check 2: Path validation (within cwd, no symlink escapes)
├─ Check 3: Destructive cmd detection (rm, mv, truncate)
├─ Check 4: Read-only constraint (whitelist safe commands)
├─ Check 5: sed/perl regex validation (no arbitrary code injection)
├─ Check 6: Sandbox necessity (risky I/O → containerize)
└─ Output: { result: true/false, message?, errorCode? }
```

### 9.2 Tool Search Keyword Matching
**File**: `ToolSearchTool/ToolSearchTool.ts`

```
Input: query (user keywords or "select:<tool_name>")
├─ If "select:foo" → direct lookup by name
├─ Else: filter deferred tools
│  ├─ For each deferred tool:
│  │  ├─ Fetch tool.prompt() (memoized per tool name)
│  │  ├─ Tokenize query + prompt text
│  │  ├─ Compute relevance score (term frequency)
│  │  └─ Store (toolName, score)
│  ├─ Sort by score DESC
│  └─ Slice top max_results
└─ Output: { matches: [toolNames], total_deferred_tools, pending_mcp }
```

### 9.3 Permission Rule Matching
**File**: `utils/permissions/filesystem.ts`, `utils/permissions/permissions.ts`

```
Input: tool, input, permission rules, shell patterns
├─ Check deny rules first (fail-closed)
├─ Exact match: rule.toolName === tool.name
├─ MCP prefix match: rule like "mcp__server" strips all tools from server
├─ Shell pattern match: matchWildcardPattern(rule, input)
│  (for bash: git, find, cp /foo/*, etc.)
├─ If matched deny rule → block
├─ Else if allow rule → approve
├─ Else if ask rule → show dialog
└─ Output: PermissionResult { behavior, updatedInput }
```

### 9.4 Git Operation Detection
**File**: `shared/gitOperationTracking.ts`

```
Input: bash command + stdout/stderr
├─ Regex detection:
│  ├─ GIT_COMMIT_RE: /\bgit.*commit\b/
│  ├─ GIT_PUSH_RE: /\bgit.*push\b/
│  ├─ GIT_CHERRY_PICK_RE, GIT_MERGE_RE, GIT_REBASE_RE
│  └─ GH_PR_ACTIONS: gh pr create/merge/comment/close/ready
├─ Extract metadata:
│  ├─ Commit SHA: [branch abc1234] message
│  ├─ Branch name: ref update line in stderr
│  ├─ PR number/URL: GitHub URL or "Pull request #123"
│  └─ Action type: create/edit/merge/etc.
├─ Log OTLP counter increments (commits, PRs)
├─ Fire analytics event: tengu_git_operation
└─ Auto-link session to PR if URL found
```

### 9.5 File Edit Diff Generation
**File**: `FileEditTool/utils.ts`, `utils/gitDiff.ts`

```
Input: original text, search string, replacement
├─ Find search string in original (with fuzzy matching fallback)
├─ Generate structured patch (hunks with context)
├─ Compute line deltas (countLinesChanged)
├─ Output both git diff + structured patch format
├─ Preserve git metadata (author, dates)
└─ Return: { originalFile, filePath, structuredPatch, gitDiff }
```

---

## 10. STATE MACHINES & LIFECYCLES

### Tool Invocation Lifecycle
```
PENDING
  ↓ validateInput() → ValidationResult
  ├─→ INVALID → error block to model
  └─→ VALID
       ↓ checkPermissions() → PermissionResult
       ├─→ behavior='deny' → reject block
       ├─→ behavior='ask' → show dialog
       │   ├─→ user approves → proceed
       │   └─→ user denies → reject block
       ├─→ behavior='skip' → defer
       └─→ behavior='allow'
            ↓ tool.call()
            ├─→ onProgress() events → ProgressMessage[]
            ├─→ throw Error → renderToolUseErrorMessage()
            └─→ return ToolResult<Output>
                 ↓ mapToolResultToToolResultBlockParam()
                 ↓ renderToolResultMessage()
                 └─→ DONE
```

### Tool Deferral State
```
Tool instantiated with shouldDefer=true
  ↓
Tool appears in getAllBaseTools() but filtered by isDeferredTool()
  ↓
At request time: not in initial prompt to model
  ↓
Model recognizes need → calls ToolSearchTool
  ↓
ToolSearchTool returns matching deferred tool names
  ↓
Model calls tool normally (now it knows the name & schema)
  └─→ If alwaysLoad=true: tool skips deferral entirely
```

### Bash Task Background/Foreground
```
SHORT: foreground (≤15s) → direct output, blocks UI
  ↓
MEDIUM: background (15-60s) → spinner + TaskOutputTool streaming
  ↓
LONG: background (>60s) → register as AppState task, live updates
  ↓
Interrupt during foreground → cancel & discard result
Interrupt during background → mark task stopped
```

---

## 11. ERROR/EDGE CASES & FALLBACK PATHS

### Error Handling Patterns

| Error Type | Detection | Response | Fallback |
|-----------|-----------|----------|----------|
| **Input Validation** | `validateInput()` throws or returns `{result: false}` | Send error block to model | None; blocking |
| **Permission Denied** | `checkPermissions()` returns `behavior: 'deny'` | `renderToolUseRejectedMessage()` | None; blocking |
| **File Not Found** | `isENOENT` check in FileRead/FileEdit | Suggest similar paths via `findSimilarFile()` | Use `suggestPathUnderCwd()` |
| **File Too Large** | Byte size > limit (1GB for FileRead, etc.) | Return persisted file reference + preview | Store in disk cache, model gets path |
| **Bash Timeout** | Command runs > timeout (default 60s, max configurable) | Kill process, send timeout message | None; hard kill |
| **Git Failure** | `exitCode !== 0` on git command | Append git stderr; track failure in analytics | None; propagate error |
| **Permission Cascade** | Denial count exceeds threshold | Show escalated dialog or switch to bypass mode | Fallback to prompting user |
| **Sandbox Unavailable** | Sandbox manager missing/unavailable for risky cmd | Run unsandboxed (with warning) or block | Log diagnostic |
| **Tool Not Found** | `findToolByName(tools, name)` returns undefined | Error: tool not available | None; blocking |
| **Deferred Tool Collision** | Tool name in both built-in + MCP | Built-in tool takes precedence (via `uniqBy`) | MCP tool silently dropped |

### Edge Cases

1. **Circular Tool Dependencies**: Team creation calls tools that reference team creation → lazy require (`getTeamCreateTool()`) breaks cycle
2. **Large Result Buffering**: Tool result > `maxResultSizeChars` → split into preview + disk file path
3. **Concurrent Bash Calls**: 
   - `isConcurrencySafe()=false` → queued sequentially
   - `isConcurrencySafe()=true` → run in parallel
4. **Path Traversal Escapes**: Symlinks, `..`, absolute paths checked; validation rejects unsafe paths
5. **Prompt Injection in Bash**: `parseForSecurity()` AST-parses commands; sed/perl regex validated against code patterns
6. **Stale File History Cache**: LRU `fileStateCache` can evict entries → re-read from disk on miss
7. **REPL Mode Shadowing**: When REPL enabled, Bash/Read/Edit hidden from direct use (wrapped inside REPL VM)
8. **Tool Renamed**: Old name in `aliases` list allows backward-compatible invocation
9. **MCP Server Crash**: Tool becomes unavailable mid-session; `assembleToolPool()` refilters if MCP reconnects
10. **Permission Mode Transition**: Switching between `default` / `bypass` / `ask` modes mid-session; `prePlanMode` saved for restoration on exit

### Recovery Mechanisms

- **Retry Bash**: User can rerun command; transient failures (network, temp file lock) auto-resolved
- **File Conflict Resolution**: FileEdit detects `FILE_UNEXPECTEDLY_MODIFIED_ERROR` (file changed between read & write); error block suggests re-read
- **Git Retry Logic**: Bash tracker detects commit signing failures; model retries with `git -c commit.gpgsign=false`
- **Fallback Permitting**: If user denies too many times, escalate to bypass-mode confirmation
- **Tool Search Retry**: Model can re-query ToolSearch with refined keywords if first result unsuccessful
- **Sandbox Bypass**: If sandboxed execution fails (unlikely), fallback to unsandboxed with warning

---

## 12. TOP-LEVEL .TS FILES IN /tools/

- **`utils.ts`** – 41 lines: Utility functions for tagging messages with tool use IDs and extracting tool IDs from parent messages

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Total Subdirectories** | 42 |
| **Total .ts Files** | 143 |
| **Core Tools** | ~15 (Bash, File*, Glob, Grep, Web*) |
| **Task Management Tools** | 5 (Create, Get, List, Update, Stop) |
| **Feature-Gated Tools** | ~20 (Cron, Sleep, REPL, Monitor, etc.) |
| **MCP Integration Tools** | 3 (ListResources, ReadResource, Auth) |
| **Team/Collaboration Tools** | 4 (TeamCreate, TeamDelete, SendMessage, Agent) |
| **Tool Interface Methods** | 25+ (call, description, prompt, renderToolUse*, etc.) |
| **Permission Models** | 3 (default, bypass, ask) |
| **Error Codes** | Custom validation error codes in ValidationResult |

---

This comprehensive report documents the full architecture, data flows, configuration, and operational details of the tools module, suitable for internal wiki documentation and developer onboarding.