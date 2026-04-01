Agent completed. agent_id: research-ink-bridge-state, agent_type: explore, status: completed, description: Research ink, bridge, state, elapsed: 232s, total_turns: 0, duration: 128s

Perfect! Now I have enough information to produce a comprehensive report. Let me compile all the findings:

---

# COMPREHENSIVE SOURCE CODE RESEARCH REPORT

## 1. INK MODULE (Terminal UI Renderer)

### Directory Structure
**96 total files** organized as:
- Root level: 45 core files
- `components/`: UI components (Box, Text, Button, etc.)
- `hooks/`: React hooks for terminal interaction
- `layout/`: Yoga layout engine integration
- `events/`: Keyboard/mouse event handling
- `termio/`: Terminal I/O operations

### Purpose
Ink is a React-based terminal rendering engine that transforms React component trees into terminal output. It handles the full lifecycle of terminal UI: component reconciliation, layout computation via Yoga, rendering to a screen buffer, and efficient diff-based terminal output. Key innovation: double-buffering and blit optimization for smooth terminal animations.

### Key Classes/Functions
1. **ink.tsx** (1,722 lines) - Main Ink class: terminal lifecycle, frame rendering, selection/search, mouse/keyboard event dispatch
2. **reconciler.ts** (512 lines) - React reconciler: createInstance, appendChild, commitUpdate for terminal nodes
3. **dom.ts** - DOM node creation/mutation: createNode, appendChildNode, removeChildNode, markDirty
4. **renderer.ts** - Frame rendering: converts dirty DOM subtree to screen buffer with Yoga layout
5. **output.ts** (797 lines) - Operation queue: write/clip/blit/clear operations on screen
6. **screen.ts** (1,486 lines) - Screen buffer: cell grid with style pooling, hyperlink support, diff tracking
7. **log-update.ts** (773 lines) - Terminal diff engine: computes minimal ANSI sequences from frame diffs
8. **render-node-to-output.ts** (1,462 lines) - DOM traversal: renders yoga-laid nodes to output operations
9. **selection.ts** (917 lines) - Text selection: capture, extend, serialize with ANSI inversion
10. **parse-keypress.ts** (801 lines) - Keyboard parsing: raw terminal key sequences → KeyboardEvent
11. **components/Box.tsx** - Flex container with style application
12. **components/Text.tsx** - Text rendering with style/wrap support
13. **layout/engine.ts** - Yoga layout computation wrapper
14. **focus.ts** - Focus manager: tabbing, autoFocus attribute
15. **terminal.ts** - Terminal capabilities: TTY detection, write buffering

### Representative Code Snippets

**DOM Node Structure (dom.ts)**:
```typescript
export type DOMElement = {
  nodeName: ElementNames
  attributes: Record<string, DOMNodeAttribute>
  childNodes: DOMNode[]
  textStyles?: TextStyles
  yogaNode?: LayoutNode
  dirty: boolean
  isHidden?: boolean
  scrollTop?: number
  focusManager?: FocusManager
}

export const markDirty = (node?: DOMNode): void => {
  let current: DOMNode | undefined = node
  while (current) {
    if (current.nodeName !== '#text') {
      (current as DOMElement).dirty = true
    }
    current = current.parentNode
  }
}
```

**Renderer Output (renderer.ts)**:
```typescript
export type RenderOptions = {
  frontFrame: Frame
  backFrame: Frame
  isTTY: boolean
  terminalWidth: number
  terminalRows: number
  altScreen: boolean
  prevFrameContaminated: boolean
}

export type Renderer = (options: RenderOptions) => Frame
```

**Output Operation Types (output.ts)**:
```typescript
export type Operation =
  | WriteOperation
  | ClipOperation
  | UnclipOperation
  | BlitOperation
  | ClearOperation
  | NoSelectOperation
  | ShiftOperation

export type Clip = {
  x1: number | undefined
  x2: number | undefined
  y1: number | undefined
  y2: number | undefined
}
```

