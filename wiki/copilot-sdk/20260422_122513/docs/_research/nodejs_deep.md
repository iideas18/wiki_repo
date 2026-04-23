# nodejs — Deep Analysis (Phase 1B)

## 1. Existence Rationale

The Node.js SDK is the reference implementation. It exists as the **first-class** language because (a) the Copilot CLI itself is a Node.js binary, so embedding a Node SDK means same-process integration is possible in the future; (b) TypeScript's structural types line up almost 1:1 with JSON Schema, making codegen the thinnest on this side; (c) VS Code and the majority of agent extensions live in the Node ecosystem. Without this SDK, the repo would still need a reference implementation — every other language is effectively a port of the Node behaviour, verified by the conformance suite.

## 2. Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|---|---|---|---|
| JSON-RPC library | `vscode-jsonrpc` | hand-rolled, `json-rpc-2.0` npm package | VS Code's impl is battle-tested across millions of extensions; supports Content-Length framing required for LSP-style stdio; handles cancellation tokens natively |
| Tool parameter spec | accepts plain JSON Schema **or** Zod schemas | force JSON Schema only | Zod is the de facto TS validation library; requiring JSON Schema adds friction; `toJSONSchema()` probe keeps the optional dependency truly optional |
| Process lifecycle | `spawn` + managed `ChildProcess` | user brings their own process, HTTP server, WebSocket | OS pipes give back-pressure + exit signals for free; no need for heartbeats |
| Module format | ESM with `.js` extensions in imports | CJS, dual package | ESM is the modern default; Node's ESM resolver forbids extensionless imports; locking to ESM avoids the "dual package hazard" |
| Session event delivery | custom `Set<Handler>` + `Map<EventType, Set>` | Node `EventEmitter` | Node EventEmitter leaks listeners silently, no type-level event discrimination; custom impl gets typed `on('assistant.message', ...)` and guaranteed removal via returned unsubscribe fn |
| System-message transforms | JSON stub + side-map of callbacks | pre-expand on client, RPC with closures | Callbacks can't be serialised; pre-expanding defeats the whole "let the server substitute" point |
| Bundled-CLI lookup | `createRequire(import.meta.url).resolve('@github/copilot')` | env var, hard-coded path | Uses Node's own package resolution — always finds the right copy in nested node_modules layouts, respects `peerDependencies` correctly |
| Types strategy | one giant `types.ts` (1735 lines) | per-domain files | Avoids circular imports (every file references types); single `types.ts` is a well-known TS idiom; re-exported from `index.ts` for public API |

## 3. Algorithm Deep-Dives

### 3.1 `sendAndWait` — race-free idle detection

**Problem.** After calling `session.send(prompt)`, user code wants to block until the assistant is done. But events can fire *between* the send call returning and the user attaching a listener — if the LLM is cached and replies in 2ms, `session.idle` may already have been emitted and missed forever.

**Trace.**
1. Pre-create an unresolved `idlePromise` with `resolve`/`reject` refs hoisted outside the executor.
2. Call `this.on(handler)` **before** `await this.send(...)`. Handler watches for three event types: `assistant.message` (captures the last one), `session.idle` (resolves), `session.error` (rejects with server-supplied message + stack).
3. Only now call `await this.send(options)` — by the time the wire request lands, the listener is already registered.
4. Race `idlePromise` against a `setTimeout`-backed rejection (default 60s).
5. In `finally`, call the returned unsubscribe fn and clear the timeout.

**Complexity.** O(1) per event, O(N) total where N = events emitted before idle. Space: constant; only the last assistant message is retained.

**Why this algorithm.** Alternatives: (a) polling `isIdle` — wastes cycles, misses transient states; (b) synchronous subscribe inside the send RPC — requires library support the underlying `vscode-jsonrpc` doesn't cleanly provide; (c) server queues events until client reads — would need new protocol. Pre-registration is the smallest change that fixes the race.

**Edge cases.**
- Timeout while tool handlers are still running: the server continues, the promise rejects — user's hooks may still fire after.
- Multiple `assistant.message` events (rare, can happen with streaming mid-flight corrections): only the last one is returned.
- `session.error` during tool execution aborts the wait but leaves the session in an indeterminate state; user must `disconnect()`.

### 3.2 Connection establishment & protocol negotiation

