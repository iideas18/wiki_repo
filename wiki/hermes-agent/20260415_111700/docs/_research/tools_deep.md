# tools/ — Tool Implementations

## 1. PURPOSE

The `tools/` module (37,485 lines across 70 Python files) is the **central orchestration hub for all agent capabilities** in Hermes Agent, a self-improving AI agent by Nous Research. It provides 40+ production tools organized into logical toolsets (terminal, file, web, vision, AI, skills, etc.), a thread-safe registry for dynamic tool discovery (especially from MCP servers), and a pluggable execution backend system supporting local, Docker, SSH, Modal cloud, Singularity, and Daytona environments. The module handles tool registration, invocation, result persistence (defense against context-window overflow), security scanning, and integration with external capability providers (MCP, OAuth, gateway APIs).

---

## 2. KEY CLASSES/FUNCTIONS

| Name | File | Role |
|------|------|------|
| `ToolRegistry` | `registry.py` | Thread-safe singleton managing tool schemas, handlers, availability checks, and dispatch; supports dynamic registration/deregistration for MCP servers |
| `BaseEnvironment` | `environments/base.py` | Abstract base for execution backends; implements session snapshot, CWD tracking, interrupt handling, and unified bash-based command wrapping |
| `LocalEnvironment` | `environments/local.py` | Direct local machine execution; filters sensitive env vars, handles subprocess lifecycle, PATH management |
| `DockerEnvironment` | `environments/docker.py` | Containerized execution with hardened security (cap-drop, no-new-privileges, PID limits), resource limits, optional bind-mount persistence |
| `ModalEnvironment` / `ManagedModalEnvironment` | `environments/modal.py`, `managed_modal.py` | Cloud sandbox execution via Modal; supports direct credentials and managed Nous gateway routing |
| `SSHEnvironment`, `SingularityEnvironment`, `DaytonaEnvironment` | `environments/ssh.py`, etc. | Remote SSH, Singularity containers, Daytona workspaces |
| `ShellFileOperations` | `file_operations.py` | Unified file API (read, write, patch, search) across all backends via shell commands; write-deny blocklist for sensitive files |
| `TodoStore` | `todo_tool.py` | In-memory task list (per-session) for decomposing complex tasks; supports merge/replace modes with deduplication |
| `SkillsHub` / `SkillSource` | `skills_hub.py` | Adapter pattern for skill registry sources (bundled, GitHub, Hub); manifest-based sync with content hash tracking |
| `ScanResult` / `skills_guard.py` | `skills_guard.py` | Security scanner for externally-sourced skills; regex-based static analysis with trust-level-aware install policy |
| `HermesTokenStorage` | `mcp_oauth.py` | OAuth token persistence to disk; handles PKCE flow, dynamic client registration, step-up auth |
| `BudgetConfig` | `budget_config.py` | Immutable 3-layer result persistence budget (per-tool, per-turn, preview size); pinned overrides for security |
| `ManagedToolGatewayConfig` | `managed_tool_gateway.py` | Configuration for Nous-hosted vendor passthroughs (Firecrawl, TTS, image generation); access token caching |
| `CheckpointManager` | `checkpoint_manager.py` | Transparent filesystem snapshots via shadow git repos; provides rollback without CLI overhead |
| `DebugSession` | `debug_helpers.py` | Structured debug logging to JSON files (one per tool call) for post-mortem analysis |
| `dangerous_command` patterns | `approval.py` | Pattern-based dangerous command detection; per-session approval state with smart LLM-based auto-approval |
| `tool_error()`, `tool_result()` | `registry.py` | JSON serialization helpers for all tool handlers; eliminate boilerplate error formatting |

---

## 3. REPRESENTATIVE SNIPPETS

### 3.1 Tool Registry — Central Dispatch (registry.py:241-258)

```python
def dispatch(self, name: str, args: dict, **kwargs) -> str:
    """Execute a tool handler by name.
    
    * Async handlers are bridged automatically via ``_run_async()``.
    * All exceptions are caught and returned as ``{"error": "..."}``
      for consistent error format.
    """
    entry = self.get_entry(name)
    if not entry:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        if entry.is_async:
            from model_tools import _run_async
            return _run_async(entry.handler(args, **kwargs))
        return entry.handler(args, **kwargs)
    except Exception as e:
        logger.exception("Tool %s dispatch error: %s", name, e)
        return json.dumps({"error": f"Tool execution failed: {type(e).__name__}: {e}"})
```

