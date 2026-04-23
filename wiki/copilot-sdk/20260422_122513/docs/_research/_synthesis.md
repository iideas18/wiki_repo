# Phase 1C — Cross-Module Synthesis

## 1. End-to-End Flows

### Flow A — "Hello, world" single-prompt conversation

```
[User App]
   └─ await client.createSession({ model: "gpt-4" })
         └─ [SDK Client]
               ├─ spawn CLI subprocess (if not already started)
               ├─ JSON-RPC: getStatus → negotiate protocolVersion
               └─ JSON-RPC: session.create → {sessionId, capabilities}
   └─ await session.sendAndWait({ prompt: "Hello" })
         └─ [SDK Session]
               ├─ register idle/error/message listener (race fix)
               ├─ JSON-RPC: session.send → {messageId}
               └─ wait for session.idle event
                     ├─ [CLI server runs LLM turn]
                     ├─ emit: session.turn_started
                     ├─ emit: assistant.message (streaming chunks)
                     └─ emit: session.idle
   └─ response.data.content → "Hi! How can I help?"
   └─ client.stop() / `await using` / defer client.Stop()
         └─ JSON-RPC: shutdown → process exits
```

**Latency profile:** SDK overhead ~20-50ms (spawn + handshake) amortised across sessions on same client; per-turn overhead <5ms + LLM latency (dominant).

### Flow B — Tool invocation round-trip

```
session.sendAndWait({ prompt: "what's the weather in Seattle?" })
  →  CLI LLM decides to call `get_weather`
  →  CLI: session/toolInvoke RPC (server→client) with {name:"get_weather", args:{city:"Seattle"}}
  →  SDK routes to registered Tool handler:
        ├─ (optional) preToolUse hook — can modify/deny
        ├─ (optional) permission handler — user approves
        ├─ user handler: returns "Cloudy, 62F"
        └─ (optional) postToolUse hook — can rewrite result
  →  SDK replies to RPC with tool result payload
  →  CLI LLM continues turn, synthesises: "Cloudy and 62°F in Seattle..."
  →  session.idle
```

**Coupling point:** The `session/toolInvoke` RPC is where server→client direction matters. The SDK must have registered the handler before the session started; doing it after is racy.

### Flow C — Permission-gated destructive tool