### Data Flow
1. React renders components → reconciler creates/updates DOMElements with Yoga nodes
2. markDirty walks up tree marking ancestors as dirty
3. reconciler.resetAfterCommit triggers onComputeLayout (Yoga → computed positions/sizes)
4. render() calls createRenderer which traverses dirty DOM subtree
5. renderNodeToOutput generates write/blit/clip operations
6. Output batches operations, applies to screen buffer
7. logUpdate computes diff (frame.cursor, frame.screen cells)
8. writeDiffToTerminal emits minimal ANSI sequences to terminal

### Interactions
- **React Compiler**: Uses React 19 Fiber architecture for reconciliation
- **Yoga Layout**: Flex-box layout via native WASM binding (`src/native-ts/yoga-layout`)
- **Terminal I/O**: Reads stdin (keyboard/mouse), writes stdout/stderr
- **UI Components**: All components (Box, Text, Button, ScrollBox) build on Ink foundation

### Key Algorithms/Mechanisms
- **Dirty Tracking**: Nodes marked dirty propagate up to root; only dirty subtrees re-render
- **Blit Optimization**: When prevFrameContaminated=false, unchanged regions copied from previous frame screen buffer (O(1) vs O(n) recompute)
- **Style Pooling**: Unique style combinations interned into pool; cells store styleId (not full style)
- **Hyperlink Pool**: OSC 8 hyperlinks cached per frame (25x efficiency vs per-cell)
- **Double Buffering**: frontFrame/backFrame swap prevents tearing; pools (charPool, stylePool, hyperlinkPool) generational-reset every 5min
- **Scroll Draining**: Virtual scroll offsets applied per-frame in throttled chunks (SCROLL_MAX_PER_FRAME rows) to smooth fast flicks
- **Coordinate Transforms**: Yoga offsets tracked during DFS; selection/click hit-test adjusted for screen position

---

## 2. BRIDGE MODULE (Remote Control API Client)

### Directory Structure
**31 files**, no subdirectories. Flat structure for transport-level abstractions.

### Purpose
Bridge handles remote session management over the Anthropic backend API. It encapsulates polling for work items, spawning local agent processes, managing session lifecycle (spawn/kill/track), permission callbacks from remote control requests, and graceful shutdown with token refresh. Acts as the local daemon endpoint for `claude remote-control`.

### Key Classes/Functions
1. **types.ts** (262 lines) - Core types: BridgeConfig, BridgeApiClient, SessionHandle, SessionSpawner, BridgeLogger
2. **bridgeMain.ts** - Main bridge event loop: poll work, spawn sessions, handle permissions
3. **bridgeApi.ts** - HTTP client for environments API: registerBridgeEnvironment, pollForWork, acknowledgeWork
4. **bridgeMessaging.ts** - SDK message handling: isSDKMessage, isSDKControlRequest predicates, permission response dispatch
5. **bridgeUI.ts** - Logger implementation: status display, session list, QR code
6. **sessionRunner.ts** (550 lines) - Child process spawner: manages subprocess stdio/lifecycle/activity tracking
7. **replBridge.ts** - WebSocket transport for CCR v2 (Code Sessions Runtime)
8. **replBridgeTransport.ts** - WebSocket message encoding/decoding
9. **workSecret.ts** - Decodes base64url-encoded work secret from server
10. **jwtUtils.ts** - Session ingress JWT refresh scheduling
11. **createSession.ts** - Session initialization from work response
12. **inboundMessages.ts** - WebSocket ingress parsing
13. **inboundAttachments.ts** - Tool use attachment handling
14. **initReplBridge.ts** - Bridge initialization (CCR v2)
15. **trustedDevice.ts** (210 lines) - Trusted device token management
16. **capacityWake.ts** - Capacity wake notification (pings backend when environment ready)
17. **pollConfig.ts** - Polling interval backoff configuration
18. **sessionIdCompat.ts** - SessionId format compatibility layer
19. **debugUtils.ts** - Error extraction, request/response logging

### Representative Code Snippets