**Why:** Single entry point for all tool invocations; async support without requiring async/await at the tool level; consistent error serialization.

### 3.2 Environment Polymorphism — Session Snapshot (environments/base.py:330-349)

```python
def _wrap_command(self, command: str, cwd: str) -> str:
    """Build the full bash script that sources snapshot, cd's, runs command,
    re-dumps env vars, and emits CWD markers."""
    escaped = command.replace("'", "'\\''")
    
    parts = []
    
    # Source snapshot (env vars from previous commands)
    if self._snapshot_ready:
        parts.append(f"source {self._snapshot_path} 2>/dev/null || true")
    
    # cd to working directory
    quoted_cwd = (
        shlex.quote(cwd) if cwd != "~" and not cwd.startswith("~/") else cwd
    )
    parts.append(f"cd {quoted_cwd} || exit 126")
    
    # Run the actual command
    parts.append(f"eval '{escaped}'")
    parts.append("__hermes_ec=$?")
```

**Why:** Each backend inherits unified snapshot/CWD/exit-code handling; backends only implement `_run_bash()`, not command wrapping; CWD persists via markers.

### 3.3 File Operations — Shell-Based Abstraction (file_operations.py:27-34)

```python
# Read a file
result = file_ops.read_file("/path/to/file.py")

# Write a file
result = file_ops.write_file("/path/to/new.py", "print('hello')")

# Search for content
result = file_ops.search("TODO", path=".", file_glob="*.py")
```

**Why:** Unified API works across all backends (local, Docker, SSH, Modal, etc.) because operations are expressed as shell commands via `env.execute()`.

### 3.4 Tool Result Persistence — Defense Against Context Overflow (tool_result_storage.py:1-23)

```
# Layer 1: Per-tool output cap (inside each tool)
# Layer 2: Per-result persistence (if > threshold, write to /tmp/hermes-results/{id}.txt)
# Layer 3: Per-turn aggregate budget (if total > 200K, spill largest results to disk)

# The model can read_file to access the full output
<persisted-output>
Preview of first 1.5 KB...
[Full output (325 KB) saved to /tmp/hermes-results/tool_use_id_xyz.txt]
</persisted-output>
```

**Why:** Three-layer defense prevents context-window overflow; per-tool/turn budgets are configurable; model retains read_file access.

### 3.5 Tool Registration Pattern — Every tool file (e.g., web_tools.py)

```python
registry.register(
    name="web_search",
    toolset="web",
    schema=WEB_SEARCH_SCHEMA,
    handler=lambda args, **kw: web_search_tool(args.get("query", ""), limit=5),
    check_fn=check_web_api_key,
    requires_env=_web_requires_env(),
    emoji="🔍",
    max_result_size_chars=100_000,
)
```

**Why:** Declarative registration at module import; check_fn gates tool availability; emoji + max_result_size are registry metadata.

---

## 4. DATA FLOW

### 4.1 Tool Registration & Dispatch

```
Tool Module Import (e.g., web_tools.py)
    ↓
registry.register(name, toolset, schema, handler, check_fn, ...)
    ↓
ToolRegistry._tools[name] = ToolEntry(...)
ToolRegistry._toolset_checks[toolset] = check_fn
    
LLM requests tool call
    ↓
model_tools.dispatch("tool_name", {"arg1": "val1", ...})
    ↓
registry.dispatch("tool_name", args)
    ↓
entry = registry.get_entry("tool_name")
    ↓
if check_fn failed → skip tool (return error)
    ↓
entry.handler(args, **kwargs) → returns JSON string
    ↓
Async? → _run_async() bridges coroutine → waits for result
    ↓
Exception? → catch + serialize as {"error": "..."}
    ↓
Return JSON string to model
```

### 4.2 File Operations Across Backends

```
Agent calls: read_file("/path/to/file")
    ↓
file_tools.read_file(path)
    ↓
ShellFileOperations.read_file(path)
    ↓
terminal_env.execute(f"cat {shlex.quote(path)}")
    ↓
Backend-Specific Execution:
    Local: subprocess.Popen(["bash", "-c", cmd])
    Docker: docker exec -i container bash -c cmd
    SSH: ssh host "bash -c cmd"
    Modal: call_stub(cmd)
    Daytona: HTTP POST /execute
    ↓
Command output → parsed as JSON or text
    ↓
If result > max_read_chars → persist + return preview
    ↓
Return {"success": true, "content": "..."}
```