```
prompt: "delete all node_modules"
  →  LLM plans to call builtin shell tool: `rm -rf node_modules/*`
  →  CLI: permission.request RPC with {tool:"shell", command:"rm -rf ...", kind:"write"}
  →  SDK invokes user's onPermissionRequest handler
        ├─ app may show a UI prompt, pause until user clicks approve
        └─ return PermissionRequestResult{kind: "approved"} or {kind:"denied", message:"..."}
  →  SDK replies to RPC
  →  CLI either proceeds (approved) or aborts the tool call with the provided message
  →  LLM sees the denial, responds: "I won't proceed without approval"
  →  session.idle
```

### Flow D — SDK fan-out (same scenario, 4 languages)

The conformance harness runs the same YAML scenario through all four SDKs:

```
                     ┌───► nodejs adapter ──► snapshot_ts.yaml
[YAML scenario] ─────┼───► python adapter ──► snapshot_py.yaml ─┐
                     ├───► go adapter     ──► snapshot_go.yaml  ├─► diff against test/snapshots/<name>.yaml
                     └───► dotnet adapter ──► snapshot_cs.yaml  ┘
```

### Flow E — Codegen pipeline

```
@github/copilot/schemas/api.schema.json
             │
             ▼
scripts/codegen/utils.ts: postProcessSchema
             │
             ├──► typescript.ts → nodejs/src/generated/rpc.ts
             ├──► python.ts     → python/copilot/generated/rpc.py (via quicktype)
             ├──► go.ts         → go/rpc/generated_rpc.go (via quicktype)
             └──► csharp.ts     → dotnet/src/Generated/Rpc.cs (via quicktype)
```

## 2. Coupling Analysis

### Tightly coupled

- **Every SDK ↔ wire protocol.** The JSON-RPC method names, parameter shapes, and event payloads are an unforgiving interface. Adding a new method requires: (1) schema update, (2) codegen, (3) 4× SDK wiring, (4) conformance fixture, (5) four-language docs.
- **Generated code ↔ hand-written SDK code.** Business logic imports from `generated/`. When codegen renames a field, the importing code breaks at compile time — intentional; failures surface in the fastest place.
- **Python read thread ↔ asyncio loop.** `call_soon_threadsafe` is the one bridge; a bug here (forgetting it, calling wrong-loop) causes silent hangs.

### Loosely coupled

- **Each language SDK ↔ every other language SDK.** No shared code. No shared test runner at the code level (only YAML scenarios). A user app consuming the Python SDK cannot accidentally pull in TS code.
- **User tool handlers ↔ SDK internals.** The tool boundary is `(args, invocation) -> result` — a function signature. User code never imports from `generated/`.
- **Permission/hook handlers ↔ everything else.** Same story — thin callbacks, no import surface.

### Accidental coupling risks

- **Protocol version bumps** cascade to four SDKs + docs + fixtures. Mitigation: the `protocolVersion` integer keeps matrix small, capability flags at session granularity handle incremental features.
- **Codegen emitter upgrades** can reformat every file. Mitigation: alphabetical property sort + deterministic output in `postProcessSchema`.
- **CLI binary version** shipped in each language's bundle; if versions drift, a user with both Node and Python SDKs installed can get two different CLIs. Mitigation: `sdk-protocol-version.json` is single source of truth.

## 3. Architectural Philosophy

Reading the codebase holistically, the following principles are visible:

1. **Contract over convention.** JSON schemas + codegen + conformance tests enforce behaviour; nothing relies on "we'll remember to do X".

2. **Per-language idiomaticity beats consistency.** Each SDK uses its language's native patterns — `async with` in Python, `await using` in C#, `defer` in Go, Promise chains in TS. The only forced symmetry is the wire contract.

3. **Process boundary as firewall.** The CLI is a separate process. This gives: trivial cleanup (OS kills the process), zero in-process CLI dependencies, and a language-agnostic communication layer (JSON-RPC).

4. **Explicit capabilities over feature probing.** `session.capabilities.ui.elicitation` tells the client at session start what works. One round-trip, no "try call, catch MethodNotFound, fall back".

5. **Shared schemas as the single source of truth.** The schema files live *in the CLI package*, not in the SDK repo. When the CLI updates, the SDK inherits the new contract. No out-of-band sync.

6. **Public preview gating.** `MIN_PROTOCOL_VERSION = 2` and the explicit CHANGELOG for every behaviour change suggest a repo that expects breaking changes and wants them surfaced loudly.

## 4. Shared State Inventory

Cross-module state is almost nil by design:

| Shared state | Location | Synchronisation |
|---|---|---|
| Protocol version integer | `sdk-protocol-version.json` | Single file, all SDKs read it at codegen time and embed a constant |
| JSON schemas | `nodejs/node_modules/@github/copilot/schemas/*.schema.json` | Shipped with CLI npm package; codegen reads at build time |
| Conformance scenarios | `test/snapshots/` YAML | All SDKs implement until snapshots match |
| CHANGELOG | root `CHANGELOG.md` | Human-maintained; lists per-feature which SDKs got it |
| Protocol negotiation result | per-Client at runtime | Cached in the client after handshake |

No runtime-shared state between SDK processes — each app's SDK instance is self-contained.

## 5. System Evolution

**Earliest layer (probably Node):** The Node SDK was the reference; the CLI is itself Node; `vscode-jsonrpc` was readily available.

**Next (Python + Go):** Ports of the Node behaviour. Python's 385-line `_jsonrpc.py` + 2730-line `client.py` ratio suggests the transport was ported once and has been stable; the client grew as features (hooks, skills, elicitation) landed.

**Then .NET:** Arrived with full parity. The polymorphic converter and MillisecondsTimeSpanConverter bespoke-code suggest someone actively solved serialisation corner cases rather than porting them.

**Scripts/codegen came when:** The first "we have to add a field to 4 SDKs manually and forgot one" bug. Then it became the forcing function for stability.

**Conformance tests came:** After the third or fourth "this works in Python but not Go" issue. The `snapshots/` folder naming inconsistencies (`ask_user` vs `ask-user`) hint at organic growth.

**Most stable today:** The JSON-RPC framing + the `Client`/`Session` façade shape. Both have been fossilised by the public API + codegen.

**Most volatile:** Hook APIs, elicitation (just-added in v0.2.1), `systemMessage` transform callbacks — these are still accruing variants.
