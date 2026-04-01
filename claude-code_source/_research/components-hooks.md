Agent completed. agent_id: research-components-hooks, agent_type: explore, status: completed, description: Research components & hooks, elapsed: 232s, total_turns: 0, duration: 118s

Perfect! Now I have enough information to compile a comprehensive report. Let me create the final analysis:

---

# COMPREHENSIVE SOURCE CODE ANALYSIS
## Components & Hooks Directories

### EXECUTIVE SUMMARY

This is a **React-based Terminal UI application** (Claude Code in terminal) featuring an interactive REPL, tool permission system, voice mode, remote control bridge, and multi-agent coordination. The architecture uses:

- **React + Ink.js** for terminal rendering
- **Hooks-heavy architecture** for state management and side effects
- **External store pattern** (useSyncExternalStore) for global state
- **Comprehensive permission system** with CLI-interactive dialogs
- **Bridge mode** for remote session control
- **Multi-modal features**: text input, voice input, typeahead suggestions, keybindings

---

## PART 1: COMPONENTS DIRECTORY

### Purpose
Renders all UI elements in the terminal via Ink.js (React for terminals). Organized by feature domain with centralized design system.

### Directory Structure
```
src/components/
├── design-system/          (16 files) - Base UI primitives
├── permissions/            (25+ files) - Tool permission dialogs  
├── PromptInput/            - Text input handling
├── LogoV2/                 - Welcome/onboarding screens
├── agents/                 - Agent coordination UI
├── messages/               - Message rendering
├── shell/                  - Terminal shell UI
├── Settings/               - Configuration UI
├── HighlightedCode/        - Syntax highlighting
├── diff/                   - Diff visualization
├── tasks/                  - Task management UI
├── dialog launchers/       - Dialog orchestration
└── [40+ direct components] - Feature-specific views
```

### Key Classes/Functions - Components (15 entries)

1. **App.tsx** - Top-level wrapper providing FpsMetrics, Stats, AppState contexts
   - Path: `src/components/App.tsx`
   - Signature: `export function App({ getFpsMetrics, stats, initialState, children })`

2. **PermissionDialog** - Styled container for permission request UI with borders/colors
   - Path: `src/components/permissions/PermissionDialog.tsx`
   - Signature: `export function PermissionDialog({ title, subtitle, color?, workerBadge?, children })`

3. **Dialog (Design System)** - Generic modal dialog with keybinding support (Esc/Ctrl+C/D)
   - Path: `src/components/design-system/Dialog.tsx`
   - Signature: `export function Dialog({ title, subtitle, children, onCancel, color?, isCancelActive? })`

4. **BridgeDialog** - Remote control bridge connection UI with QR code display
   - Path: `src/components/BridgeDialog.tsx`
   - Size: 400 lines
   - Features: Session URL, QR code generation, status indicators

5. **ContextVisualization** - Shows context collapse status, token budget, source grouping
   - Path: `src/components/ContextVisualization.tsx`
   - Size: 76KB (largest component)
   - Features: Context strategy display, collapse statistics, source filtering

6. **PermissionRequest** - Wrapper dispatching to specific permission types
   - Path: `src/components/permissions/PermissionRequest.tsx`
   - Signature: `export function PermissionRequest(props: PermissionRequestProps)`

7. **CoordinatorAgentStatus** - Displays swarm coordination status and tasks
   - Path: `src/components/CoordinatorAgentStatus.tsx`
   - Exports: `getVisibleAgentTasks()`, `CoordinatorTaskPanel()`, `useCoordinatorTaskCount()`

8. **FuzzyPicker (Design System)** - Searchable list selection with typeahead
   - Path: `src/components/design-system/FuzzyPicker.tsx`
   - Size: 40KB
   - Features: Filtering, keyboard navigation, item highlighting

9. **Tabs (Design System)** - Tab navigation component with keyboard selection
   - Path: `src/components/design-system/Tabs.tsx`
   - Size: 41KB

10. **ThemeProvider (Design System)** - Applies theme colors to all components
    - Path: `src/components/design-system/ThemeProvider.tsx`
    - Signature: `export function ThemeProvider({ children, theme })`