**Problem.** The client needs to (a) spawn or connect to a CLI server, (b) agree on a protocol version, (c) set up bi-directional RPC so the server can call *back* into the client (for tool dispatch, permissions, elicitations).

**Trace.**
1. `new CopilotClient(options)` — options are validated but no I/O yet.
2. `client.start()` / auto-start on first `createSession`: resolve CLI path via `createRequire(import.meta.url).resolve('@github/copilot')` → fallback to user-supplied `cliPath` → fallback to `cliUrl` (no spawn needed).
3. For spawn path: `spawn(cliPath, ['serve', '--stdio'], { stdio: ['pipe','pipe','pipe'] })` → wire `StreamMessageReader(stdout)` + `StreamMessageWriter(stdin)` into `createMessageConnection`.
4. For TCP path: open `Socket`, wait for connect, wrap in reader/writer.
5. `registerClientSessionApiHandlers(connection, {...this})` — registers server→client RPC methods (tool callbacks, permission, elicitation, FS ops).
6. `connection.listen()` starts the read loop.
7. First RPC: `copilot.getStatus` — returns `{ protocolVersion, capabilities }`. Client compares with `MIN_PROTOCOL_VERSION = 2`, rejects below.
8. Cache `negotiatedProtocolVersion` for future capability gates (e.g., permission `no-result`).

### 3.3 Tool invocation flow

**Problem.** Server wants to call a tool the user defined in the SDK. The server only knows the tool by name + JSON args. The SDK must route to the right handler, typecheck args, execute possibly-async code, and return a JSON result — while respecting the permission policy.

**Trace.**
1. Server emits `session/toolInvoke` RPC with `{ toolName, args, invocationId }`.
2. Pre-registered handler in `registerClientSessionApiHandlers` looks up the session by ID, then the tool by name in `session.toolHandlers: Map<string, ToolHandler>`.
3. If a `preToolUse` hook is configured, invoke it — it can modify args, deny, or short-circuit with a canned result.
4. Call permission handler (if gated): result → approved/denied/modified.
5. Invoke the user's `handler(args, invocation)` — awaited if async.
6. Post-process via `postToolUse` hook (can rewrite the result).
7. Return typed `ToolResult` (string passes through, object → JSON string).

**Why this algorithm.** Alternatives include running tools in a worker thread (adds latency, marshalling), or having the SDK forward raw RPC to user code (defeats the convenience API). The current design keeps the user-facing contract simple (`(args) => result`) while supporting hooks, permissions, and type safety.

## 4. Error Philosophy

**Propagate-up with typed errors.** The SDK uses plain `Error` subclasses (`ConnectionError`, `ResponseError` from `vscode-jsonrpc`). No custom error hierarchy — the thinking seems to be that typed errors require users to catch specific types, which is friction for the 95% case of `try { ... } catch(e) { console.error(e) }`. Errors include enough info (message + cause) for structured logging.

Notable: `NO_RESULT_PERMISSION_V2_ERROR` is a constant string so upstream code can pattern-match without importing a sentinel. This is a "protocol downgrade" error — the user asked for a behaviour the server doesn't support.

## 5. Performance Characteristics

- **Hot path:** the event pump. A single `Set.forEach(handler => handler(event))` per event. O(handlers) per event. No allocation in the hot path beyond the event object itself.
- **Cold path:** session creation — one RPC round trip, ~10ms on localhost.
- **Bottleneck:** JSON serialisation for large tool results. Not mitigated (no streaming tool results) — would need a protocol extension.
- **Memory:** ~1 MB per idle session (event handlers + capability cache). Tools are per-session so duplicating 20 tools across 10 sessions = 200 handlers.

## 6. Evolution Clues

- `index.ts` re-exports 80+ types individually by name — classic "stabilise the public surface" move; consistent with "public preview" status.
- `types.ts` has grown to 1735 lines; candidates for extraction (separate `events.ts`, `permissions.ts`) are visible from natural grouping in the file.
- `NO_RESULT_PERMISSION_V2_ERROR` constant and `MIN_PROTOCOL_VERSION = 2` (not 1) suggest protocol v1 existed and was retired; the SDK still labels behaviour as "v2-era" or "v3-era".
- `extension.ts` (44 lines) hints at an unfinished VS Code extension integration — "extension" is a meaningful word in that ecosystem.