### 4.3 Tool Result Persistence Decision Tree

```
Tool returns result (str)
    ↓
Size = len(result)
    ↓
If size > registry.get_max_result_size(tool_name):
    [PER-RESULT PERSISTENCE]
    ↓
    Write to /tmp/hermes-results/{tool_use_id}.txt
    Generate preview (first 1.5 KB)
    Return: <persisted-output>preview...[full output saved to ...]
    ↓
Else if size <= threshold:
    [INLINE RESULT]
    Return result as-is
    ↓
After all tools in turn collected:
    Aggregate size = sum(all_result_sizes)
    ↓
    If aggregate > turn_budget (200K):
        [PER-TURN BUDGET ENFORCEMENT]
        ↓
        Sort results by size (largest first)
        ↓
        For each unpersisted result:
            If removing it gets under budget:
                Persist it + replace with preview
            ↓
        Return model with mixed inline + persisted results
```

### 4.4 Environment Selection & Execution

```
Terminal Tool Invoked (terminal_tool.terminal(cmd, env="docker"))
    ↓
Resolve env type from:
    1. env param
    2. TERMINAL_ENV env var
    3. config.yaml terminal.default_backend
    4. Fallback to "local"
    ↓
Match environment:
    "local" → LocalEnvironment(cwd, timeout)
    "docker" → DockerEnvironment(image, cwd, timeout)
    "modal" → ModalEnvironment (direct or managed gateway)
    "ssh" → SSHEnvironment(host, user, key)
    "singularity" → SingularityEnvironment(sif_path)
    "daytona" → DaytonaEnvironment(api_url)
    ↓
env.init_session() → capture bash environment snapshot
    ↓
env.execute(cmd, cwd, timeout, ...)
    ↓
_wrap_command(cmd, cwd)
    - Source snapshot (env vars, functions, aliases)
    - cd to cwd
    - eval command
    - Capture exit code + stdout
    ↓
_wait_for_process(proc, timeout)
    - Poll for completion or timeout
    - Check is_interrupted() → SIGTERM if user interrupted
    - Enforce hard timeout
    ↓
Parse output markers (CWD, exit code)
    ↓
return {"returncode": 0, "stdout": "...", "cwd": "..."}
```

---

## 5. CONFIG/KNOBS (12+ Parameters)

| Parameter | File | Type | Purpose |
|-----------|------|------|---------|
| `TERMINAL_ENV` | terminal_tool.py | env var | Backend selection: local, docker, modal, ssh, singularity, daytona |
| `TERMINAL_MAX_FOREGROUND_TIMEOUT` | terminal_tool.py | env var (int) | Hard cap on foreground command timeout (seconds); default 600 |
| `TERMINAL_DISK_WARNING_GB` | terminal_tool.py | env var (float) | Disk usage warning threshold in GB; default 500 |
| `TERMINAL_SANDBOX_DIR` | environments/base.py | env var (path) | Host-side root for sandboxes; default HERMES_HOME/sandboxes |
| `HERMES_CHECKPOINT_TIMEOUT` | checkpoint_manager.py | env var (int) | Git subprocess timeout for snapshots; clamped to [10, 60]; default 30 |
| `file_read_max_chars` | file_tools.py | config.yaml | Max chars per read_file call; default 100K (≈25–35K tokens) |
| `web.backend` | web_tools.py | config.yaml | Web backend: exa, firecrawl, parallel, tavily |
| `mcp_servers` | mcp_tool.py | config.yaml | Dict of MCP server configs (stdio/HTTP, env vars, timeouts, OAuth) |
| `code_execution.timeout` | code_execution_tool.py | config.yaml | Sandbox script timeout; default 300 seconds |
| `code_execution.max_tool_calls` | code_execution_tool.py | config.yaml | Max tool invocations within sandbox; default 50 |
| `delegation.max_concurrent_children` | delegate_tool.py | config.yaml | Max parallel subagents; default 3 |
| `tts.provider` | tts_tool.py | config.yaml | TTS backend: edge, elevenlabs, openai, mistral, minimax, neutts |
| `HERMES_VISION_DOWNLOAD_TIMEOUT` | vision_tools.py | env var (float) | Image download timeout; default 30s |
| `TOOL_GATEWAY_USER_TOKEN` | managed_tool_gateway.py | env var | Nous access token override for tool gateway |