11. **BaseTextInput** - Core text input with Vim mode, autocompletion, history
    - Path: `src/components/BaseTextInput.tsx`
    - Size: 19KB
    - Features: Multi-line input, cursor management, paste handling

12. **PermissionExplanation** - Renders detailed tool permission context and rules
    - Path: `src/components/permissions/PermissionExplanation.tsx`

13. **AgentProgressLine** - Shows agent execution progress with spinner
    - Path: `src/components/AgentProgressLine.tsx`
    - Size: 14KB

14. **AutoUpdater** - Handles CLI auto-updates with user prompts
    - Path: `src/components/AutoUpdater.tsx`
    - Size: 31KB

15. **ConsoleOAuthFlow** - OAuth authentication flow UI for bridges
    - Path: `src/components/ConsoleOAuthFlow.tsx`
    - Size: 630 lines

### Representative Code Snippets - Components

**Snippet 1: App.tsx - Context Nesting Pattern**
```tsx
export function App({
  getFpsMetrics,
  stats,
  initialState,
  children,
}: Props): React.ReactNode {
  return (
    <FpsMetricsProvider getFpsMetrics={getFpsMetrics}>
      <StatsProvider store={stats}>
        <AppStateProvider
          initialState={initialState}
          onChangeAppState={onChangeAppState}
        >
          {children}
        </AppStateProvider>
      </StatsProvider>
    </FpsMetricsProvider>
  )
}
```

**Snippet 2: PermissionDialog - Styled Box Layout**
```tsx
export function PermissionDialog({
  title,
  subtitle,
  color = 'permission',
  workerBadge,
  children,
}: Props): React.ReactNode {
  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={color}
      borderLeft={false}
      borderRight={false}
      borderBottom={false}
      marginTop={1}
    >
      <Box paddingX={1} flexDirection="column">
        <Box justifyContent="space-between">
          <PermissionRequestTitle {...} />
          {titleRight}
        </Box>
      </Box>
      <Box flexDirection="column" paddingX={innerPaddingX}>
        {children}
      </Box>
    </Box>
  )
}
```

**Snippet 3: Dialog - Ctrl+C/D Double-Press Exit Handling**
```tsx
export function Dialog({
  title,
  subtitle,
  isCancelActive = true,
  inputGuide,
}: DialogProps): React.ReactNode {
  const exitState = useExitOnCtrlCDWithKeybindings(
    undefined,
    undefined,
    isCancelActive
  );
  
  useKeybinding("confirm:no", onCancel, { 
    context: "Confirmation", 
    isActive: isCancelActive 
  });

  const defaultInputGuide = exitState.pending 
    ? <Text>Press {exitState.keyName} again to exit</Text>
    : <Byline><KeyboardShortcutHint.../></Byline>;
    
  return inputGuide ? inputGuide(exitState) : defaultInputGuide;
}
```

**Snippet 4: ContextVisualization - Grouped Display**
```tsx
function groupBySource<T extends { source: SettingSource; tokens: number }>(
  items: T[]
): Map<string, T[]> {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const key = getSourceDisplayName(item.source);
    const existing = groups.get(key) || [];
    existing.push(item);
    groups.set(key, existing);
  }
  // Sort each group by tokens descending
  for (const [key, group] of groups.entries()) {
    groups.set(key, group.sort((a, b) => b.tokens - a.tokens));
  }
  return orderedGroups; // Order: Project > User > Managed > Plugin > Built-in
}
```

### Component Hierarchy & Major UI Sections

```
App (root wrapper)
 ├─ FpsMetricsProvider
 ├─ StatsProvider
 └─ AppStateProvider
     ├─ REPL Screen
     │  ├─ PromptInput (BaseTextInput + PromptInputFooterSuggestions)
     │  ├─ ScrollBox (virtual scrolling with useVirtualScroll)
     │  └─ Message rendering
     ├─ Dialog overlays
     │  ├─ PermissionDialog
     │  ├─ BridgeDialog
     │  └─ Task/Settings dialogs
     ├─ Typeahead suggestions
     └─ Notifications/toasts
```

### Data Flow - Components