**Bridge Configuration (types.ts)**:
```typescript
export type BridgeConfig = {
  dir: string
  machineName: string
  branch: string
  gitRepoUrl: string | null
  maxSessions: number
  spawnMode: SpawnMode // 'single-session' | 'worktree' | 'same-dir'
  sandbox: boolean
  bridgeId: string
  workerType: string
  environmentId: string
  apiBaseUrl: string
  sessionIngressUrl: string
  sessionTimeoutMs?: number
}

export type SessionHandle = {
  sessionId: string
  done: Promise<SessionDoneStatus>
  kill(): void
  forceKill(): void
  activities: SessionActivity[]
  accessToken: string
  writeStdin(data: string): void
}
```

**API Client (bridgeApi.ts)**:
```typescript
export type BridgeApiClient = {
  registerBridgeEnvironment(config: BridgeConfig): Promise<{
    environment_id: string
    environment_secret: string
  }>
  pollForWork(
    environmentId: string,
    environmentSecret: string,
    signal?: AbortSignal,
    reclaimOlderThanMs?: number,
  ): Promise<WorkResponse | null>
  acknowledgeWork(
    environmentId: string,
    workId: string,
    sessionToken: string,
  ): Promise<void>
  sendPermissionResponseEvent(
    sessionId: string,
    event: PermissionResponseEvent,
    sessionToken: string,
  ): Promise<void>
}
```

**SDK Message Predicates (bridgeMessaging.ts)**:
```typescript
export function isSDKMessage(value: unknown): value is SDKMessage
export function isSDKControlRequest(value: unknown): value is SDKControlRequest
export function isEligibleBridgeMessage(m: Message): boolean
  // Filters virtual REPL messages; only user/assistant/slash-command forwarded
```

### Data Flow
1. Bridge registers environment with backend API (GET /environments, POST /environments)
2. Poll loop calls pollForWork (long-polling with backoff)
3. On work received: decode workSecret → get session ingress URL/token
4. Spawn child process via sessionRunner with CCR v2 env vars (SSE transport)
5. WebSocket connects to session ingress (replBridge/replBridgeTransport)
6. Forward user messages; receive tool_use/result/control_request
7. On control_request (permission prompt): call bridgePermissionCallbacks
8. sendPermissionResponseEvent sends control_response back to session
9. On session end: acknowledge work, loop back to poll

### Interactions
- **Anthropic API**: REST endpoints for work polling and session events
- **Session Ingress**: WebSocket for real-time message exchange (CCR v2)
- **Session Runner**: Spawns child processes with isolated working directories (worktree mode)
- **Permission Callbacks**: integrates with tool permission system
- **Analytics**: Logs session activity for tracking
- **CLI**: `claude remote-control` command calls bridge initialization

### Key Algorithms/Mechanisms
- **Work Polling**: Long-poll with exponential backoff (2s → 2min cap, 10min give-up)
- **Token Refresh**: JWT decoded; if expiring soon, schedule refresh via jwtUtils
- **Session Spawning**: Worktree or single-session mode; stdout replay for title extraction
- **Graceful Shutdown**: SIGTERM→wait 30s→SIGKILL; session state persisted for resume via `--session-id`
- **Permission Dispatch**: Synchronous callback on control_request; response sent via HTTP endpoint
- **Activity Tracking**: Ring buffer of SessionActivity (tool_start, text, result, error) for multi-session UI

---

## 3. STATE MODULE (Global App State Management)

### Directory Structure
**6 files**: AppState.tsx, AppStateStore.ts, store.ts, onChangeAppState.ts, selectors.ts, teammateViewHelpers.ts

### Purpose
State module provides centralized global app state management using a reactive store pattern. Maintains UI state (modals, notifications, sidebar), model settings, tool permissions, speculation state (pipelined inference), teammate presence, and task tracking. Uses React Context + custom Store for efficient updates without Redux overhead.

### Key Classes/Functions
1. **AppStateStore.ts** - Type definitions: AppState, SpeculationState, CompletionBoundary, FooterItem
2. **store.ts** (35 lines) - Generic Store<T>: getState, setState, subscribe
3. **AppState.tsx** - AppStateProvider: creates/provides store, wraps children with MailboxProvider/VoiceProvider
4. **onChangeAppState.ts** - Change listener: fires when state updates
5. **selectors.ts** - Derived state selectors for components
6. **teammateViewHelpers.ts** - Agent swarm teammate state helpers

### Representative Code Snippets