---

## 6. INTERACTIONS

### 6.1 Module Dependencies (Import Chain)

```
registry.py (no imports from model_tools or tool files)
    ↓ Imported by
tools/*.py (web_tools, terminal_tool, etc.)
    ↓ Imported by
model_tools.py (queries registry + dispatches)
    ↓ Imported by
run_agent.py, cli.py, batch_runner.py, gateway.py
```

### 6.2 Cross-Module Interfaces

| From | To | Via | Purpose |
|------|-----|-----|---------|
| All tools | `registry` | `registry.register()` | Declare schema, handler, toolset at module import |
| terminal_tool | environments/* | `BaseEnvironment.execute()` | Run commands in different backends |
| file_tools | file_operations | `ShellFileOperations` | Unified file API via shell commands |
| code_execution_tool | terminal_tool | `_active_environments` | RPC back to parent for tool dispatch (local: UDS, remote: file-based) |
| delegate_tool | AIAgent | `subagent = AIAgent(toolset=restricted)` | Spawn child agents with isolated context |
| web_tools | auxiliary_client | `async_call_llm()` | Intelligent content extraction via cheap model |
| skills_tool, skill_manager_tool | skills_hub, skills_guard | `scan_skill()`, `should_allow_install()` | Security scanning + installation policy |
| mcp_tool | registry | `registry.register/deregister` | Dynamic tool discovery on MCP server list_changed |
| approval | gateway.session_context | `get_session_env()` | Per-session approval state in concurrent gateway |
| tool_result_storage | budget_config | `BudgetConfig.resolve_threshold()` | Resolve per-tool result size caps |
| memory_tool | file system | `HERMES_HOME/memories/*.md` | Persistent memory files (system prompt injected) |
| checkpoint_manager | git | `subprocess.run(["git", ...])` | Shadow git repos for transparent snapshots |

### 6.3 External Provider Integration

- **MCP Servers** → mcp_tool.py → discover tools, run sampling LLM, OAuth auth
- **Modal Cloud** → environments/modal.py → persistent filesystems, managed gateway
- **Web Backends** → web_tools.py → Firecrawl, Tavily, Exa, Parallel
- **LLM Providers** → auxiliary_client → OpenRouter, Nous, Codex, Anthropic
- **TTS/Voice** → tts_tool.py, voice_mode.py → Edge, ElevenLabs, OpenAI, Mistral, NeuTTS
- **Image Generation** → image_generation_tool.py → FAL.ai (FLUX + Clarity Upscaler)
- **Transcription** → transcription_tools.py → Whisper, Groq, etc.
- **Vision** → vision_tools.py → auxiliary vision router (OpenRouter, Nous, etc.)

---

## 7. TERMINOLOGY

1. **Toolset** — Logical grouping of related tools (e.g., "terminal", "web", "file", "skills", "mcp-github")
2. **Check Function (check_fn)** — Optional callable that returns bool; gates tool availability (e.g., "API key present?")
3. **ToolEntry** — Metadata struct storing tool's name, schema, handler, check_fn, requires_env, etc.
4. **Registry** — Thread-safe singleton collecting all tool entries; main dispatch hub
5. **Handler** — Callable that executes a tool; returns JSON string; may be sync or async
6. **Schema** — JSON Schema (OpenAI function calling format) describing tool parameters
7. **Environment** — Backend for command execution (Local, Docker, SSH, Modal, Singularity, Daytona)
8. **Session Snapshot** — Bash environment (exports, functions, aliases) captured once, sourced before each command
9. **CWD Tracking** — Persistent working directory across session via markers or temp files
10. **Spawn-per-Call** — Each command spawns a fresh bash process (no persistent shell session)
11. **Tool Result Persistence** — Writing large tool outputs to sandbox disk instead of context window
12. **Per-Result Budget** — Individual tool output size threshold (default 100K chars)
13. **Per-Turn Budget** — Aggregate size limit for all tool results in one LLM turn (default 200K chars)
14. **Skill** — Reusable procedural knowledge captured in ~/.hermes/skills/skill_name/SKILL.md
15. **Hub** — Registry of community/official skills (manifest, quarantine, audit log, taps)
16. **MCP** — Model Context Protocol; external tool/resource protocol via stdio/HTTP
17. **Managed Gateway** — Nous-hosted tool gateway for subscribers (Firecrawl, image gen, TTS, etc.)
18. **Approval** — Per-session dangerous command detection + interactive/auto-approval
19. **Checkpoint** — Transparent filesystem snapshot via shadow git repo (for rollback)
20. **PKCE** — Proof Key for Code Exchange; secure OAuth 2.1 flow used by MCP OAuth

---

## 8. ARCHITECTURAL PATTERNS

### 8.1 **Registry Pattern** (registry.py)
- **Why:** Decouples tool implementation from dispatch mechanism; supports dynamic registration (MCP servers can add/remove tools at runtime); thread-safe mutations via RWLock.
- **Evidence:** `ToolRegistry` with thread-safe `_tools` dict, `register/deregister` methods, snapshots for readers, `dispatch()` for invocation.

### 8.2 **Polymorphism via Inheritance** (environments/base.py)
- **Why:** LocalEnvironment, DockerEnvironment, ModalEnvironment, SSHEnvironment all inherit from BaseEnvironment; each implements only `_run_bash()`, reusing snapshot/CWD/timeout logic.
- **Evidence:** Abstract `BaseEnvironment` with `_wrap_command()`, `init_session()`, `execute()` shared; 7 subclasses override only backend-specific `_run_bash()`.

### 8.3 **Adapter Pattern** (skills_hub.py → SkillSource)
- **Why:** Unified interface for different skill registry sources (bundled, GitHub repo, official hubs); each adapter implements `SkillSource` ABC.
- **Evidence:** `SkillSource` abstract class, `OptionalSkillSource`, `GitHubSource`, `HubLockFile` tracking provenance.

### 8.4 **3-Layer Defense** (tool_result_storage.py)
- **Why:** Defense-in-depth against context-window overflow: per-tool cap, per-result persistence, per-turn aggregate budget.
- **Evidence:** `maybe_persist_tool_result()` checks tool threshold; `enforce_turn_budget()` spills largest results to disk.

### 8.5 **Lazy Loading** (various tools)
- **Why:** Avoid import failures on headless systems (SSH, Docker, no PortAudio); import only when actually needed.
- **Evidence:** `_import_audio()`, `_import_edge_tts()`, `_import_elevenlabs()` in tts_tool.py, voice_mode.py; helpers catch ImportError/OSError gracefully.

### 8.6 **Session Snapshot Caching** (environments/base.py)
- **Why:** Environment setup (env vars, functions) is expensive; capture once at init_session(), source before each command; avoids `bash -l` overhead per call.
- **Evidence:** `_snapshot_ready` flag, `_wrap_command()` sources snapshot, CWD file updated after each command.

### 8.7 **Trust-Aware Security Scanning** (skills_guard.py)
- **Why:** Different threat levels for different sources (builtin, trusted, community, agent-created); regex-based static analysis; install policy matrix.
- **Evidence:** `INSTALL_POLICY` dict, `ScanResult.verdict`, `should_allow_install()` checks trust level + verdict.

### 8.8 **Manifest-Based Sync** (skills_sync.py)
- **Why:** Track bundled skills' origin hashes; only update if user hasn't customized; respect user deletions.
- **Evidence:** `MANIFEST_FILE` with v1/v2 format, `_read_manifest()` deduplicates, sync logic compares hashes.

---

## 9. ALGORITHMS & MECHANISMS

### 9.1 **CWD Persistence Across Spawn-Per-Call**
- **Problem:** Each command spawns a fresh bash process; how does CWD persist?
- **Solution:**
  1. Write `pwd -P > /tmp/hermes-cwd-{session_id}.txt` at end of each command
  2. Before next command, read that file and use it as the default CWD
  3. Emit CWD markers in output (`__HERMES_CWD_{session_id}__`) so remote backends can parse it
  4. For local backend, parse markers; for remote (Modal, Daytona), read the temp file

### 9.2 **Interrupt-Safe Execution**
- **Problem:** Long-running commands should respond immediately to user interrupts.
- **Solution:**
  1. `interrupt.py` exposes `is_interrupted()` context var + `_interrupt_event` threading.Event
  2. `_wait_for_process()` polls `is_interrupted()` every 0.5s
  3. On interrupt, send SIGTERM to subprocess (or equivalent for remote backends)
  4. Cleanup thread cleans up inactive environments after idle threshold

### 9.3 **Async Tool Support Without Coroutine Leakage**
- **Problem:** Some tools are async (web_extract, vision_analyze), but tool handlers must return str (not coroutines).
- **Solution:**
  1. Handler returns `Coroutine[str]` (awaitable)
  2. `registry.dispatch()` checks `entry.is_async`, calls `_run_async(coro)` from model_tools.py
  3. `_run_async()` bridges to thread-local event loop or new event loop
  4. Model never sees coroutine, only final JSON string result

### 9.4 **Result Persistence Decision Algorithm**
```
For each tool result:
  size = len(result)
  threshold = registry.get_max_result_size(tool_name)
  
  if size > threshold:
    preview = result[:1500] + "\n..."
    path = /tmp/hermes-results/{tool_use_id}.txt
    env.execute(f"cat > {path} << EOF\n{result}\nEOF")
    return_to_model = <persisted-output>
                      {preview}
                      [Full output ({size} bytes) saved to {path}]
                      </persisted-output>
  else:
    return_to_model = result

After all tools:
  aggregate = sum(len(r) for r in all_return_to_model)
  budget = 200_000  # chars
  
  if aggregate > budget:
    results_sorted = sorted(all_results, key=len, reverse=True)
    for r in results_sorted:
      if not r.is_persisted():
        persist(r)
        if aggregate - len(r) <= budget:
          break
```

### 9.5 **MCP Dynamic Tool Discovery**
- **Problem:** MCP servers can be added/removed at runtime; tool list can change.
- **Solution:**
  1. MCP server sends `notifications/tools/list_changed`
  2. mcp_tool.py calls `list_tools()` on server
  3. For each tool, call `registry.deregister(old_name)` if exists
  4. For each new tool, `registry.register(name, toolset="mcp-{server_name}", schema, handler, ...)`
  5. Thread-safe via registry RWLock; readers get stable snapshots during mutation

---

## 10. ERROR/EDGE CASES

### 10.1 **Blocked Device Paths** (file_tools.py)
```python
_BLOCKED_DEVICE_PATHS = frozenset({
    "/dev/zero", "/dev/random", "/dev/urandom",  # infinite output
    "/dev/stdin", "/dev/tty",                    # blocks on input
})

# Check before read_file() to avoid hanging
if _is_blocked_device(filepath):
    return tool_error("Cannot read from device (would hang)")
```
**Fallback:** Deny read, return error message; never attempt I/O.

### 10.2 **Write Deny List** (file_operations.py)
```python
WRITE_DENIED_PATHS = {
    ~/.ssh/authorized_keys, ~/.ssh/id_rsa,
    ~/.hermes/.env, ~/.bashrc, ~/.zshrc, /etc/sudoers, ...
}
WRITE_DENIED_PREFIXES = {
    ~/.ssh/, ~/.aws/, ~/.docker/, ~/.kube/, /etc/sudoers.d/, ...
}

if _is_write_denied(path):
    return tool_error("Write target is protected")
```
**Fallback:** Deny write, return error; check prefix walk to catch directory escapes.

### 10.3 **Dangerous Command Approval** (approval.py)
```
DANGEROUS_PATTERNS = [
    r'\brm\s+(-[^\s]*\s+)*/',  # delete in root
    r'\bchmod\s+(-[^\s]*\s+)*(777|666|o\+w)',  # world-writable
    r'\bsudo\s+',  # sudo without args
    ...
]