1. **AppState → Components**: Central state store using AppStateProvider context
2. **Events → Handlers**: Keybindings via useKeybinding() → handlers
3. **External Stores**: useSyncExternalStore for command queue, settings changes
4. **Props Drilling**: Theme colors passed down via design system components
5. **Message Rendering**: Message[] array → virtual scroll → PermissionDialog on user interaction

### Interactions - Components

- **Components ↔ AppState**: useAppState() / useSetAppState() read/write app state
- **Components ↔ Hooks**: Dialog uses useExitOnCtrlCDWithKeybindings(), useTypeahead()
- **Components ↔ Ink.js**: Box, Text, useInput for terminal rendering
- **Components ↔ Keybindings**: useKeybinding() for action binding
- **Design System ↔ Theme**: ThemeProvider supplies color schemes to all components

---

## PART 2: HOOKS DIRECTORY

### Purpose
React hooks implementing complex stateful logic: terminal I/O, typeahead, permissions, voice, bridge synchronization, virtual scrolling, keybindings, notifications.

### Directory Structure
```
src/hooks/
├── toolPermission/
│  ├─ PermissionContext.ts       - Permission decision context
│  ├─ permissionLogging.ts       - Permission audit logging
│  └─ handlers/
│     ├─ coordinatorHandler.ts   - Swarm coordinator approval
│     ├─ interactiveHandler.ts   - User dialog handling
│     └─ swarmWorkerHandler.ts   - Worker agent approval
├── notifs/
│  ├─ useFastModeNotification.tsx
│  ├─ useLspInitializationNotification.tsx
│  ├─ useRateLimitWarningNotification.tsx
│  ├─ useModelMigrationNotifications.tsx
│  └─ [5+ notification hooks]
├── [90+ individual hook files]
```

### Key Hooks - 16 Representative Entries

1. **useCommandQueue** - Subscribe to unified command queue via external store
   - Path: `src/hooks/useCommandQueue.ts`
   - Signature: `export function useCommandQueue(): readonly QueuedCommand[]`
   - Uses: useSyncExternalStore with getCommandQueueSnapshot/subscribeToCommandQueue

2. **useGlobalKeybindings** - Register handlers for Ctrl+T (todos), Ctrl+O (transcript), Ctrl+E (show all)
   - Path: `src/hooks/useGlobalKeybindings.tsx`
   - Size: 31KB
   - Features: Two-way prompt ↔ transcript toggle, expanded view cycling

3. **useExitOnCtrlCD** - Double-press exit confirmation for Ctrl+C/Ctrl+D
   - Path: `src/hooks/useExitOnCtrlCD.ts`
   - Size: 3.2KB
   - Signature: `export function useExitOnCtrlCD(useKeybindingsHook, onInterrupt?, onExit?, isActive?): ExitState`
   - Uses: useDoublePress for confirmation timing

4. **useAssistantHistory** - Lazy-load remote session history on scroll-up
   - Path: `src/hooks/useAssistantHistory.ts`
   - Size: 251 lines
   - Features: Scroll anchoring, viewport filling, sentinel messages for "loading..."

5. **useReplBridge** - Initialize and maintain always-on bridge connection
   - Path: `src/hooks/useReplBridge.tsx`
   - Size: 115KB (largest hook)
   - Features: Background sync, failure retry logic (max 3 consecutive failures), outbound-only mode
   - Manages: Initial message sync, WebSocket connection state, QR code display

6. **useCanUseTool** - Tool permission decision engine
   - Path: `src/hooks/useCanUseTool.tsx`
   - Size: 40KB
   - Features: Config-based auto-allow/deny, user prompts, classifier predictions, swarm/coordinator approval paths

7. **useTypeahead** - Unified suggestion engine for command/file/shell history
   - Path: `src/hooks/useTypeahead.tsx`
   - Size: 212KB (second largest)
   - Features: Command completion, file path completion, shell history, session resumption suggestions
   - Regex patterns: AT_TOKEN_HEAD_RE, PATH_CHAR_HEAD_RE, HAS_AT_SYMBOL_RE