**Generic Store (store.ts)**:
```typescript
export type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (listener: Listener) => () => void
}

export function createStore<T>(
  initialState: T,
  onChange?: OnChange<T>,
): Store<T> {
  let state = initialState
  const listeners = new Set<Listener>()
  return {
    getState: () => state,
    setState: (updater: (prev: T) => T) => {
      const prev = state
      const next = updater(prev)
      if (Object.is(next, prev)) return
      state = next
      onChange?.({ newState: next, oldState: prev })
      for (const listener of listeners) listener()
    },
    subscribe: (listener: Listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}
```

**AppState Type (AppStateStore.ts)**:
```typescript
export type AppState = DeepImmutable<{
  settings: SettingsJson
  verbose: boolean
  mainLoopModel: ModelSetting
  expandedView: 'none' | 'tasks' | 'teammates'
  selectedIPAgentIndex: number
  notifications: { queue: Notification[]; current: Notification | null }
  speculationState: SpeculationState
  toolPermissionContext: ToolPermissionContext
  // ... 50+ other fields
}>

export type SpeculationState =
  | { status: 'idle' }
  | {
      status: 'active'
      id: string
      abort: () => void
      messages: Message[]
      boundary: CompletionBoundary | null
      suggestionLength: number
      toolUseCount: number
      isPipelined: boolean
    }
```

### Data Flow
1. AppStateProvider creates Store<AppState> at mount
2. Components use useAppStateStore() hook to subscribe
3. setState updater function receives prev state, returns next state (immutable)
4. Listener callbacks fire (ink renders, analytics log)
5. onChangeAppState hook notified of [newState, oldState] pair
6. Derived selectors compute UI-relevant slices

### Interactions
- **React**: useSyncExternalStore for store subscription
- **Context**: AppStoreContext provides store to all descendants
- **Mailbox**: MailboxProvider wraps children for async message dispatch
- **Settings**: UI settings changes trigger applySettingsChange
- **Permissions**: Tool permission context included in state
- **Analytics**: State changes logged via logEvent

### Key Algorithms/Mechanisms
- **Immutable Updates**: setState enforces Object.is comparison; unchanged state = no listener fire
- **Shallow Comparison**: Store optimizes for state shape stability (tests use Jest snapshots)
- **Notification Queue**: Fold semantics allow combining duplicate notifications (e.g., repeated errors)
- **Speculation State**: Pipelined inference tracks messages, boundary, abort controller, mutable refs for no-copy appends

---

## 4. CONTEXT MODULE (React Context Providers)

### Directory Structure
**9 files**: QueuedMessageContext.tsx, fpsMetrics.tsx, mailbox.tsx, modalContext.tsx, notifications.tsx, overlayContext.tsx, promptOverlayContext.tsx, stats.tsx, voice.tsx

### Purpose
Context module provides React Context providers for cross-cutting concerns: message queuing, notifications, modals, stats collection, performance metrics, overlay management, and voice input. Each is independently togglable via feature flags or runtime detection.

### Key Classes/Functions
1. **mailbox.tsx** - Mailbox provider: async message dispatch queue with useMailbox hook
2. **notifications.tsx** - Notification system: priority queue, fold semantics, auto-timeout, useNotifications hook
3. **stats.tsx** (StatsStore) - Metrics collection: increment, set, observe (histogram), add (set), with percentile computation
4. **modalContext.tsx** - Modal stack provider
5. **overlayContext.tsx** - Overlay (e.g., selection highlight) state
6. **promptOverlayContext.tsx** - Command palette/prompt overlay context
7. **QueuedMessageContext.tsx** - Deferred message batching
8. **fpsMetrics.tsx** - Frame timing metrics (FPS, frame duration)
9. **voice.tsx** - Voice input context (Ant only, feature-flagged)

### Representative Code Snippets

**Mailbox Context (mailbox.tsx)**:
```typescript
import { Mailbox } from '../utils/mailbox.js'
const MailboxContext = createContext<Mailbox | undefined>(undefined)

export function MailboxProvider({ children }: Props) {
  const mailbox = useMemo(() => new Mailbox(), [])
  return (
    <MailboxContext.Provider value={mailbox}>
      {children}
    </MailboxContext.Provider>
  )
}

export function useMailbox(): Mailbox {
  const mailbox = useContext(MailboxContext)
  if (!mailbox) {
    throw new Error("useMailbox must be used within a MailboxProvider")
  }
  return mailbox
}
```