If pattern matches:
  1. Try smart LLM-based auto-approval (low-risk check)
  2. If passes → execute
  3. If fails → prompt user (CLI) or log (gateway)
  4. Remember per-session (allowlist)
```
**Fallback:** Log+warn, don't execute; let user re-phrase or approve explicitly.

### 10.4 **MCP Connection Failures** (mcp_tool.py)
```
Try to connect with exponential backoff (up to 5 retries)

If connection fails:
  Return error to model, skip MCP toolset
  Existing (non-MCP) tools still work

If sampling (LLM call from MCP server) fails:
  Log error, return "tool unavailable" to server
  Don't crash the MCP task
```
**Fallback:** Graceful degradation; MCP toolset unavailable but agent continues.

### 10.5 **Sandbox Process Timeout** (environments/base.py)
```
def _wait_for_process(proc, timeout):
  deadline = time.time() + timeout
  while time.time() < deadline:
    if is_interrupted():
      proc.terminate()
      return {"error": "interrupted"}
    if proc.poll() is not None:
      return parse_output()
    time.sleep(0.5)
  
  # Timeout reached
  proc.kill()
  return {"error": "command timeout", "returncode": -1}
```
**Fallback:** SIGTERM → 5s grace → SIGKILL; no hanging.

### 10.6 **Large File Reads** (file_tools.py)
```
if file_size > _LARGE_FILE_HINT_BYTES (512 KB):
  if limit is None or limit > 200:  # caller didn't specify narrow range
    include_hint: "File is large; use offset+limit for targeted reads"