8. **useVirtualScroll** - Efficient rendering for large message lists
   - Path: `src/hooks/useVirtualScroll.ts`
   - Size: 35KB
   - Constants: DEFAULT_ESTIMATE=3, OVERSCAN_ROWS=80, SCROLL_QUANTUM=40
   - Returns: {range: [start, end), topSpacer, bottomSpacer, measureRef, spacerRef}

9. **useVoiceIntegration** - Unified voice input handler
   - Path: `src/hooks/useVoiceIntegration.tsx`
   - Size: 99KB
   - Features: Key hold detection, warmup feedback, transcript handling
   - Thresholds: HOLD_THRESHOLD=5, WARMUP_THRESHOLD=2, RAPID_KEY_GAP_MS=120

10. **useVoice** - Core voice recording and transcription
    - Path: `src/hooks/useVoice.ts`
    - Size: 45KB
    - Features: microphone input, stream-to-text transcription

11. **useArrowKeyHistory** - Navigate message history with arrow keys
    - Path: `src/hooks/useArrowKeyHistory.tsx`
    - Size: 34KB
    - Features: Up/down navigation, filtered history search

12. **useTextInput** - Core terminal text input handling
    - Path: `src/hooks/useTextInput.ts`
    - Size: 17KB
    - Features: Cursor position tracking, selection, paste, undo/redo

13. **useInboxPoller** - Poll for new system notifications/messages
    - Path: `src/hooks/useInboxPoller.ts`
    - Size: 34KB
    - Features: Periodic polling, notification deduplication

14. **useSwarmPermissionPoller** - Poll coordinator for tool permission decisions
    - Path: `src/hooks/useSwarmPermissionPoller.ts`
    - Size: 9.6KB
    - Features: Async polling, abort signal handling

15. **useRemoteSession** - Manage remote session lifecycle
    - Path: `src/hooks/useRemoteSession.ts`
    - Size: 23KB
    - Features: SSH tunneling, session recovery

16. **useTasksV2** - Task list state and filtering
    - Path: `src/hooks/useTasksV2.ts`
    - Size: 8.8KB
    - Features: Task completion tracking, filtering by status

### Permission-Related Hooks - Tool Permission System

**PermissionContext (src/hooks/toolPermission/PermissionContext.ts)**
- 382 lines
- Exports: `createPermissionContext()`, `createPermissionQueueOps()`, `createResolveOnce()`
- Core type: `PermissionContext` with methods:
  - `resolveIfAborted()` - Check abort signal
  - `persistPermissions()` - Save user decisions
  - `buildAllow/buildDeny()` - Create decisions
  - `tryClassifier()` - Run bash command classifier
  - `runHooks()` - Execute permission request hooks
  - `handleUserAllow/handleHookAllow()` - Process approval sources

**Permission Handlers**
- `coordinatorHandler.ts` - Swarm agent coordinator approval flow
- `interactiveHandler.ts` - Interactive user dialog with text input
- `swarmWorkerHandler.ts` - Worker agent approval requests

### Representative Code Snippets - Hooks

**Snippet 1: useCommandQueue - External Store Pattern**
```ts
export function useCommandQueue(): readonly QueuedCommand[] {
  return useSyncExternalStore(
    subscribeToCommandQueue,
    getCommandQueueSnapshot
  )
}
// Usage: const commands = useCommandQueue() // re-renders only on mutation
```

**Snippet 2: useExitOnCtrlCD - Double-Press Confirmation**
```tsx
export function useExitOnCtrlCD(
  useKeybindingsHook: UseKeybindingsHook,
  onInterrupt?: () => boolean,  // Return true if handled
  onExit?: () => void,
  isActive = true,
): ExitState {
  const [exitState, setExitState] = useState<ExitState>({
    pending: false,
    keyName: null,
  });

  const handleCtrlCDoublePress = useDoublePress(
    (pending) => setExitState({ pending, keyName: 'Ctrl-C' }),
    exitFn,
  );

  const handleInterrupt = useCallback(() => {
    if (onInterrupt?.()) return; // Feature handled it
    handleCtrlCDoublePress(); // Show "Press again to exit"
  }, [handleCtrlCDoublePress, onInterrupt]);

  useKeybindingsHook(
    { 'app:interrupt': handleInterrupt, 'app:exit': handleExit },
    { context: 'Global', isActive }
  );

  return exitState;
}
```

