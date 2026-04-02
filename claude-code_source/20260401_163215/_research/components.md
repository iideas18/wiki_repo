Agent completed. agent_id: research-components, agent_type: explore, status: completed, description: Research components module, elapsed: 160s, total_turns: 0, duration: 138s

Perfect! Now I have comprehensive information. Let me compile the research report:

---

# **COMPREHENSIVE RESEARCH REPORT: CLAUDE CODE COMPONENTS MODULE**

## **1. PURPOSE**

The components module provides a complete terminal UI framework built on **Ink** (React for terminal rendering). It implements the interactive REPL interface for Claude Code, including message rendering (user input/assistant output), modal dialogs, tool permission requests, syntax highlighting, theming, and comprehensive state management. The system handles real-time streaming, virtual scrolling for large transcripts, keyboard navigation, and accessibility features while maintaining ~150K+ writes per frame optimization through memoization and blit caching.

---

## **2. SUB-MODULE DIRECTORY LISTING (31 subdirectories)**

| Directory | File Count | Purpose |
|-----------|-----------|---------|
| **messages** | 33 | Message renderers for all block types (user text, assistant text, tool use, thinking, attachments, system messages, bash I/O) |
| **PromptInput** | 21 | Primary input handler with multi-modal support (normal, vim, voice, history search, typeahead suggestions) |
| **design-system** | 16 | Core terminal UI primitives (Dialog, Tabs, Pane, FuzzyPicker, ProgressBar, ThemedText, ThemeProvider) |
| **LogoV2** | 15 | Animated branding and status feeds (logo, clawd mascot, notices, upsells) |
| **permissions** | 15 | Tool permission dialogs (bash, file edit, web fetch, workflow, etc.) |
| **tasks** | 12 | Background/parallel task management (detail dialogs, progress tracking) |
| **mcp** | 12 | MCP server connections and approvals |
| **Spinner** | 12 | Loading/progress spinners with animations |
| **agents** | 13 | Agent task status, coordinator tracking |
| **CustomSelect** | 10 | Dropdown/menu selection component |
| **FeedbackSurvey** | 9 | In-app survey collection |
| **diff** | 3 | Diff/patch rendering components |
| **HelpV2** | 3 | Help system UI |
| **ui** | 3 | Tree select, ordered lists |
| **Settings** | 4 | Configuration dialogs |
| **shell** | 4 | Shell output expansion, progress display |
| **wizard** | 5 | Multi-step setup flows |
| **sandbox** | 5 | Sandbox environment interactions |
| **memory** | 2 | Memory context indicators |
| **teams** | 2 | Team/swarm management |
| **hooks** | 6 | Hook mode dialogs |
| **grove** | 1 | Code grove integration |
| **skills** | 1 | Skill management |
| **ClaudeCodeHint** | 1 | Tutorial/hint popover |
| **DesktopUpsell** | 1 | Desktop app marketing |
| **HighlightedCode** | 1 | Syntax highlighting wrapper |
| **LspRecommendation** | 1 | LSP server suggestions |
| **ManagedSettingsSecurityDialog** | 2 | Security policy enforcement |
| **Passes** | 1 | Guest pass management |
| **StructuredDiff** | 2 | Structured diff viewer |
| **TrustDialog** | 2 | Trust/security decisions |

**Top-level components**: 113 .tsx/.ts files (App, Messages, Message, VirtualMessageList, FullscreenLayout, TextInput, PromptInput, etc.)

---

## **3. KEY REACT COMPONENTS (15 Core Components)**