if content_length > max_read_chars (100 KB):
  truncate_at_newline()
  include_note: "[Output truncated; use offset+limit to read sections]"
```
**Fallback:** Include hints; let model re-request with targeted range.

### 10.7 **OAuth Token Expiration** (mcp_oauth.py)
```
def read_nous_access_token():
  cached = load_from_auth_json()
  if cached and not is_expiring(cached.expires_at, skew=120s):
    return cached
  
  # Refresh via hermes_cli.auth.resolve_nous_access_token()
  new_token = refresh_token()
  return new_token or cached or None
```
**Fallback:** Attempt refresh; fall back to cached; if both fail, OAuth unavailable.

---

## 11. DESIGN DECISIONS

### 11.1 **Why Spawn-Per-Call Instead of Persistent Shell?**
- **Decision:** Each command spawns fresh bash, sources snapshot before each.
- **Rationale:**
  - Eliminates shell state pollution (one command's side effects don't affect others)
  - Backends (Docker, SSH, Modal) already pay connection cost; spawning a bash process is cheap
  - Snapshot captures env vars + functions; CWD persists via file tracking
  - Easier to enforce timeouts and interrupt handling per-call
  - Remote backends naturally align with this model (HTTP API, Modal stubs)

### 11.2 **Why 3-Layer Result Persistence Instead of Single Global Cap?**
- **Decision:** Per-tool threshold, per-turn budget, per-result preview size.
- **Rationale:**
  - Per-tool allows search_files (inherently huge) to be capped higher than read_file
  - Per-turn budget catches cases where 5 medium-sized results overflow context
  - Preview size (1.5 KB) balances readability + token efficiency
  - Model can read_file() to access persisted content; no loss of information

### 11.3 **Why Registry Instead of Hardcoded ToolList?**
- **Decision:** Thread-safe registry with dynamic register/deregister.
- **Rationale:**
  - MCP servers need to add/remove tools without restarting agent
  - Tools are scattered across 50+ modules; centralized registry avoids maintaining parallel lists
  - Thread-safe mutations protect against concurrent gateway requests
  - Snapshots ensure readers see stable state during updates

### 11.4 **Why Security Scanning Before Skill Installation?**
- **Decision:** Regex-based static analysis; trust-level-aware policy (builtin > trusted > community).
- **Rationale:**
  - Externally-sourced code is inherently risky (exfiltration, persistence, destructive)
  - Regex patterns catch obvious red flags without requiring sandboxed execution
  - Trust levels reduce false positives (OpenAI/Anthropic skills get looser thresholds)
  - Scanner is the single source of truth; prevents users from bypassing checks

### 11.5 **Why Manifest-Based Sync Instead of Overwriting User Skills?**
- **Decision:** Track origin hash; only update if user hasn't customized.
- **Rationale:**
  - User customizations shouldn't be lost on agent update
  - Manifest lets us detect user modifications (hash mismatch)
  - Respect user deletions (don't re-add deleted skills)
  - Support migration from v1 to v2 format

---

## 12. SUMMARY

The `tools/` module is a **production-grade orchestration layer** for an AI agent. It demonstrates:

- **Abstraction mastery:** 7 execution backends under one interface (BaseEnvironment)
- **Safety hardening:** Write blocklists, dangerous command approval, skill scanning, OAuth
- **Performance optimization:** Session snapshots, lazy imports, result persistence, token-efficient summarization
- **Extensibility:** Thread-safe registry supports MCP dynamic tool discovery, skill hubs, adapters
- **Observability:** Debug logging, approval audit trails, checkpoint history
- **Reliability:** Graceful degradation, exponential backoff, timeout enforcement, error coalescing

The module's design reflects hard-won lessons about deploying autonomous agents: **tools must be safe, fast, transparent, and resilient.**