**Snippet 3: useAssistantHistory - Scroll Anchoring & Lazy Load**
```tsx
const anchorRef = useRef<{ beforeHeight: number; count: number } | null>(null);

const prepend = useCallback(
  (page: HistoryPage, isInitial: boolean) => {
    const msgs = pageToMessages(page);
    cursorRef.current = page.hasMore ? page.firstId : null;

    // Snapshot scroll height BEFORE setMessages
    if (!isInitial) {
      anchorRef.current = scrollRef.current
        ? { beforeHeight: scrollRef.current.getFreshScrollHeight(), count: msgs.length }
        : null;
    }

    setMessages((prev) => {
      const base = prev[0]?.uuid === sentinelUuidRef.current ? prev.slice(1) : prev;
      return sentinel ? [sentinel, ...msgs, ...base] : [...msgs, ...base];
    });
  },
  [setMessages],
);

// Compensate scroll position in layout effect
useLayoutEffect(() => {
  const anchor = anchorRef.current;
  if (anchor === null) return;
  const delta = scrollRef.current.getFreshScrollHeight() - anchor.beforeHeight;
  if (delta > 0) scrollRef.current.scrollBy(delta); // Keep viewport fixed
  onPrepend?.(anchor.count, delta);
}, []); // Runs every render; cheap no-op when null
```

**Snippet 4: useCanUseTool - Permission Decision Flow**
```tsx
export type CanUseToolFn = (
  tool: ToolType,
  input: Record<string, unknown>,
  toolUseContext: ToolUseContext,
  assistantMessage: AssistantMessage,
  toolUseID: string,
  forceDecision?: PermissionDecision<Input>,
) => Promise<PermissionDecision<Input>>;

// Decision paths:
// 1. Config-based: Auto-allow/deny (classifier, rules)
// 2. Classifier: Bash command safety check
// 3. Coordinator: Swarm multi-agent approval
// 4. Interactive: User dialog confirmation
// 5. Hooks: Custom plugin permission logic

const decisionPromise = forceDecision !== undefined
  ? Promise.resolve(forceDecision)
  : hasPermissionsToUseTool(tool, input, toolUseContext, assistantMessage, toolUseID);

return decisionPromise.then(async (result) => {
  if (result.behavior === "allow") {
    ctx.logDecision({ decision: "accept", source: "config" });
    resolve(ctx.buildAllow(result.updatedInput ?? input, { decisionReason: result.decisionReason }));
    return;
  }
  // ... switch on result.behavior ("deny", "ask")
});
```

**Snippet 5: useTypeahead - Unified Suggestion Generation**
```tsx
// Unicode-aware tokenization (handles CJK, Cyrillic, combining marks)
const AT_TOKEN_HEAD_RE = /^@[\p{L}\p{N}\p{M}_\-./\\()[\]~:]*/u;
const PATH_CHAR_HEAD_RE = /^[\p{L}\p{N}\p{M}_\-./\\()[\]~:]+/u;
const TOKEN_WITH_AT_RE = /(@[\p{L}\p{N}\p{M}_\-./\\()[\]~:]*|...)$/u;
const HAS_AT_SYMBOL_RE = /(^|\s)@([\p{L}\p{N}\p{M}_\-./\\()[\]~:]*|"[^"]*"?)$/u;

// Suggestion priorities: command > file > shell history > session resume
function getPreservedSelection(
  prevSuggestions: SuggestionItem[],
  prevSelection: number,
  newSuggestions: SuggestionItem[]
): number {
  if (newSuggestions.length === 0) return -1;
  if (prevSelection < 0) return 0;
  const prevSelectedItem = prevSuggestions[prevSelection];
  const newIndex = newSuggestions.findIndex(item => item.id === prevSelectedItem.id);
  return newIndex >= 0 ? newIndex : 0;
}
```