| Component | File Path | Role |
|-----------|-----------|------|
| **App** | `App.tsx` | Root provider wrapper: memoized context tree (FpsMetrics, Stats, AppState providers) |
| **Messages** | `Messages.tsx` (833 lines) | Memoized transcript renderer: normalizes/collapses messages, applies grouping, filters for brief mode |
| **Message** | `Message.tsx` (626 lines) | Individual message renderer: routes to specialized handlers (TextMessage, ToolUseMessage, SystemMessage, etc.) |
| **PromptInput** | `PromptInput/PromptInput.tsx` (2338 lines) | Primary REPL input: handles vim/normal modes, history, suggestions, buddy notifications, inline paste |
| **VirtualMessageList** | `VirtualMessageList.tsx` | Virtual scroll container: lazy-renders messages, handles search indexing, keyboard navigation |
| **FullscreenLayout** | `FullscreenLayout.tsx` | Layout manager: scrollable area + sticky header + modal overlay + floating companion |
| **Dialog** | `design-system/Dialog.tsx` | Modal dialog: title/subtitle, keybinding handlers (Esc to cancel, Enter to confirm) |
| **Tabs** | `design-system/Tabs.tsx` | Tabbed interface: keyboard nav, fixed content height, tab index tracking |
| **FuzzyPicker** | `design-system/FuzzyPicker.tsx` | Search dropdown: async filtering, cursor nav, tab/shift-tab actions, preview pane |
| **Pane** | `design-system/Pane.tsx` | Command pane wrapper: colored top divider, padding, modal-aware rendering |
| **TextInput** | `TextInput.tsx` | Base text field: cursor rendering, voice mode waveform, animation frame support |
| **Spinner** | `Spinner.tsx` (85KB) | Loading spinner: frame-based animation, emoji rotation, custom patterns |
| **ThemeProvider** | `design-system/ThemeProvider.tsx` | Theme context: auto/dark/light modes, live terminal theme watching (OSC 11) |
| **PermissionRequest** | `permissions/PermissionRequest.tsx` | Tool permission dispatcher: routes to specialized handlers (BashPermissionRequest, FileEditPermissionRequest, etc.) |
| **ThemedText** | `design-system/ThemedText.tsx` | Color-aware text: theme color lookup, hover color context |

---

## **4. REPRESENTATIVE CODE SNIPPETS**

### **Snippet 1: App Root Provider (Memoized Context Hierarchy)**
```typescript
// App.tsx (lines 15-55)
/**
 * Top-level wrapper for interactive sessions.
 * Provides FPS metrics, stats context, and app state to the component tree.
 */
export function App(t0) {
  const $ = _c(9);
  const {
    getFpsMetrics,
    stats,
    initialState,
    children
  } = t0;
  // React compiler: memoizes each provider to prevent cascade invalidation
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

### **Snippet 2: Message Component Props Type**
```typescript
// Message.tsx (lines 32-57)
export type Props = {
  message: NormalizedUserMessage | AssistantMessage | AttachmentMessageType | SystemMessage | GroupedToolUseMessageType | CollapsedReadSearchGroupType;
  lookups: ReturnType<typeof buildMessageLookups>;
  /** Absolute width for the container Box. When provided, eliminates a wrapper Box in the caller. */
  containerWidth?: number;
  addMargin: boolean;
  tools: Tools;
  commands: Command[];
  verbose: boolean;
  inProgressToolUseIDs: Set<string>;
  progressMessagesForMessage: ProgressMessage[];
  shouldAnimate: boolean;
  shouldShowDot: boolean;
  style?: 'condensed';
  width?: number | string;
  isTranscriptMode: boolean;
  isStatic: boolean;
  onOpenRateLimitOptions?: () => void;
  isActiveCollapsedGroup?: boolean;
  isUserContinuation?: boolean;
  lastThinkingBlockId?: string | null;
  latestBashOutputUUID?: string | null;
};
```

### **Snippet 3: Dialog Component Props**
```typescript
// design-system/Dialog.tsx (lines 11-29)
type DialogProps = {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  onCancel: () => void;
  color?: keyof Theme;
  hideInputGuide?: boolean;
  hideBorder?: boolean;
  inputGuide?: (exitState: ExitState) => React.ReactNode;
  /**
   * Controls whether Dialog's built-in confirm:no (Esc/n) and app:exit/interrupt
   * (Ctrl-C/D) keybindings are active. Set to `false` while an embedded text
   * field is being edited so those keys reach the field instead of being
   * consumed by Dialog.
   */
  isCancelActive?: boolean;
};
```

### **Snippet 4: FuzzyPicker Component Props**
```typescript
// design-system/FuzzyPicker.tsx (lines 14-62)
type Props<T> = {
  title: string;
  placeholder?: string;
  initialQuery?: string;
  items: readonly T[];
  getKey: (item: T) => string;
  renderItem: (item: T, isFocused: boolean) => React.ReactNode;
  renderPreview?: (item: T) => React.ReactNode;
  previewPosition?: 'bottom' | 'right';
  visibleCount?: number;
  direction?: 'down' | 'up';
  onQueryChange: (query: string) => void;
  onSelect: (item: T) => void;
  onTab?: PickerAction<T>;
  onShiftTab?: PickerAction<T>;
  onFocus?: (item: T | undefined) => void;
  onCancel: () => void;
  emptyMessage?: string | ((query: string) => string);
  matchLabel?: string;
};
```

### **Snippet 5: PromptInput Hook Usage (Multi-Modal Input)**
```typescript
// PromptInput/PromptInput.tsx (lines 1-120)
// Demonstrates extensive hook usage for complex input handling:
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import { useCommandQueue } from 'src/hooks/useCommandQueue.js';
import { useAppState, useSetAppState } from 'src/state/AppState.js';
import { useTerminalSize } from '../../hooks/useTerminalSize.js';
import { useKeybinding, useKeybindings } from '../../keybindings/useKeybinding.js';
import { usePromptSuggestion } from '../../hooks/usePromptSuggestion.js';
import { useArrowKeyHistory } from '../../hooks/useArrowKeyHistory.js';
import { useHistorySearch } from '../../hooks/useHistorySearch.js';
import { useTypeahead } from '../../hooks/useTypeahead.js';

