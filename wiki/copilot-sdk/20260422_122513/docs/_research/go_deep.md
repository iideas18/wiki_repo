# go — Deep Analysis (Phase 1B)

## 1. Existence Rationale

Go is the lingua franca of cloud-native tooling — Kubernetes operators, CI runners, backend services. A Go SDK means Copilot agents can be embedded into these without shelling out. Additionally, Go compiles to a single static binary, so an operator-style tool built on the Go SDK deploys trivially. The Go SDK also showcases the **embeddedcli** pattern: because Go can't trivially depend on npm packages, it ships or extracts the CLI itself.

## 2. Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|---|---|---|---|
| JSON-RPC library | hand-rolled `internal/jsonrpc2` | `sourcegraph/jsonrpc2`, `creachadair/jrpc2` | Framing is LSP-style (Content-Length headers); external libs assume HTTP or websocket — wrong transport assumption |
| Tool handlers | `DefineTool[T, U]` with generics | `interface{}` args, reflection-only | Go 1.18+ generics give compile-time arg typing while still auto-generating the JSON schema via reflection on T |
| Cross-platform concerns | `process_windows.go` / `process_other.go`, `flock_{unix,windows,other}.go` | `runtime.GOOS` switches inside one file | Go build tags isolate syscall specifics; file-level separation is idiomatic and lets each file import only its platform's deps |
| Concurrency primitives | `sync.Mutex`, `sync.RWMutex`, `atomic.Pointer[os.Process]` | channels-only, single mutex | `atomic.Pointer` for the short-lived `os.Process` read; `RWMutex` for start/stop (rare writes, many reads); `Mutex` for sessions map (equal read/write) |
| CLI bundling | `internal/embeddedcli/installer.go` + `internal/flock/` | require user to install CLI, bundle via `go:embed` | flock handles parallel process races; extraction to cache dir keeps binary size normal; `go:embed` would 3x the binary |
| Public API surface | pointer-to-struct receivers, constructor `NewClient` | `copilot.Client{}` direct | Enforces "use the constructor" so internal fields can be added without breaking API; `nil` options allowed for defaults |
| Result-union types | `rpc/result_union.go` with type tags | `interface{}` + type assertions at call sites | Hand-written switch/assert layer keeps user code clean: `if d, ok := event.Data.(*AssistantMessageData); ok { ... }` |
| Permission handlers | single exported `PermissionHandler` struct with methods | package-level functions | `copilot.PermissionHandler.ApproveAll` reads naturally; namespaces the helpers without polluting the package root |

## 3. Algorithm Deep-Dives

### 3.1 `DefineTool[T, U]` — generic tool wrapper

**Problem.** Users want to write `func(args GetWeatherArgs) (string, error)` and have the SDK (a) generate the JSON Schema for `GetWeatherArgs`, (b) unmarshal JSON into it, (c) marshal the return value back to JSON — all without users writing schema strings.

**Trace.**
1. `DefineTool[T, U any]` receives a `handler func(T, ToolInvocation) (U, error)`.
2. `generateSchemaForType(reflect.TypeOf(zero))` walks `T` via reflection, producing a `*jsonschema.Schema` with `jsonschema` struct-tag hints honoured.
3. `createTypedHandler(handler)` returns a `func(raw ToolInvocation) (any, error)` that unmarshals `inv.Arguments` into a new `T`, calls `handler(t, inv)`, returns `U` as-is.
4. SDK stores both in a `Tool{Name, Description, Parameters (schema), Handler (erased)}` record.
5. At invocation time, the erased handler runs; Go's type system is out of the picture — the compiler verified at `DefineTool` that `T` and `U` line up.

**Why this algorithm.** Alternatives: (a) code generation — awkward, pollutes repo; (b) `interface{}` + manual unmarshal — loses type safety, every tool reimplements the unmarshal; (c) struct tags on the tool itself — still loses the zero-value check. Generics let the schema *and* the runtime wrapper both derive from a single `T`, with compile-time guarantees.

**Edge cases.** Anonymous struct types get auto-named; nested structs recurse; `json:"-"` fields are omitted from schema; private fields are skipped.

### 3.2 File-lock-guarded CLI extraction