**Snippet 6: useVirtualScroll - Item Range Calculation**
```tsx
const DEFAULT_ESTIMATE = 3; // rows per item
const OVERSCAN_ROWS = 80;  // buffer above/below viewport
const SCROLL_QUANTUM = OVERSCAN_ROWS >> 1; // Quantize scrollTop to reduce re-renders
const PESSIMISTIC_HEIGHT = 1; // Assume 1-row min for coverage
const MAX_MOUNTED_ITEMS = 300;
const SLIDE_STEP = 25; // Max new items per commit

export type VirtualScrollResult = {
  range: readonly [number, number]; // [startIndex, endIndex) slice
  topSpacer: number;               // Rows of whitespace before first item
  bottomSpacer: number;            // Rows of whitespace after last item
  measureRef: (key: string) => (el: DOMElement | null) => void;
  spacerRef: RefObject<DOMElement | null>;
};
```

### Key Algorithms/Mechanisms - Hooks

**Algorithm 1: Virtual Scrolling (useVirtualScroll)**
- Maintains item height cache (measured via Yoga after render)
- Bins scrollTop by SCROLL_QUANTUM to batch updates
- Mounts items in SLIDE_STEP increments to bound sync block time
- Returns [startIndex, endIndex) half-open slice + spacer heights

**Algorithm 2: Scroll Anchoring (useAssistantHistory)**
- Snapshot height pre-mutation
- Prepend items via setMessages
- In useLayoutEffect, compare new height vs. snapshot
- Adjust scrollTop to keep viewport at same logical position

**Algorithm 3: Permission Decision Tree (useCanUseTool → createPermissionContext)**
1. Check abort signal
2. Attempt config-based decision (auto-allow/deny rules)
3. If "ask": try coordinator (swarm multi-agent approval)
4. If coordinator pending: try classifier (bash safety check)
5. If classifier allows: accept
6. If classifier blocks or no classifier: show interactive dialog
7. On user accept: persist permission update; build ALLOW decision
8. On user reject: log; build DENY decision

**Algorithm 4: Command/File Suggestions (useTypeahead)**
- Tokenize input by @-prefix or file path patterns
- Match @-token to commands, file paths, agents, sessions
- Filter by prefix match + fuzzy matching
- Score by recency, popularity, match position
- Deduplicate and order: commands > paths > history > resume
- Debounce on keystroke to avoid thrashing

**Algorithm 5: Voice Hold Detection (useVoiceIntegration)**
- Track keypress events in rapid succession
- If > HOLD_THRESHOLD (5) rapid presses in RAPID_KEY_GAP_MS (120ms): hold = true
- If WARMUP_THRESHOLD (2) presses: show warmup feedback
- Once held, pass to useVoice for recording

**Algorithm 6: Typeahead Selection Preservation (useTypeahead)**
- On suggestion list change, find previously-selected item by ID
- If found in new list: keep selection at new index
- Else default to index 0
- Ensures arrow-key position doesn't "jump" unexpectedly

### Data Flow - Hooks

1. **Input Events** → useInput/useKeybinding → handlers update state
2. **State Changes** → AppState → useAppState (memoized selectors)
3. **Async Operations** → useEffect with cleanup
4. **External Stores** → useSyncExternalStore (command queue, settings)
5. **Permissions** → useCanUseTool → createPermissionContext → decision
6. **Messages** → useVirtualScroll → range → component renders items
7. **Voice** → useVoiceIntegration → transcript → onTranscript callback

### Interactions - Hooks

- **useCommandQueue ↔ messageQueueManager**: External store subscription
- **useCanUseTool ↔ permissionLogging**: Analytics event emission
- **useAssistantHistory ↔ sessionHistory API**: Fetch pages, create auth context
- **useVirtualScroll ↔ Ink ScrollBox**: Measure refs, read computedTop
- **useTypeahead ↔ fileSuggestions**: Background cache refresh, index builds
- **useReplBridge ↔ bridge/initReplBridge**: WebSocket setup, initial message flush
- **useGlobalKeybindings ↔ AppState**: Toggle expandedView, screen mode
- **useExitOnCtrlCD ↔ useDoublePress**: Confirm exit state management

---

## PART 3: COMPREHENSIVE CROSS-MODULE VIEW

### Component + Hook Collaboration Examples