export default function PromptInput({ ... }: Props) {
  const [isAutoUpdating, setIsAutoUpdating] = useState(false);
  const [cursorOffset, setCursorOffset] = useState<number>(input.length);
  const [exitMessage, setExitMessage] = useState<ExitState>(...);
  const [showTeamsDialog, setShowTeamsDialog] = useState(false);
  const lastInternalInputRef = React.useRef(input);
  const trackAndSetInput = React.useCallback((value: string) => { ... }, []);
  // ... 100+ more state/ref/hook declarations
}
```

---

## **5. DATA FLOW ARCHITECTURE**

```
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION ROOT (App.tsx)               │
│   ┌────────────────────────────────────────────────────┐   │
│   │ FpsMetricsProvider (context: performance tracking) │   │
│   │ ├─ StatsProvider (context: stats/analytics)        │   │
│   │ └─ AppStateProvider (context: global UI state)     │   │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│              FULLSCREEN LAYOUT (FullscreenLayout.tsx)        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ScrollBox (virtual scroll with blit optimization)   │  │
│  │   ├─ LogoHeader (memoized, uses AppState/Settings) │  │
│  │   ├─ Messages (memoized transcript list)           │  │
│  │   ├─ VirtualMessageList (lazy render + search)     │  │
│  │   └─ Message[] (individual message renderers)      │  │
│  ├─ PromptInput (REPL prompt + suggestions + footer)   │  │
│  ├─ Modal Overlay (slash commands, dialogs, pickers)   │  │
│  └─ BottomFloat (companion speech bubble)              │  │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│                 MESSAGE RENDERING PIPELINE                  │
│  Messages.tsx normalizes/collapses/groups messages         │
│         ↓                                                   │
│  Message.tsx routes to specialized handlers:              │
│    • UserTextMessage → UserPlanMessage|UserCommandMessage │
│    • AssistantTextMessage (with API error handling)        │
│    • AssistantToolUseMessage (with progress tracking)      │
│    • AssistantThinkingMessage (collapsed/expanded)         │
│    • SystemTextMessage, AttachmentMessage, etc.            │
│         ↓                                                   │
│  Markdown/HighlightedCode (syntax highlighting)            │
│         ↓                                                   │
│  Terminal pixels (Ink Box/Text components)                │
└─────────────────────────────────────────────────────────────┘