**Notification Queue (notifications.tsx)**:
```typescript
export type Notification = TextNotification | JSXNotification

type BaseNotification = {
  key: string
  priority: 'low' | 'medium' | 'high' | 'immediate'
  timeoutMs?: number
  fold?: (accumulator: Notification, incoming: Notification) => Notification
  invalidates?: string[]
}

export function useNotifications(): {
  addNotification: (content: Notification) => void
  removeNotification: (key: string) => void
}
```

**Stats Store (stats.tsx)**:
```typescript
export type StatsStore = {
  increment(name: string, value?: number): void
  set(name: string, value: number): void
  observe(name: string, value: number): void // histogram
  add(name: string, value: string): void // set
  getAll(): Record<string, number>
}

function percentile(sorted: number[], p: number): number {
  const index = p / 100 * (sorted.length - 1)
  // Linear interpolation between lower/upper bounds
}
```

### Data Flow
1. Providers mounted in AppState.tsx hierarchy
2. Components consume context via useMailbox, useNotifications, useStats
3. Operations (add notification, increment metric) dispatched to context
4. Context maintains queue/maps; listeners notified on change
5. Stats.observe uses reservoir sampling (Algorithm R) for space-efficient percentiles

### Interactions
- **AppState**: Contexts wrap app state children
- **Mailbox**: Async dispatch for tool results, permissions
- **Notifications**: UI layer renders current notification
- **Analytics**: Stats collected and reported to telemetry
- **Voice**: Feature-flagged, dynamically required

### Key Algorithms/Mechanisms
- **Notification Fold**: When notification with same key added, fold(acc, new) called; result replaces acc
- **Invalidation**: invalidates array lists keys of notifications to remove when this one arrives
- **Reservoir Sampling**: Histogram observe() uses Algorithm R to store up to 1024 samples, compute percentiles from reservoir
- **FPS Metrics**: Frame timestamps tracked; min/max/p50/p99 computed per interval

---

## 5. SKILLS MODULE (AI Model Skills/Commands)

### Directory Structure
**20+ files**: bundled, bundledSkills.ts, loadSkillsDir.ts, mcpSkillBuilders.ts

### Purpose
Skills module manages "skills" — domain-specific prompts that guide the model on specialized tasks. Supports bundled skills (compiled into binary), disk-based skills (loaded from ~/.claude/skills/), plugin skills, and MCP (Model Context Protocol) skills. Each skill is a Command with metadata (name, description, aliases) and a prompt generator.