**Example 1: Permission Request Flow**
```
User types command with tool
  ↓
useCanUseTool hook triggered
  ↓
createPermissionContext analyzes tool
  ↓
if auto-deny: resolve immediately
if auto-allow: resolve immediately
if ask: 
  ├─ tryClassifier (bash classifier)
  ├─ runHooks (permission request hooks)
  ├─ swarmWorker approval (if needed)
  └─ interactiveHandler (show PermissionDialog component)
  ↓
PermissionDialog component (useKeybinding for accept/reject)
  ↓
User presses 'y' or 'n'
  ↓
ctx.handleUserAllow() or ctx.logDecision()
  ↓
Resolve promise with PermissionDecision
```

**Example 2: Message Display with Virtual Scroll**
```
useReplBridge hook (backend):
  - Fetch messages, sync bridge state
  - Call setMessages([...])

AppState.messages updated
  ↓
useVirtualScroll hook (measurement):
  - Calculate visible range [start, end)
  - Mounts items in SlideStep increments
  - Returns measureRef callbacks

Message array → Component rendering:
  - Map over messages[start:end]
  - Attach measureRef to each row
  - Render topSpacer + items + bottomSpacer

ScrollBox forceRender → Ink layout → measureRef fired
  ↓
measureRef callbacks cache item heights
  ↓
Next scroll event → recalculate range → new commits
```

**Example 3: Typeahead + Keybinding Integration**
```
User types in PromptInput (BaseTextInput component)
  ↓
useTextInput hook tracks cursor position
  ↓
useTypeahead hook:
  - Debounces input parsing
  - Matches tokens (@ for agents, . for paths, etc.)
  - Queries command/file/history sources
  - Sets suggestions state (via setSuggestionsState callback)

Suggestions rendered by PromptInputFooterSuggestions component
  ↓
useKeybindings hook:
  - Up/Down arrows: navigate selectedSuggestion
  - Enter: apply suggestion via applyCommandSuggestion()
  - Esc: close suggestions

Apply suggestion:
  - Call onInputChange with new value
  - Suggestions clear
  - Cursor positioned
```

### Module Integration Map

```
Components (UI Layer)
  ├─ App (context wrappers)
  ├─ Dialog (modal container)
  ├─ PermissionDialog (permission UI)
  ├─ BridgeDialog (bridge UI)
  ├─ BaseTextInput (text input UI)
  ├─ FuzzyPicker (suggestion UI)
  └─ design-system/* (primitives)

Hooks (Logic Layer)
  ├─ useCanUseTool (permission logic)
  ├─ useVirtualScroll (scroll logic)
  ├─ useTypeahead (suggestion logic)
  ├─ useReplBridge (bridge sync)
  ├─ useGlobalKeybindings (app navigation)
  ├─ useVoiceIntegration (voice input)
  ├─ useCommandQueue (command queue)
  └─ Permission handlers
      ├─ coordinatorHandler
      ├─ interactiveHandler
      └─ swarmWorkerHandler

Contexts (State Layer)
  ├─ AppState (central state)
  ├─ PermissionContext (in hooks)
  ├─ NotificationsContext
  ├─ KeybindingContext
  └─ VoiceContext

External Systems
  ├─ messageQueueManager (command queue)
  ├─ Ink.js (terminal rendering)
  ├─ sessionHistory API
  ├─ bridge connection (WebSocket)
  ├─ tool execution engine
  └─ permission rules engine
```

---

## SUMMARY TABLE

| Category | Count | Key Pattern | Largest |
|----------|-------|-------------|---------|
| **Components** | 80+ | Feature-organized, design-system primitives | ContextVisualization (76KB) |
| **Hooks** | 90+ | Stateful logic, side effects, I/O | useReplBridge (115KB), useTypeahead (212KB) |
| **Design System** | 16 files | Box/Text/Dialog/Tabs/FuzzyPicker primitives | - |
| **Permission Components** | 25+ | Dialog layers, specialized request types | PermissionDialog, PermissionRequest |
| **Permission Hooks** | 3 handlers + context | createPermissionContext, 3 handler types | PermissionContext.ts (382 lines) |

---

**Report Generated**: Complete analysis of React + Hooks-based terminal UI architecture with emphasis on permission system, virtual scrolling, voice integration, and bridge synchronization.