DATA FLOW PATTERNS:
1. AppState (from external) → useAppState hook → component re-render
2. User keystroke → TextInput hook → onSubmit callback → REPL processes
3. Message update → Messages memoization → VirtualMessageList cache invalidation
4. Scroll event → useSyncExternalStore → pillVisible update (no REPL re-render)
5. Terminal resize → useTerminalSize hook → layout recalculation
```

---

## **6. CONFIGURATION: PROPS, THEMES, LAYOUT OPTIONS**

### **Theme System (ThemeProvider + color.ts)**
```typescript
// Design tokens: 'dark' | 'light' | 'auto'
// auto = live system theme watching (OSC 11 escape sequence polling)
// Colors: 'permission', 'error', 'success', 'info', 'warning', 'secondary', 'muted'

ThemeName:
  ├─ 'dark': Terminal dark theme (background #000, text light)
  ├─ 'light': Terminal light theme (background light, text dark)
  └─ 'auto': Auto-detect from $COLORFGBG or terminal capabilities

// Layout config via props:
Pane: { color?: keyof Theme; children: ReactNode }
Dialog: { title, subtitle, color?, hideInputGuide?, hideBorder? }
Tabs: { 
  defaultTab?, selectedTab?, onTabChange?, 
  contentHeight? (fixed-height tab content), 
  initialHeaderFocused?, navFromContent? 
}
FuzzyPicker: { 
  direction?: 'down'|'up', 
  previewPosition?: 'bottom'|'right', 
  visibleCount?: number 
}
PromptInput: { 
  mode?: 'normal'|'vim'|'voice',
  multiline?: boolean,
  placeholder?: string
}
```

### **Ink Layout Props (Box/Text primitives)**
```typescript
Box:
  ├─ flexDirection: 'row' | 'column'
  ├─ gap: number (spacing between children)
  ├─ paddingX, paddingY, paddingTop, paddingRight, etc.
  ├─ width: number | string
  ├─ height: number | string
  ├─ flexGrow: number
  ├─ flexShrink: number
  ├─ borderStyle: 'single' | 'double' | 'round' | 'bold'
  └─ borderColor: string (chalk color)

Text:
  ├─ bold: boolean
  ├─ italic: boolean
  ├─ color: string (theme color or chalk)
  ├─ backgroundColor: string
  ├─ dimColor: boolean
  └─ wrap: 'wrap' | 'truncate'

ScrollBox:
  ├─ showScrollbar: boolean
  ├─ maxHeight: number
  └─ onScroll?: (top: number, height: number) => void
```

---

## **7. INTERACTIONS: HOOKS, SERVICES, STATE MANAGEMENT**

### **React Hooks Used Throughout Components**

**State & Context Hooks:**
- `useState()` - Local component state (modal visibility, form input, selections)
- `useRef()` - Persist mutable values (input buffer, animation state, scroll position)
- `useContext()` - Theme, AppState, ModalContext, KeybindingContext
- `useSyncExternalStore()` - Scroll position tracking (pillVisible calculation)
- `useCallback()` - Stable event handlers (input validation, keybinding actions)
- `useMemo()` - Expensive computations (message normalizations, searches, theme resolution)
- `useEffect()` - Side effects (terminal theme watching, file system events, subscriptions)
- `useImperativeHandle()` - Imperative APIs (VirtualMessageList.jumpToIndex, warmSearchIndex)

**Custom Hooks (from ../hooks):**
- `useTerminalSize()` - Terminal rows/columns (context changes on resize)
- `useTextInput()` - Input buffer state machine (cursor, history, vim mode)
- `useTheme()` - Theme context + preview mode
- `useAppState()` / `useSetAppState()` - Global UI state
- `useKeybinding()` / `useKeybindings()` - Keyboard event dispatch
- `useVirtualScroll()` - Virtual scrolling calculations
- `useArrowKeyHistory()` - History navigation (up/down arrows)
- `useHistorySearch()` - Ctrl+R transcript search
- `usePromptSuggestion()` - Model-powered prompt completion
- `useTypeahead()` - @-mention/@-command typeahead
- `useShortcutDisplay()` - Format keybinding labels

**Ink Hooks:**
- `useTerminalFocus()` - Terminal focused/blurred state
- `useInput()` - Raw keyboard input handling
- `useAnimationFrame()` - Frame-based animation (spinners, waveforms)

### **State Management Architecture**

```
┌─────────────────────────────────────────────────┐
│  External State (persisted outside React)      │
│  ├─ Global config (theme, keybindings, history)
│  ├─ AppState (current model, task list, etc.)  │
│  ├─ Stats (FPS metrics, token usage)           │
│  └─ Store (message history, cache)             │
└─────────────────────────────────────────────────┘
           ↓ useAppState(selector)
┌─────────────────────────────────────────────────┐
│  React Component Tree                          │
│  ├─ App (providers) → FullscreenLayout          │
│  ├─ Local state: modal visibility, forms       │
│  ├─ Refs: scroll position, animation state     │
│  └─ Memoization: prevent unnecessary re-renders
└─────────────────────────────────────────────────┘

CRITICAL OPTIMIZATION: LogoHeader is memoized with agentDefinitions as dependency
so re-rendering Messages doesn't cascade to logo/status. The memo + stable AppState
selectors prevent 150K+/frame writes during long sessions (~2800 messages).
```

---

## **8. TERMINOLOGY: UI COMPONENTS & TERMINAL CONCEPTS**

| Term | Meaning |
|------|---------|
| **Pane** | A command-output region with a colored divider, padding, and flex layout |
| **Dialog** | Modal overlay with title, content, Esc/Enter keybindings |
| **Tabs** | Tab bar with arrow key navigation, optional fixed content height |
| **FuzzyPicker** | Search dropdown: async-filtered items, focus tracking, multi-action support |
| **Spinner** | Animated loading indicator (emoji rotation, progress bars) |
| **Box** | Ink flex container: layout children with gap, padding, direction |
| **Text** | Ink text node: renders strings with color, bold, italic, dimming |
| **ScrollBox** | Virtual scroll container with optional scrollbar |
| **Byline** | Status line with keyboard shortcut hints |
| **Divider** | Horizontal rule (colored top border) |
| **ThemedText** | Text that looks up color from theme context |
| **Sticky Prompt** | Header that sticks to top while user scrolls (computed from VirtualMessageList) |
| **Pill** | Floating badge ("N new messages") at scroll position |
| **Unseen Divider** | Marker line between last-read and new messages (for "jump to new") |
| **Virtual Scroll** | Lazy rendering: only render visible messages, compute heights dynamically |
| **Blit** | Terminal optimization: only redraw changed cells (Ink's renderChildren cascade) |
| **Message Actions** | Context menu on selected message (verbose toggle, copy, delete) |
| **Tool Permission** | Modal asking user to approve/reject tool use (file edit, bash, etc.) |
| **Briefing** | Reduced-verbosity mode: only show Brief tool results + user input |
| **Transcript Mode** | Read-only view (no input, search enabled, thinking collapsed) |

---

## **9. ALGORITHMS & MECHANISMS**

### **Virtual Scroll Algorithm (VirtualMessageList.tsx)**
```
INPUT: messages[], columns, scrollTop, viewportHeight
OUTPUT: rendered items for visible range

1. Cache message heights (WeakMap): height[i] = computeRenderHeight(messages[i])
2. Compute cumulative heights: cumHeight[i] = sum(heights[0..i])
3. Binary search: find first message where cumHeight[i] >= scrollTop
4. Render messages[i] through messages[j] where cumHeight[j] <= scrollTop + viewportHeight
5. Render above-padding, items[visible], below-padding (all heights in rows)
6. On scroll: cache valid, only update startIndex/endIndex (no re-render unless cache miss)
7. On columns change: invalidate cache, recompute all heights (text rewrap)
8. Search indexing: warm cache by lowercasing all messages (Ctrl+R trigger)
```

### **Keybinding Dispatch (useKeybinding hook)**
```
INPUT: action (e.g., "confirm:no"), handler, context
OUTPUT: keyboard events routed to handler if active

1. useKeybinding registers { action, context, isActive, handler } in global map
2. On keystroke: Ink reads raw key → lookup action → check context.isActive
3. If active: call handler() → prevent default → return true
4. Multiple handlers per key allowed (context priority: "input" > "global")
5. useKeybindings() registers multiple: useKeybinding(…) called N times
6. isCancelActive=false silences Esc/Ctrl-C/Ctrl-D so text field gets them
```

### **Message Normalization (Messages.tsx + utils/messages.js)**
```
INPUT: raw API message array
OUTPUT: RenderableMessage[] (user-facing normalized form)

1. Collapse consecutive messages of same type (e.g., 3 text blocks → 1)
2. Apply grouping: gather consecutive tool_use blocks with single tool_result
3. Filter: remove internal system messages (e.g., @-mention directives)
4. Reorder: if brief-only mode, drop text blocks, keep only Brief tool_use
5. Compute: buildMessageLookups (tool name → block, UUID → index, etc.)
6. Result: Messages sorted, deduplicated, searchable, with lookups for rendering
```

### **Search Indexing (VirtualMessageList.tsx + transcriptSearch.js)**
```
GOAL: Fast Ctrl+R incremental search with no jank

1. warmSearchIndex() called on first "/" keystroke
2. For each message: extractSearchText(msg) → toLowerCase() → cache in WeakMap
3. setSearchQuery(q): for each msg, indexOf(q.toLowerCase()) in cache
4. Collect all matches: (messageIndex, offsetWithinMessage)
5. Next/prev: jump to next (messageIndex, offset), scroll to visible, highlight
6. Anchor mechanism: user presses "/" → record scrollTop → typing jumps → ESC restores
```

### **Permission Decision Flow (PermissionRequest.tsx)**
```
INPUT: tool_use block (e.g., bash command)
OUTPUT: user decision (approve / reject / ask parent model)

1. Route tool to appropriate PermissionRequest component:
   BashTool → BashPermissionRequest
   FileEditTool → FileEditPermissionRequest
   etc.
2. Component renders: tool details + risk assessment + hints
3. Keybindings: Ctrl+D = reject, Enter = approve, ? = explain
4. Callback: onDone({ decision: 'approve'|'reject', ...}) → parent processes
5. Sticky footer: registerStickyFooter(jsx) keeps options visible during scroll
```

---

## **10. STATE MACHINES: LIFECYCLE & MODAL STATES**

### **Component Lifecycle Patterns**

```typescript
// MOUNT → RENDER → EVENT → UPDATE → RENDER → UNMOUNT

Example: TextInput.tsx
┌─ mount
│  └─ useTextInput() creates input state machine
│     └─ subscribe to keystroke events
│     └─ initialize history index
│
├─ render
│  └─ compute cursor position (visual vs logical)
│  └─ render Text node with cursor
│
├─ event: keystroke
│  └─ if vim mode: dispatch to vim state machine
│  └─ else: handle normal mode (insert/delete/history)
│  └─ setState(newInput, newCursorOffset)
│
├─ re-render
│  └─ Text component re-renders with new input
│
└─ unmount
   └─ unsubscribe keystroke events
   └─ cleanup history state
```

### **Modal Overlay State Machine (FullscreenLayout.tsx)**

```
┌──────────────────────────────────────────────────┐
│           MODAL STATE MACHINE                    │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌─ NO_MODAL (empty modal slot)                  │
│  │                                               │
│  ├─ SLASH_COMMAND_PANE (/config, /help, etc.)  │
│  │  ├─ User navigates tabs/menu                  │
│  │  ├─ ESC → NO_MODAL                            │
│  │  └─ Enter or action → NO_MODAL or next modal  │
│  │                                               │
│  ├─ PERMISSION_REQUEST (user approval)           │
│  │  ├─ Shows tool details + risk                 │
│  │  ├─ Ctrl+D → REJECT                           │
│  │  ├─ Enter → APPROVE                           │
│  │  └─ Complete → NO_MODAL                       │
│  │                                               │
│  ├─ FUZZY_PICKER (file select, model pick)       │
│  │  ├─ User types query + arrows                 │
│  │  ├─ ESC → NO_MODAL                            │
│  │  ├─ Enter → SELECT item + NO_MODAL            │
│  │  └─ Tab → ALTERNATE action + NO_MODAL         │
│  │                                               │
│  └─ DIALOG (confirm/reject)                      │
│     ├─ User presses Enter or ESC                 │
│     └─ Complete → NO_MODAL                       │
│                                                  │
└──────────────────────────────────────────────────┘

CONTEXT: ModalContext + useIsModalOverlay()
  ├─ Modal slots only show content if state != NO_MODAL
  └─ Pane/Dialog check useIsInsideModal() to skip own borders
```

### **Input Mode State Machine (PromptInput/inputModes.ts)**

```
┌───────────────────────────────────────────────────────┐
│        PROMPT INPUT MODE TRANSITIONS                  │
├───────────────────────────────────────────────────────┤
│                                                       │
│  NORMAL MODE                                          │
│  ├─ User types → accumulate buffer                   │
│  ├─ @mention → typeahead menu (FuzzyPicker)          │
│  ├─ #hashtag → slash command menu                    │
│  ├─ @file → file selector                            │
│  ├─ Ctrl+V → image paste (voice waveform during)     │
│  ├─ Ctrl+E → external editor                         │
│  └─ Enter → submit prompt                            │
│                                                       │
│  VOICE MODE (feature flag)                            │
│  ├─ Ctrl+; start recording                           │
│  ├─ Render waveform cursor (live audio levels)       │
│  ├─ Ctrl+; or timeout → stop, transcribe             │
│  ├─ Transcribed text appended to buffer              │
│  └─ User edits, Enter → submit                       │
│                                                       │
│  VIM MODE                                             │
│  ├─ ESC → normal mode                                │
│  ├─ i → insert mode                                  │
│  ├─ d, y, p → delete, copy, paste                    │
│  ├─ j, k → history                                   │
│  ├─ /, n, N → search                                 │
│  └─ : → command mode                                 │
│                                                       │
│  HISTORY SEARCH (Ctrl+R)                              │
│  ├─ Query input + match highlighting                 │
│  ├─ n/N → next/prev match                            │
│  ├─ Enter → restore match                            │
│  └─ ESC → cancel, restore anchor                     │
│                                                       │
└───────────────────────────────────────────────────────┘
```

### **Message Streaming State Machine**

```
┌────────────────────────────────────────────────────┐
│    MESSAGE RENDER STATE (shouldAnimate, isStatic)  │
├────────────────────────────────────────────────────┤
│                                                    │
│  STREAMING (incoming from API)                     │
│  ├─ shouldAnimate=true                             │
│  ├─ Render spinner for tool_use blocks             │
│  ├─ On each chunk: useAnimationFrame(50ms)         │
│  ├─ On completion: Message updates, spinner gone   │
│  └─ Time-out animation if tool stalls              │
│                                                    │
│  COMPLETE                                          │
│  ├─ shouldAnimate=false                            │
│  ├─ Full message rendered                          │
│  ├─ User can expand verbose / scroll               │
│  └─ Static rendering (blit optimization)           │
│                                                    │
│  TRANSCRIPT MODE                                   │
│  ├─ isStatic=true (no animation)                   │
│  ├─ Thinking blocks collapsed/redacted             │
│  ├─ Tool output truncated                          │
│  └─ Read-only (no verbose expand for some types)   │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## **SUMMARY: KEY ARCHITECTURAL INSIGHTS**

1. **Ink-based Terminal UI**: Pure React component tree compiled to terminal escape sequences, no manual ANSI handling
2. **Virtual Scroll Optimization**: Height cache + cumulative sums enable 2800-message transcripts with smooth 60 FPS
3. **Memoization Strategy**: `React.memo` on costly subtrees (LogoHeader, Message, Messages) prevents cascade re-renders
4. **Blit Caching**: Ink's renderChildren marks siblings as "dirty" on first change; memo breaks the cascade
5. **Context Layering**: FpsMetrics → Stats → AppState providers separate concerns; each subscribed independently
6. **Keybinding Priority**: Global map tracks { action, context, handler }; "input" context beats "global"
7. **Multi-Modal Input**: Single PromptInput component routes to vim/normal/voice state machines
8. **Permission Gating**: Tool permissions routed to specialized request components; supports sticky footer for scroll
9. **Search Indexing**: Lazy-warm cache (first Ctrl+R) prevents startup jank; incremental match on keystroke
10. **Theme Live-Watching**: OSC 11 polling enables auto theme switching without restart

---

This components module represents a **production-grade terminal UI framework** with sophisticated state management, performance optimization, and accessibility support. The architecture prioritizes framerate consistency and memory efficiency critical for long interactive sessions.