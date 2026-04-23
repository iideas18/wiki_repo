# python — Deep Analysis (Phase 1B)

## 1. Existence Rationale

The Python SDK exists because a massive slice of agent development happens in Python (LangChain, DSPy, data-science notebooks, MLOps). Without it, Python users would shell out to `copilot` and parse stdout — losing the event stream, tool callbacks, and permission flow. The module structure mirrors Node almost 1:1 on purpose (`client.py` ↔ `client.ts`, `session.py` ↔ `session.ts`) so a developer who knows one SDK can navigate the other immediately.

## 2. Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|---|---|---|---|
| Async runtime | native `asyncio` with `async def` / `await` | trio, sync-only, threaded-sync | asyncio is standard-library; matches Node's event-loop semantics; zero extra deps |
| JSON-RPC transport | hand-rolled `_jsonrpc.py` using threads + asyncio | use `json-rpc`, `jsonrpc-asyncio` pkg | asyncio subprocess on Windows has long-standing bugs with stdin/stdout; threads + `run_coroutine_threadsafe` is the bulletproof pattern |
| Type system | `TypedDict` for payloads, dataclasses for config | pydantic, attrs, plain dicts | TypedDict is stdlib; pydantic would be a 1MB+ transitive dep; dataclasses fit config objects with defaults cleanly |
| FS provider | `abc.ABC` with abstract methods | protocol, duck-typed callables | `ABC` gives clear compiler errors at class definition time; users prefer it for the "implement this interface" ergonomic |
| Context manager | `async with CopilotClient()` | explicit `start()`/`stop()` | Pythonic resource management; impossible-to-forget cleanup; harmonises with file-like idioms |
| Package layout | flat `copilot/` package, internal modules prefixed `_` | sub-packages | Flat structure keeps import paths short (`from copilot import CopilotClient`); underscore prefix signals "private" without enforcing it |
| Error translation in SessionFs | catch `Exception` → convert to `SessionFSError` | let exceptions propagate | RPC counterpart must receive structured error (code+message) — propagating raw Python exceptions would crash the server's JSON parser |
| Private vs public imports | `.generated.rpc` / `.generated.session_events` | re-export through `__init__` | Users shouldn't poke at generated code; keeping it in a sub-module is a social signal |

## 3. Algorithm Deep-Dives

### 3.1 Threaded JSON-RPC bridge (`_jsonrpc.py`)

**Problem.** `asyncio` subprocess pipes on Windows drop bytes under load, fragment frame boundaries, and have returned partial reads as empty strings for years. Meanwhile CPython's blocking stdio is rock-solid. How do you present an `async` API while reading blocking stdio?