### Key Classes/Functions
1. **bundledSkills.ts** (80+ lines) - registerBundledSkill, BundledSkillDefinition type
2. **loadSkillsDir.ts** (150+ lines) - Loads skills from disk: parseFrontmatter, loadMarkdownFilesForSubdir, PromptCommand builder
3. **mcpSkillBuilders.ts** - MCP tool-to-skill adapters
4. **bundled/** - Subdirectory with compiled-in skills (reference, debug, etc.)

### Representative Code Snippets

**Bundled Skill Definition (bundledSkills.ts)**:
```typescript
export type BundledSkillDefinition = {
  name: string
  description: string
  aliases?: string[]
  whenToUse?: string
  argumentHint?: string
  allowedTools?: string[]
  model?: string
  disableModelInvocation?: boolean
  userInvocable?: boolean
  isEnabled?: () => boolean
  hooks?: HooksSettings
  context?: 'inline' | 'fork'
  agent?: string
  files?: Record<string, string> // Additional reference files
  getPromptForCommand: (
    args: string,
    context: ToolUseContext,
  ) => Promise<ContentBlockParam[]>
}

export function registerBundledSkill(definition: BundledSkillDefinition): void {
  // Memoized extraction + prompt generation
  // Prevents re-extraction on concurrent calls
}
```

**Skill Loading (loadSkillsDir.ts)**:
```typescript
export type LoadedFrom =
  | 'commands_DEPRECATED'
  | 'skills'
  | 'plugin'
  | 'managed'
  | 'bundled'
  | 'mcp'

export function getSkillsPath(
  source: SettingSource | 'plugin',
  dir: 'skills' | 'commands',
): string {
  // Returns ~/.claude/skills/ or ~/.claude/commands/ or plugin path
}

// Loads .md files with frontmatter:
// name: Skill Name
// description: What it does
// aliases: [alias1, alias2]
// tools: [read_file, bash_shell]
// ---
// Prompt content here
```

### Data Flow
1. At startup: registerBundledSkill called for each internal skill
2. loadSkillsDir scans skill directories (.claude/skills/, plugins, managed)
3. Each .md file parsed: frontmatter → metadata, body → prompt template
4. Skills merged into global Command[] registry
5. User invokes skill via slash command (/skill-name args)
6. getPromptForCommand called with args + context
7. Model receives prompt in system/user message

### Interactions
- **Commands**: Skills are Command type with 'prompt' action
- **Frontmatter Parser**: Parses YAML frontmatter for metadata
- **MCP**: MCP tools can be adapted to skills via mcpSkillBuilders
- **Model Invocation**: Skills can disable model with disableModelInvocation flag
- **Hooks**: Skills can specify HooksSettings for model behavior

### Key Algorithms/Mechanisms
- **Frontmatter Parsing**: YAML frontmatter extraction; supports boolean, array, object fields
- **Reference Files**: bundled skills with files key extracted to disk on first invocation, memoized promise prevents races
- **Gitignore Filtering**: Disk skills filtered against .gitignore patterns
- **Token Estimation**: Skill prompts token-counted to avoid exceeding limits
- **Effort Levels**: Skills can specify effort (debug/moderate/extended) influencing model behavior

---

## 6. TASKS MODULE (Background Task Management)

### Directory Structure
**12 files across 5 subdirectories**:
- `DreamTask/`: DreamTask.ts (async test task)
- `InProcessTeammateTask/`: types.ts (agent teammate management)
- `LocalAgentTask/`: LocalAgentTask.ts (local agent invocation)
- `LocalShellTask/`: guards.ts, killShellTasks.ts (bash task type guards)
- `RemoteAgentTask/`: RemoteAgentTask.ts (remote agent invocation)
- Root: types.ts (task union type), pillLabel.ts (task indicator pill), stopTask.ts (kill task), LocalMainSessionTask.ts

### Purpose
Tasks represent background/foreground work: shell commands, agent invocations, teammates, MCP monitoring. The module defines task state types, status transitions, UI indicators, and lifecycle (spawn/kill). Integrates with state module for persistence and Ink for visual feedback.

### Key Classes/Functions
1. **types.ts** - TaskState union: LocalShellTaskState | LocalAgentTaskState | RemoteAgentTaskState | DreamTaskState | etc.
2. **LocalShellTask/guards.ts** - isLocalShellTask type guard, BashTaskKind ('bash' | 'monitor')
3. **stopTask.ts** - killShellTasks, stopTask entry points
4. **pillLabel.ts** - getPillLabel(task) → visual indicator text
5. **LocalMainSessionTask.ts** - Main session REPL task state
6. **DreamTask/DreamTask.ts** - Test task (async mock)

### Representative Code Snippets

**Task Type Union (types.ts)**:
```typescript
export type TaskState =
  | LocalShellTaskState
  | LocalAgentTaskState
  | RemoteAgentTaskState
  | InProcessTeammateTaskState
  | LocalWorkflowTaskState
  | MonitorMcpTaskState
  | DreamTaskState

export function isBackgroundTask(task: TaskState): task is BackgroundTaskState {
  if (task.status !== 'running' && task.status !== 'pending') {
    return false
  }
  if ('isBackgrounded' in task && task.isBackgrounded === false) {
    return false
  }
  return true
}
```

**Shell Task State (LocalShellTask/guards.ts)**:
```typescript
export type LocalShellTaskState = TaskStateBase & {
  type: 'local_bash'
  command: string
  result?: {
    code: number
    interrupted: boolean
  }
  shellCommand: ShellCommand | null
  lastReportedTotalLines: number
  isBackgrounded: boolean
  agentId?: AgentId
  kind?: BashTaskKind // 'bash' | 'monitor'
}

export function isLocalShellTask(task: unknown): task is LocalShellTaskState {
  return (
    typeof task === 'object' &&
    task !== null &&
    'type' in task &&
    task.type === 'local_bash'
  )
}
```

### Data Flow
1. User runs bash command → createLocalShellTask(command) → add to AppState.tasks
2. Task status: pending → running → completed (with exit code/signal)
3. Task output streamed to TaskOutput (held separately, not in task state)
4. Task backgrounded when user selects other work
5. stopTask / killShellTasks called on exit or explicit kill
6. Task persisted to session history if complete

### Interactions
- **State**: Tasks stored in AppState.tasks array
- **Ink**: Tasks rendered in status bar (pill indicator)
- **Shell**: ShellCommand executes subprocess
- **Agent**: LocalAgentTask invokes agent, tracks subprocess
- **UI**: Task details modal shows output, controls stop/bg

### Key Algorithms/Mechanisms
- **Type Guards**: isLocalShellTask, isBackgroundTask for type-safe task filtering
- **Status Tracking**: status field tracks lifecycle (pending/running/completed/failed)
- **Background Tracking**: isBackgrounded flag; foreground tasks (false) not counted as background
- **Activity Ring Buffer**: lastReportedTotalLines for delta computation
- **Cleanup**: unregisterCleanup callback, cleanupTimeoutId for proper process termination

---

## 7. ENTRYPOINTS MODULE (Application Entry Points)

### Directory Structure
**8 files**: agentSdkTypes.ts, cli.tsx, init.ts, mcp.ts, sandboxTypes.ts, sdk/

### Purpose
Entrypoints define the various ways the application starts: CLI REPL, MCP server, agent SDK runtime, sandbox isolated execution. Each exposes different capabilities based on context (local dev, remote agent, MCP consumer).

### Key Classes/Functions
1. **init.ts** (80+ lines) - init() async: memoized startup: configs, env vars, OAuth, telemetry, plugin loading
2. **cli.tsx** - CLI entry point: runs interactive REPL loop
3. **mcp.ts** - MCP server entry point: stdio transport, tool list/call handlers
4. **agentSdkTypes.ts** - SDK types: SDKMessage, SDKControlRequest, SDKControlResponse
5. **sandboxTypes.ts** - Sandbox execution types
6. **sdk/** - SDK schemas for control flow

### Representative Code Snippets

**Init Function (init.ts)**:
```typescript
export const init = memoize(async (): Promise<void> => {
  const initStartTime = Date.now()
  
  // 1. Enable configs (validation + parsing)
  enableConfigs()
  
  // 2. Apply safe env vars before trust dialog
  applySafeConfigEnvironmentVariables()
  
  // 3. Apply CA certs early (before TLS handshakes)
  applyExtraCACertsFromConfig()
  
  // 4. Detect repository
  detectCurrentRepository()
  
  // 5. Initialize telemetry
  // ... policy limits, managed settings, OAuth, telemetry
  
  // 6. Load plugins
  // ... plugin discovery + registration
})
```

**MCP Server (mcp.ts)**:
```typescript
export async function startMCPServer(
  cwd: string,
  debug: boolean,
  verbose: boolean,
): Promise<void> {
  const server = new Server({
    name: 'claude/tengu',
    version: MACRO.VERSION,
  }, {
    capabilities: {
      tools: {}
    }
  })
  
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    const tools = getTools(getEmptyToolPermissionContext())
    // Convert internal Tool schema to MCP Tool schema
  })
  
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    // Execute tool, return result
  })
}
```

**Agent SDK Types (agentSdkTypes.ts)**:
```typescript
export type SDKMessage =
  | { type: 'user_message'; text: string; ... }
  | { type: 'assistant_message'; text: string; ... }
  | { type: 'tool_use'; ... }
  | { type: 'tool_result'; ... }
  | { type: 'control_request'; ... }
  | { type: 'control_response'; ... }
```

### Data Flow
1. Process start → entrypoint (cli, mcp, or agent SDK harness)
2. init() called (memoized, safe to call multiple times)
3. Startup validation: configs, env, trust, OAuth
4. Plugin discovery + registration
5. Command/skill/tool loading
6. UI initialization (for CLI: Ink root component, for MCP: stdio transport)
7. Main loop: REPL (CLI) / message polling (agent) / stdio listening (MCP)

### Interactions
- **init()**: Called from all entrypoints before main loop
- **Plugins**: Loaded in init → register commands/skills/tools
- **Tools**: getTools() called by MCP and REPL
- **Bridge**: Remote control entrypoint initializes bridge
- **Analytics**: init logs telemetry startup
- **Config**: Settings loaded during init phase

### Key Algorithms/Mechanisms
- **Memoized Init**: init() wrapped with memoize so multiple calls are no-op (reuse results)
- **Staged Startup**: Safe env vars → trust → full env vars → telemetry (controls when sensitive data loaded)
- **Plugin Discovery**: Scans plugin directories; loads dynamically imported modules
- **Schema Validation**: Configs parsed with Zod; errors trigger validation UI
- **Feature Flags**: growthbook gates control feature availability

---

## CROSS-MODULE INTERACTIONS

### Architecture Summary Diagram
```
┌─────────────────────────────────────────────────────┐
│              ENTRYPOINTS (init, cli, mcp)           │
└──────────────┬──────────────────────────────────────┘
               │
        ┌──────┴────────┐
        │               │
    ┌───▼───┐      ┌────▼────┐
    │ INK   │      │  BRIDGE  │
    │(UI)   │      │(Remote)  │
    └───┬───┘      └────┬─────┘
        │               │
    ┌───┴───────────────┴─────┐
    │      STATE MODULE       │
    │  (AppState + Store)     │
    └───┬───────────────┬─────┘
        │               │
    ┌───▼────┐  ┌──────▼──────┐
    │CONTEXT │  │  TASKS      │
    │(async) │  │(background) │
    └────────┘  └─────────────┘
        ▲            ▲
        │            │
    ┌───┴────────────┴────┐
    │  SKILLS/COMMANDS    │
    │  (Model guidance)   │
    └─────────────────────┘
```

### Key Data Flows
1. **Rendering**: React render → reconciler → DOM mutation → markDirty → next frame renders dirty subtrees
2. **State Updates**: setState(updater) → Store updates → listeners fire → React re-render via useSyncExternalStore
3. **Async Dispatch**: useMailbox → Mailbox.send() → queued → processQueue → setState
4. **Task Lifecycle**: Command execution → createLocalShellTask → setState → Ink renders pill → output streams → completion
5. **Remote Control**: Bridge polls work → spawns session → WebSocket ingress → forwards messages → state updates → Ink renders

### Module Dependencies
- **INK** depends on: layout (Yoga), styles, terminal
- **BRIDGE** depends on: types, API client (axios), work secret decoding
- **STATE** depends on: Store (generic), React Context, Mailbox
- **CONTEXT** depends on: React, AppState, utils (mailbox, stats)
- **SKILLS** depends on: frontmatter parser, token estimation, MCP adapters
- **TASKS** depends on: type guards, ShellCommand, AppState
- **ENTRYPOINTS** depends on: all modules (initialization orchestrator)

---

## SUMMARY

This codebase implements a **terminal-based AI assistant with remote control capabilities**:

- **INK**: High-performance React terminal renderer with double-buffering, layout engine, efficient diff-based output
- **BRIDGE**: Local daemon for remote session management (polling backend, spawning subprocesses, permission callbacks)
- **STATE**: Global immutable state store with subscriber pattern for UI reactivity
- **CONTEXT**: React context providers for cross-cutting async/metrics concerns
- **SKILLS**: Pluggable domain-specific prompt templates with bundled, disk-based, plugin, and MCP sources
- **TASKS**: Background task tracking (shell, agent, teammate, MCP monitoring) with kill/lifecycle management
- **ENTRYPOINTS**: Initialization orchestrator supporting CLI, MCP server, and agent SDK modes

The architecture prioritizes **performance** (blit optimization, dirty tracking), **composability** (React components, context providers), and **flexibility** (multiple entrypoints, skill sources, task types).