**Problem.** The Go SDK bundles a zipped CLI. On first use (or after CLI version bump), it extracts to `~/.cache/copilot-sdk-go/cli-<sha>/copilot`. If two Go programs start at the same time, both may try to extract; concurrent writes corrupt the binary.

**Trace.**
1. `installer.go` computes the target path using the embedded binary's content hash (so content-addressable, safe to reuse).
2. If target exists and hash matches, return early.
3. Otherwise, open `<target>.lock`, acquire exclusive flock via `flock_unix.go` (`unix.Flock(fd, LOCK_EX)`) or `flock_windows.go` (`LockFileEx` with `LOCKFILE_EXCLUSIVE_LOCK`).
4. Re-check existence under lock (double-checked locking).
5. Extract to `<target>.tmp`, `fchmod` to 0755, `os.Rename(tmp, target)` — atomic on same filesystem.
6. Release lock.

**Why this algorithm.** Alternatives: (a) nothing — first run race corrupts binary; (b) OS-global mutex — doesn't work across machines using shared caches; (c) user-space lockfile with PID — races on crash recovery. POSIX advisory flock + Windows `LockFileEx` are kernel-enforced and automatically released on process exit.

**Edge cases.** Stale lock from crashed process: kernel releases automatically on exit. Lock file persists; that's fine — it's 0 bytes. Filesystem doesn't support flock (some network FSs): `flock_other.go` no-ops and relies on the atomic rename alone.

### 3.3 Start-stop lifecycle under `startStopMux`

**Problem.** `client.Start()` and `client.Stop()` can be called from any goroutine, and the client exposes methods (`CreateSession`, etc.) that need a live process. Naïve implementation races: `Stop` kills the process while `CreateSession` is mid-RPC.

**Trace.**
1. `Start()` acquires `startStopMux` as **writer** → no callers can see the half-initialised state.
2. Spawns subprocess, wires pipes, starts reader goroutine, performs handshake, updates `state = Connected` under the write lock.
3. Methods like `CreateSession` acquire `startStopMux` as **reader** — many can run concurrently, all see a stable process handle.
4. `Stop()` writer-acquires, sends `shutdown` RPC, `cancel()`s the RPC context, `process.Wait()`, sets `state = Disconnected`.
5. `atomic.Pointer[os.Process]` lets goroutines sending `SIGTERM` during a forced shutdown check for nil without holding the mutex.

**Complexity.** Readers: constant under contention (RWMutex fairness). Writers: O(readers-in-flight) wait.

## 4. Error Philosophy

**Error values + typed errors for recognisable conditions.** `errors.New("...")` for simple cases, exported `var ErrXxx` for conditions callers should branch on (`ErrParse`, `ErrMethodNotFound`). Wrapping with `fmt.Errorf("...: %w", err)` preserves chains. No panics except for literal programmer bugs. Permission handlers return `(PermissionRequestResult, error)` — letting Go's comma-error pattern carry both the user decision and a failure.

## 5. Performance Characteristics

- **Zero-alloc hot path:** the event dispatch loop uses pre-allocated buffers; JSON decode reuses `bufio.Reader`.
- **Reflection cost:** `DefineTool` pays at registration (once per tool). Runtime tool invocations don't reflect — they use the closure captured at `DefineTool` time.
- **Goroutines:** one reader goroutine per client + N short-lived goroutines per in-flight RPC. Not tens of thousands.
- **Lock contention:** `sessionsMux` is per-`map` access only; not held during RPC.

## 6. Evolution Clues

- `client_test.go` is 966 lines — roughly half as long as `client.go`. Heavy test coverage consistent with a "reference-quality" SDK.
- `internal/flock/flock_other.go` (no-op fallback) suggests flock-unsupported filesystems were observed in the wild.
- `rpc/result_union.go` being hand-written next to `rpc/generated_rpc.go` hints that codegen can't yet emit Go-idiomatic discriminated unions — a known limitation accepted by having one handmade file.
- `cmd/bundler/main.go` exists purely for release: it bundles a CLI release into the SDK. This separation keeps the main module free of the bundling code in user builds.
- `process_{windows,other}.go` suggests an early phase where everything was in one file and a Windows-specific bug forced the split.