**Trace.**
1. `JsonRpcClient(process)` spawns two daemon threads: `_read_thread` (reads stdout) and `_stderr_thread` (drains stderr so the subprocess doesn't deadlock on a full pipe).
2. Main asyncio loop owns `pending_requests: dict[str, asyncio.Future]`, keyed by request ID.
3. To send: allocate UUID, create a Future, stash it, write `Content-Length: N\r\n\r\n<json>` to stdin through a `threading.Lock()`, return the future.
4. Read thread: loop forever reading headers, then body bytes, parse JSON, dispatch by message type.
5. If response: `loop.call_soon_threadsafe(future.set_result, result)` — the crucial cross-thread handoff.
6. If notification: `call_soon_threadsafe(notification_handler, method, params)` — forwards to Python-async user handler.
7. If incoming request (server→client): look up handler, schedule it on the loop, send the response back from the loop when done.
8. On process exit, the read thread observes EOF, sets `_process_exit_error`, calls `call_soon_threadsafe` to reject all pending futures with `ProcessExitedError`.

**Complexity.** O(1) per message for dispatch, O(N) read for each message of size N. Two OS threads per client regardless of session count.

**Why this algorithm.** The equivalent pure-asyncio implementation (using `asyncio.subprocess_exec`) must use a `StreamReader` internally, which itself uses `add_reader` on stdin/stdout FDs — on Windows this maps onto IOCP overlap operations that can drop data when the Python GIL is held during certain native-extension calls. Threads with a lock sidestep the entire asyncio-on-Windows minefield.

**Edge cases.**
- Process dies mid-request → `ProcessExitedError` rejects all pending futures.
- Malformed JSON → logged to stderr, read loop continues (tolerant to server-side bugs).
- Back-pressure: `write_lock` serialises writers; if the server stops reading stdin, writes eventually block. No timeout on write — relies on OS pipe semantics.

### 3.2 `async with` lifecycle

**Problem.** The CLI subprocess must be stopped no matter what exception kills the caller's code, otherwise orphan processes accumulate.

**Trace.**
1. `__aenter__`: `await self.start()` — spawns subprocess, starts threads, does protocol handshake.
2. Caller uses `client` normally.
3. Any exception (or normal exit) triggers `__aexit__`: `await self.stop()` — sends graceful `shutdown` RPC, waits up to `shutdownTimeout` (default 5s), then `process.terminate()`, then `process.kill()` as escalating fallbacks.
4. Threads observe EOF on stdout, exit cleanly.
5. All pending session futures receive `ProcessExitedError`.

**Why.** Python's `try/finally` is often forgotten; `async with` makes cleanup impossible to forget. The escalation `shutdown RPC → SIGTERM → SIGKILL` matches POSIX convention and avoids corrupting on-disk state from an abrupt kill when possible.

### 3.3 `SessionFsProvider` abstract base + adapter

**Problem.** CLI wants to call `read`/`write`/`stat` as RPC methods, getting back results **or** structured `SessionFSError` codes. Python users want to write natural code that raises exceptions when things fail.

**Trace.**
1. Define `SessionFsProvider(abc.ABC)` with abstract `async read(path)`, `write(path, content)`, `stat(path)`, etc. Users subclass and raise whatever.
2. `create_session_fs_adapter(provider)` returns a `SessionFsHandler` (generated class) whose methods wrap each provider call in `try/except`.
3. On exception, `_to_session_fs_error(exc)` maps Python exceptions to `SessionFSError` variants: `FileNotFoundError → not_found`, `PermissionError → permission_denied`, `NotImplementedError → not_supported`, else `{ code: "internal", message: str(exc) }`.
4. Adapter returns the `SessionFSError` in the RPC result (not as an exception — the server expects a typed error *payload*).

**Why this algorithm.** Alternatives: (a) force users to return sentinel errors — un-Pythonic; (b) let exceptions propagate through RPC — wire format can't carry them. The adapter is the thinnest layer that translates idioms.

## 4. Error Philosophy

**Translate at boundaries.** Internal errors are Python exceptions (`JsonRpcError`, `ProcessExitedError`, plus subclass chains). At the SDK surface (SessionFS adapter, tool handlers) they're converted to structured RPC error payloads because the CLI expects them. Tool handler exceptions become `{ isError: true, content: str(e) }` so the model sees the failure and can retry or apologise.

## 5. Performance Characteristics

- **Two OS threads per Client**, regardless of session count — the bridge is shared. This is cheap on Linux/Mac (< 100KB each) but adds up across many clients.
- **GIL impact:** the read thread holds GIL while deserialising JSON; big tool results stall asyncio briefly. Not benchmarked in source — trade-off accepted.
- **Serialisation:** `json.dumps`/`json.loads` stdlib — not the fastest (orjson is 3-4x quicker) but zero extra deps.
- **Back-pressure:** relies on OS pipe buffers (typically 64KB). Beyond that, writes block on `write_lock`. In practice tool results are small.

## 6. Evolution Clues

- `_jsonrpc.py` is only 385 lines; the complexity elsewhere (2730 lines of `client.py`) suggests the hard work is permission/tool/session wiring, not transport.
- `TypedDict` pervades — the code was likely converted from plain dicts + mypy stubs as the public API solidified.
- `_sdk_protocol_version.py` is 19 lines — a trivial getter. This tiny module style implies more helpers were extracted recently to keep `client.py` from ballooning further.
- Complete absence of pydantic, attrs, or any popular validation library is striking — an explicit "stdlib only" stance that reduces install footprint.
