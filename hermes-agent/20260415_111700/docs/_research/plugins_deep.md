# Comprehensive Analysis: Hermes Agent Module Architecture

## Module 1: plugins/ — Plugin System

### Purpose
The plugins system provides a dynamic plugin discovery and loading infrastructure for **context engines** and **memory providers**. These are built-in extensible backends (context compression, user memory) that live in the repo and are always available without external installation. Each system (context, memory) can have only ONE active instance at a time, selected via `config.yaml`.

### Key Classes/Functions

1. **`discover_context_engines()`** — Scans `plugins/context_engine/` for available engines, returns (name, description, available) tuples without importing
2. **`load_context_engine(name)`** — Dynamic import and instantiation of context engine by name; supports both `register(ctx)` pattern and direct class subclass detection
3. **`_load_engine_from_dir(engine_dir)`** — Core importlib machinery: registers parent packages in sys.modules, handles relative imports, executes module spec
4. **`discover_memory_providers()`** — Mirror of context_engines for memory backends; scans `plugins/memory/<name>/`, checks `plugin.yaml` metadata
5. **`load_memory_provider(name)`** — Load memory provider by name; captures via `_ProviderCollector` if using `register()` pattern
6. **`_EngineCollector`, `_ProviderCollector`** — Fake plugin contexts that capture `register_context_engine()` / `register_memory_provider()` calls
7. **`discover_plugin_cli_commands()`** — Returns CLI commands for the **active** memory provider only by reading its `cli.py` and calling `register_cli(subparser)`
8. **`_get_active_memory_provider()`** — Lightweight config read to detect which provider is active; used to avoid loading unused plugins

### Representative Snippets

**Snippet 1: Dynamic module loading with submodule registration**
```python
# From plugins/memory/__init__.py
spec = importlib.util.spec_from_file_location(
    module_name, str(init_file),
    submodule_search_locations=[str(provider_dir)]
)
mod = importlib.util.module_from_spec(spec)
sys.modules[module_name] = mod
# Register submodules for relative imports (e.g., "from .store import MemoryStore")
for sub_file in provider_dir.glob("*.py"):
    if sub_file.name != "__init__.py":
        sub_spec = importlib.util.spec_from_file_location(full_sub_name, str(sub_file))
        sub_mod = importlib.util.module_from_spec(sub_spec)
        sys.modules[full_sub_name] = sub_mod
        sub_spec.loader.exec_module(sub_mod)
spec.loader.exec_module(mod)
```

**Snippet 2: Dual-mode plugin extraction — support both register() and direct class subclass**
```python
# From plugins/memory/__init__.py - fallback after register() fails
if hasattr(mod, "register"):
    collector = _ProviderCollector()
    mod.register(collector)
    if collector.provider:
        return collector.provider
# Fallback: find MemoryProvider subclass and instantiate
from agent.memory_provider import MemoryProvider
for attr_name in dir(mod):
    attr = getattr(mod, attr_name, None)
    if (isinstance(attr, type) and issubclass(attr, MemoryProvider)
            and attr is not MemoryProvider):
        return attr()
```

**Snippet 3: CLI command discovery for active plugin only**
```python
# From plugins/memory/__init__.py
active_provider = _get_active_memory_provider()  # Read config, don't load plugin yet
if not active_provider:
    return []
cli_file = _MEMORY_PLUGINS_DIR / active_provider / "cli.py"
if cli_file.exists():
    # Import only cli.py (lightweight, no SDK needed)
    spec = importlib.util.spec_from_file_location(module_name, str(cli_file))
    cli_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli_mod)
    register_cli = getattr(cli_mod, "register_cli", None)
```

### Data Flow

```
config.yaml (context.engine, memory.provider)
            ↓
discover_*() — scan filesystem, read plugin.yaml, check availability
            ↓
load_*() — importlib.util.spec_from_file_location() chain
            ↓
module imported → call register(collector) OR find subclass
            ↓
ContextEngine / MemoryProvider instance returned
```

Memory and context backends live in their own subdirs; only ONE is active at runtime. CLI commands are scoped to the active provider and loaded on-demand.

### Config/Knobs

- **`config.yaml: context.engine`** — Name of active context engine (e.g., "compressor", "lcm")
- **`config.yaml: memory.provider`** — Name of active memory provider (e.g., "honcho", "holographic", "mem0")
- **`plugin.yaml` per plugin** — YAML metadata: `description`, availability flags
- **Environment variables** — Plugins can read env vars for API keys, credentials (e.g., `HONCHO_API_KEY`, `MEM0_API_KEY`)

### Interactions with other modules

- **Interactions**: Config system (`hermes_cli.config`), runtime provider detection (`hermes_cli.runtime_provider`)
- **Used by**: AIAgent initialization (loads active memory provider as a tool), CLI setup (loads active provider's CLI commands)
- **CLI bridge**: CLI commands registered by active memory plugin are merged into main argparse

### Architectural Patterns and WHY

1. **Registry + Lazy Loading** — Only import the active provider to avoid dependency bloat. Registry pattern allows multiple implementations without hard-coding.
2. **Dual interface (register() + subclass)** — Supports both declarative plugin style (`register(ctx)`) and imperative class-based style, maximizing compatibility.
3. **Importlib + sys.modules management** — Dynamic imports with parent package registration ensure relative imports within plugins work cross-platform.
4. **Availability checks without import** — `plugin.yaml` + lightweight checks prevent loading broken backends.
5. **Single-active pattern** — Only ONE context engine and ONE memory provider can be active. Enforced at load time, simplifies agent initialization.

### Design Decisions

1. **Plugin discovery is *eager*, loading is *lazy*** — Discover all plugins at startup (cheap filesystem scan), import only the active one. Allows fast CLI help without importing heavy dependencies (Honcho SDK, Mem0 client, etc.).
2. **Register() pattern mirrors user plugins** — Hermes has a general plugin system for tools/hooks; context/memory use the same `register(ctx)` interface for consistency even though they're built-in.
3. **CLI commands scoped to active provider** — Only register CLI subcommands for the active memory provider. Avoids conflicting commands and keeps CLI clean.
4. **No partial loading** — If a plugin's `__init__.py` fails to load, the entire plugin is unavailable. Prevents silent fallbacks hiding configuration errors.
5. **sys.modules registration before exec_module()** — Ensures relative imports within the plugin see themselves in sys.modules before execution, preventing ImportError loops.

### Existence Rationale

- **Why separate from general plugin system?** Context engines and memory providers are *always* available built-in backends, not third-party installables. They need fast discovery without pip dependencies.
- **Why single-active?** Both solve orthogonal problems (context compression vs. user memory), but agent initialization needs a single, deterministic behavior. Mixing strategies would complicate the API surface.
- **Why plugin.yaml + discovery?** User-facing CLI needs to show "what providers are available and which is active" without loading anything. This is cheap information read from YAML.

### Error Philosophy

- **Graceful degradation**: `discover_*()` skips plugins that fail availability checks; doesn't crash if a plugin directory is malformed.
- **Warnings, not errors**: `logger.warning()` for load failures; `logger.debug()` for import internals.
- **Availability checks are **non-fatal**: A missing API key (e.g., `MEM0_API_KEY`) marks the provider as unavailable; it doesn't prevent discovery or CLI help.
- **Backward compatibility**: Supports both `register()` and class-subclass patterns so old and new plugins coexist.

### Evolution Clues

- **plugin.yaml convention** — Metadata standard suggests plans for marketplace/registry of plugins.
- **CLI discovery separate from provider loading** — CLI commands can exist without the full SDK; suggests plans for lighter-weight CLI in resource-constrained environments.
- **_ProviderCollector pattern** — Simulates a plugin context without the full framework; suggests potential future refactor to unify user + built-in plugins.
- **Multi-skill support in cron jobs** — Cron module normalizes `skill` → `skills[]`, suggesting memory/context engines may also support chaining or composition in the future.

---

## Module 2: environments/ — RL Training Environments

### Purpose
Integrates hermes-agent's tool-calling capabilities with the Atropos RL training framework. Provides a layered abstraction that bridges the agent's OpenAI-spec tool calling with Atropos dataset rollouts, reward scoring, and training loops. Supports two operational modes: Phase 1 (OpenAI server) and Phase 2 (VLLM ManagedServer with client-side tool call parsing).

### Key Classes/Functions

1. **`HermesAgentLoop`** — Reusable multi-turn agent engine; runs tool-calling loop with standard OpenAI-spec tools parameter, dispatches via `handle_function_call()` from `model_tools.py`
2. **`AgentResult`** — Dataclass capturing loop outcome: messages, turns used, finished naturally, reasoning per turn, tool errors
3. **`ToolContext`** — Per-rollout handle giving reward functions unrestricted access to ALL hermes tools (terminal, file, web, browser) scoped to rollout's task_id
4. **`HermesAgentBaseEnv`** — Abstract BaseEnv subclass for Atropos; orchestrates agent loop, ToolContext creation, ScoredDataGroup construction
5. **`HermesAgentEnvConfig`** — Pydantic config: toolsets, terminal backend, agent loop params, dataset config
6. **`resize_tool_pool(max_workers)`** — Resize the global tool thread executor at runtime; called by `__init__()` based on config
7. **`ToolError`** — Tracks tool execution failures during loop: turn, tool_name, arguments, error message, result returned
8. **`apply_patches()`** — Monkey-patch compatibility layer for async-safe tool execution inside Atropos event loop

### Representative Snippets

**Snippet 1: AgentResult dataclass structure**
```python
# From environments/agent_loop.py
@dataclass
class AgentResult:
    messages: List[Dict[str, Any]]  # Full conversation history in OpenAI message format
    managed_state: Optional[Dict[str, Any]] = None  # ManagedServer.get_state() if available
    turns_used: int = 0  # How many LLM calls
    finished_naturally: bool = False  # Model stopped calling tools vs hitting max_turns
    reasoning_per_turn: List[Optional[str]] = field(default_factory=list)  # From PR #297
    tool_errors: List[ToolError] = field(default_factory=list)  # Tool failures during loop
```

**Snippet 2: ToolContext provides unrestricted tool access for reward verifiers**
```python
# From environments/tool_context.py
class ToolContext:
    """Open-ended access to all hermes-agent tools for a specific rollout."""
    def __init__(self, task_id: str):
        self.task_id = task_id
    
    def terminal(self, command: str) -> str:
        """Run terminal command in rollout's task sandbox."""
        return _run_tool_in_thread("terminal", {"command": command}, self.task_id)
    
    def read_file(self, path: str) -> Dict[str, Any]:
        """Read file from rollout's task sandbox."""
        return _run_tool_in_thread("read_file", {"path": path}, self.task_id)
```

**Snippet 3: HermesAgentBaseEnv config excerpt**
```python
# From environments/hermes_base_env.py
class HermesAgentEnvConfig(BaseEnvConfig):
    enabled_toolsets: Optional[List[str]] = Field(default=None)
    distribution: Optional[str] = Field(default=None)
    max_agent_turns: int = Field(default=30)
    system_prompt: Optional[str] = Field(default=None)
    terminal_backend: str = Field(default="local")  # local, docker, modal, daytona, ssh, singularity
    terminal_timeout: int = Field(default=120)
    terminal_lifetime: int = Field(default=3600)
```

### Data Flow

```
Atropos rollout asks for next item
            ↓
get_next_item() → returns dataset item
            ↓
format_prompt() → convert item to user message
            ↓
HermesAgentLoop runs agent:
  - calls LLM with tools=
  - parses response.choices[0].message.tool_calls
  - calls handle_function_call() for each tool
  - loops until max_turns or natural stop
            ↓
AgentResult: messages, turns_used, finished_naturally, tool_errors
            ↓
ToolContext created for compute_reward():
  - reward verifier runs tools against rollout's task_id
  - terminal/file/web operations replay in same sandbox
            ↓
compute_reward() returns score (0.0-1.0)
            ↓
ScoredDataGroup built from ManagedServer state + results
```

Task IDs ensure all tool calls for a rollout hit the same backend instance (same terminal session, browser profile, etc.).

### Config/Knobs

- **`enabled_toolsets`** — Explicit list of hermes toolsets (terminal, file, web, etc.)
- **`distribution`** — Name of toolset distribution sampled once per group (mutually exclusive with enabled_toolsets)
- **`disabled_toolsets`** — Toolsets to disable on top of enabled/distribution
- **`max_agent_turns`** — Maximum LLM calls per rollout (default: 30)
- **`terminal_backend`** — "local", "docker", "modal", "daytona", "ssh", "singularity"
- **`terminal_timeout`** — Per-command timeout in seconds (default: 120)
- **`terminal_lifetime`** — Sandbox inactivity lifetime in seconds (default: 3600)
- **`agent_temperature`** — Sampling temperature for agent generation
- **`system_prompt`** — Custom system prompt (tools handled via tools= parameter, not prompt text)

### Interactions with other modules

- **Depends on**: `model_tools.handle_function_call()`, `toolset_distributions.sample_toolsets_from_distribution()`, `tools.terminal_tool.get_active_env()`, `tools.tool_result_storage.maybe_persist_tool_result()`, Atropos (`atroposlib.envs.base.BaseEnv`)
- **Provides**: Agent loop for RL training; ToolContext for reward verifiers
- **Used by**: Hermes SWE-bench benchmarks, Terminal-Bench evaluations, custom RL training pipelines

### Architectural Patterns and WHY

1. **Two-mode operation (Phase 1 vs Phase 2)** — OpenAI server (simple, works with most LLM backends) vs. ManagedServer with client-side parsing (lower latency, better for streaming). Abstracts away differences via AgentResult.
2. **Centralized tool executor (ThreadPoolExecutor)** — Tool calls run in separate thread pool to prevent deadlock when tools use `asyncio.run()` internally (Modal, Docker, Daytona). Large pool size (128 workers) prevents thread starvation in parallel evals.
3. **ToolContext = unrestricted access** — Reward verifiers get full tool access scoped to rollout's task_id. Unlike agent-facing tools (which may be restricted by permissions/budget), verifiers need to inspect anything.
4. **Per-group toolset sampling** — Toolsets sampled once per rollout group, not per rollout, so entire groups use the same tool distribution for fair comparison.
5. **Config-driven toolset selection** — Avoid hard-coding tool lists; enables research experiments (e.g., "does web access help SWE tasks?") by swapping distributions.

### Design Decisions

1. **Task ID as isolation boundary** — All tool calls for a rollout share one task_id. Ensures terminal history, file state, browser session persist across reward checking without cross-pollination.
2. **Thread pool resizing at env init** — `resize_tool_pool()` called by HermesAgentBaseEnv.__init__() with config.tool_pool_size. Prevents starvation on high-concurrency evals but still allows per-environment tuning.
3. **AgentResult as immutable outcome** — Entire conversation history + metadata captured atomically. Makes it easy to persist, replay, analyze rollouts without querying live state.
4. **Patches module as no-op** — Original async-safety patches are no longer needed because Modal environment uses dedicated _AsyncWorker thread. Module kept for backward compat but is a no-op.
5. **System prompt not embedded in tools= parameter** — Tools are passed to the LLM separately, not concatenated into prompt text. Cleaner separation of concerns; model can optimize tool calling differently (streaming, structured output, etc.).

### Existence Rationale

- **Why separate from run_agent.py?** run_agent.py is CLI-focused (single query, interactive). Environments are RL-focused (batch rollouts, reward scoring, dataset integration).
- **Why RL framework integration?** Atropos is a production RL training framework; environments bridge agent capabilities into its data/reward/training pipeline.
- **Why ToolContext?** Reward verifiers need to inspect rollout state (did the model actually create that file? is the test passing?). Can't use the agent's tool restrictions; need full access scoped by task_id.
- **Why Phase 1 + Phase 2 abstraction?** Different backends have different latency/capability tradeoffs. Phase 1 (OpenAI API) is simple; Phase 2 (ManagedServer) is faster for dense rollouts.

### Error Philosophy

- **Tool errors are captured, not fatal** — AgentResult.tool_errors records failures (turn, tool_name, error message). Loop continues; reward function decides if error is a failure state.
- **Task cleanup is non-optional** — Try-finally in compute_reward() ensures cleanup_vm()/cleanup_browser() run regardless of verifier exceptions.
- **Thread pool backpressure** — If tool pool is saturated, LLM calls block. Better than dropping tasks silently.

### Evolution Clues

- **Phase 2 / ManagedServer abstractions** — Suggests plans to support more exotic backends (remote GPU clusters, streaming models, etc.).
- **Distribution system** — Pre-defined toolset combinations (e.g., "development", "terminal_tasks") suggest future marketplace of task-specific tool distributions.
- **Reasoning extraction (PR #297)** — `reasoning_per_turn` field suggests upcoming work on interpretability / chain-of-thought analysis of RL rollouts.
- **Tool error tracking** — AgentResult.tool_errors suggests future failure analysis pipelines (e.g., "which tools fail most often?").

---

## Module 3: cron/ — Scheduled Tasks

### Purpose
Provides a durable cron job scheduler for executing agent tasks on schedules (intervals, cron expressions, one-shot). Jobs are persisted to `~/.hermes/cron/jobs.json` and executed by the gateway daemon every 60 seconds. Supports delivery of results to messaging platforms (Telegram, Discord, Slack, etc.) or local storage. Jobs are isolated—each execution runs in a fresh session with no prior context.

### Key Classes/Functions

1. **`create_job()`** — Create a new cron job with schedule, prompt, optional skills, delivery target, origin info
2. **`get_job(job_id)`** — Retrieve a job by ID
3. **`list_jobs()`** — Return all jobs
4. **`update_job(job_id, updates)`** — Modify job fields (schedule, prompt, delivery, etc.)
5. **`remove_job(job_id)`** — Delete a job
6. **`pause_job(job_id)`, `resume_job(job_id)`** — Suspend/resume execution
7. **`trigger_job(job_id)`** — Manually trigger a job immediately
8. **`tick()`** — Main scheduler entry point; called every 60 seconds by gateway daemon
9. **`parse_schedule(schedule_str)`** — Parse "30m", "every 2h", "0 9 * * *", or ISO timestamp → structured schedule dict
10. **`compute_next_run(schedule, last_run_at)`** — Calculate next run time given schedule and last execution
11. **`mark_job_run(job_id, at_timestamp)`** — Record that a job just ran; updates `last_run_at`
12. **`save_job_output(job_id, timestamp, content, metadata)`** — Persist job output to `~/.hermes/cron/output/{job_id}/{timestamp}.md`

### Representative Snippets

**Snippet 1: Schedule parsing — supports 4 formats**
```python
# From cron/jobs.py
def parse_schedule(schedule: str) -> Dict[str, Any]:
    """Parse schedule into structured format.
    
    Returns dict with:
    - kind: "once" | "interval" | "cron"
    - For "once": "run_at" (ISO timestamp)
    - For "interval": "minutes" (int)
    - For "cron": "expr" (cron expression)
    """
    # "every X" pattern → recurring interval
    if schedule_lower.startswith("every "):
        minutes = parse_duration(schedule[6:])
        return {"kind": "interval", "minutes": minutes}
    
    # Cron expression (5+ space-separated fields)
    if len(parts) >= 5 and all(re.match(r'^[\d\*\-,/]+$', p) for p in parts[:5]):
        croniter(schedule)  # validate
        return {"kind": "cron", "expr": schedule}
    
    # ISO timestamp or duration like "30m", "2h", "1d"
    try:
        dt = datetime.fromisoformat(schedule.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.astimezone()  # interpret as local
        return {"kind": "once", "run_at": dt.isoformat()}
    except ValueError:
        pass
    
    # Duration → one-shot
    minutes = parse_duration(schedule)
    run_at = _hermes_now() + timedelta(minutes=minutes)
    return {"kind": "once", "run_at": run_at.isoformat()}
```

**Snippet 2: Delivery target resolution with origin fallback**
```python
# From cron/scheduler.py
def _resolve_delivery_target(job: dict) -> Optional[dict]:
    """Resolve the concrete delivery target for a cron job."""
    deliver = job.get("deliver", "local")
    origin = _resolve_origin(job)
    
    if deliver == "origin":
        if origin:
            return {"platform": origin["platform"], "chat_id": str(origin["chat_id"]), ...}
        # Origin missing → try each platform's home channel
        for platform_name in ("matrix", "telegram", "discord", "slack", "bluebubbles"):
            chat_id = os.getenv(f"{platform_name.upper()}_HOME_CHANNEL", "")
            if chat_id:
                return {"platform": platform_name, "chat_id": chat_id}
    
    # "deliver=telegram:alice_dm" or "deliver=discord"
    if ":" in deliver:
        platform_name, rest = deliver.split(":", 1)
        return {"platform": platform_name, "chat_id": resolve_channel_name(platform_name, rest)}
```

**Snippet 3: One-shot grace window logic**
```python
# From cron/jobs.py
def _recoverable_oneshot_run_at(schedule: Dict[str, Any], now: datetime, *, last_run_at=None) -> Optional[str]:
    """Return a one-shot run time if it is still eligible to fire.
    
    One-shot jobs get a small grace window (120 seconds) so jobs created a few 
    seconds after their requested minute still run on the next tick.
    Once a one-shot has already run, it is never eligible again.
    """
    if schedule.get("kind") != "once":
        return None
    if last_run_at:
        return None  # Already ran — never again
    
    run_at = schedule.get("run_at")
    if not run_at:
        return None
    
    run_at_dt = _ensure_aware(datetime.fromisoformat(run_at))
    if run_at_dt >= now - timedelta(seconds=ONESHOT_GRACE_SECONDS):
        return run_at
    return None
```

### Data Flow

```
User creates job (CLI/API) via create_job()
            ↓
Job persisted to ~/.hermes/cron/jobs.json
            ↓
Gateway daemon calls tick() every 60 seconds
            ↓
tick() loads all jobs, checks for due jobs:
  - For "interval": last_run + interval <= now?
  - For "cron": croniter.get_next() <= now?
  - For "once": run_at in grace window?
            ↓
Due jobs are executed:
  - Load optional skills
  - Run agent with prompt + skills in fresh session
  - Capture output to ~/.hermes/cron/output/{job_id}/{timestamp}.md
            ↓
If deliver != "local":
  - Resolve delivery target (platform + chat_id)
  - Send output to platform (Telegram, Discord, etc.) OR
  - Send via live adapter if gateway is running (supports E2EE)
            ↓
mark_job_run(job_id, timestamp) updates last_run_at
            ↓
next_run computed and stored for next tick
```

Job state is fully persistent; if gateway dies, jobs resume on restart.

### Config/Knobs

- **`cron.schedule`** — "30m", "every 2h", "0 9 * * *", "2026-02-03T14:00"
- **`cron.repeat`** — How many times to run (None = forever, 1 = once)
- **`cron.deliver`** — "local" (storage only), "origin" (back to sender), "telegram:alice_dm", "discord", "slack", platform name, or webhook URL
- **`cron.wrap_response`** — Whether to wrap output with job header (default: true)
- **`cron.script_timeout_seconds`** — Pre-run script timeout (default: 120); can be overridden by env var `HERMES_CRON_SCRIPT_TIMEOUT` or module `_SCRIPT_TIMEOUT`
- **Environment variables**: `TELEGRAM_HOME_CHANNEL`, `DISCORD_HOME_CHANNEL`, etc. — used as fallback delivery targets for jobs with no origin

### Interactions with other modules

- **Depends on**: `run_agent.AIAgent` (executes prompts), `send_message_tool` (delivery), `gateway.platforms` (platform adapters), `gateway.channel_directory` (channel name resolution), `hermes_cli.config` (job config), `hermes_time` (timezone-aware scheduling)
- **Used by**: Gateway daemon (`gateway install`), CLI commands (`hermes cron create`, `hermes cron list`, etc.)
- **Affects**: Session isolation (each job runs in fresh session), message delivery (results sent to platforms)

### Architectural Patterns and WHY

1. **Persistent JSON-based job store** — Simple, portable, no database dependency. File is atomic-written via temp file + rename to prevent corruption.
2. **File-based lock for concurrent ticks** — `~/.hermes/cron/.tick.lock` ensures only one tick runs at a time if multiple gateway instances overlap. Prevents duplicate job execution.
3. **Grace window for one-shots** — 120-second grace window allows jobs created slightly after their trigger time to still fire. Without this, jobs created at 14:00:05 with run_at=14:00:00 would never execute.
4. **Dynamic grace period for recurring jobs** — Grace seconds = half the schedule period (clamped to 120s - 2h). Daily jobs can catch up if missed by 2h; frequent jobs (5-10 min) fast-forward quickly.
5. **Delivery fallback chain** — Live adapter (if gateway running) → standalone HTTP → home channel env var. Ensures delivery even if gateway restarts or adapter is unavailable.
6. **Script injection pattern** — Optional pre-run script whose stdout is prepended to prompt. Enables data collection (e.g., stock prices, weather) to be injected at runtime without modifying the job definition.

### Design Decisions

1. **One-shot jobs never repeat** — After a one-shot runs (even if late), it's done. Prevents accidental re-execution. Can always `repeat=2` for a job that should run twice.
2. **Job output is immutable** — Output saved to timestamped file (`{job_id}/{timestamp}.md`). Prevents loss of execution history if job is re-run or modified.
3. **Fresh session per execution** — Each job runs in an isolated session with no prior context. Prevents state leakage between runs; makes jobs reproducible.
4. **Delivery is optional** — Jobs can store output locally without sending anywhere (`deliver=local`). Useful for data collection / logging without platform overhead.
5. **Platform validation prevents env var injection** — Delivery platform names checked against `_KNOWN_DELIVERY_PLATFORMS` frozenset. Prevents attacker from crafting deliver="MY_CUSTOM_EXPLOIT_VAR" to exfiltrate env vars.
6. **Skill normalization** — Both `skill` (legacy single) and `skills` (new list) supported; internally normalized to `skills[]` so multi-skill jobs work transparently.

### Existence Rationale

- **Why separate from agent core?** Cron is a daemon feature requiring persistent state and background scheduling. Keeps CLI/agent lightweight.
- **Why file-based, not database?** Portable across platforms, no schema migrations, human-readable for debugging.
- **Why JSON, not YAML?** JSON is simple and doesn't require a parser beyond stdlib. YAML's power isn't needed; structure is flat.
- **Why gateway integration?** Gateway daemon is already running as a background service (for message delivery); natural place to tick the scheduler.

### Error Philosophy

- **Delivery failures are logged but non-fatal** — If a job output can't be delivered, it's still saved locally. User can manually check `~/.hermes/cron/output/`.
- **Pre-run scripts can fail safely** — If the script times out or returns non-zero, the prompt runs anyway (not injected with script output). Job still executes.
- **Corrupt jobs.json auto-repairs** — If JSON has control characters, tries to reload with `strict=False`, auto-repairs, and rewrites. Better than data loss.
- **Missing config doesn't crash tick()** — If gateway config is unavailable or a platform is disabled, delivery silently skips (logged as warning). Job still runs.

### Evolution Clues

- **Multi-skill support** — Cron jobs support multiple skills; suggests potential for skill composition / chaining in agent core.
- **Script injection** — Pre-run scripts enable templating (e.g., inject daily stock prices). May evolve into full template/context injection system.
- **Delivery platform abstraction** — Delivery targets are resolved through a generic platform interface. Suggests future expansion beyond current 17 platforms.
- **Repeat counter** — Jobs have a `repeat` field; suggests potential for backoff/retry logic in future versions.

---

## Module 4: acp_adapter/ — Agent Communication Protocol

### Purpose
Bridges hermes-agent to the Agent Client Protocol (ACP), a standardized protocol for AI agent-editor/IDE integration. Exposes the agent as an ACP server over stdio, allowing editors (Cursor, VSCode with ACP plugin, etc.) to spawn Hermes agent sessions, run tool calls, and maintain conversation history. Sessions are persistent (survive process restarts) and support features like forking, model switching, MCP server registration, and permission approval.

### Key Classes/Functions

1. **`HermesACPAgent`** — Main ACP Agent subclass implementing initialize(), create_session(), message(), fork_session(), etc.
2. **`SessionManager`** — Thread-safe manager for ACP sessions backed by Hermes AIAgent instances; sessions persisted to shared SessionDB
3. **`SessionState`** — Dataclass: session_id, agent, cwd, model, history, cancel_event
4. **`make_message_cb()`, `make_step_cb()`, `make_thinking_cb()`, `make_tool_progress_cb()`** — Callback factories that bridge AIAgent events to ACP notifications
5. **`make_approval_callback()`** — Maps ACP permission requests to hermes approval callbacks; returns "once", "always", or "deny"
6. **`detect_provider()`, `has_provider()`** — Detect active Hermes runtime provider for ACP auth
7. **`get_tool_kind(tool_name)`** — Map hermes tool names to ACP ToolKind ("read", "edit", "execute", "fetch", "think", "other")
8. **`build_tool_*()` functions** — Construct ACP tool call messages from hermes tool execution results
9. **`_extract_text()`** — Extract plain text from ACP content blocks (TextContentBlock, ImageContentBlock, etc.)

### Representative Snippets

**Snippet 1: HermesACPAgent class hierarchy and initialize response**
```python
# From acp_adapter/server.py
class HermesACPAgent(acp.Agent):
    """ACP Agent implementation wrapping Hermes AIAgent."""
    
    _SLASH_COMMANDS = {
        "help": "Show available commands",
        "model": "Show or change current model",
        "tools": "List available tools",
        ...
    }
    
    async def initialize(
        self,
        protocol_version: int | None = None,
        client_capabilities: ClientCapabilities | None = None,
        client_info: Implementation | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        provider = detect_provider()
        auth_methods = None
        if provider:
            auth_methods = [
                AuthMethodAgent(
                    id=provider,
                    name=f"{provider} runtime credentials",
                    description=f"Authenticate Hermes using the currently configured {provider} runtime credentials.",
                )
            ]
        
        return InitializeResponse(
            protocol_version=acp.PROTOCOL_VERSION,
            agent_info=Implementation(name="hermes-agent", version=HERMES_VERSION),
            agent_capabilities=AgentCapabilities(
                load_session=True,
                session_capabilities=SessionCapabilities(...),
            ),
            auth_methods=auth_methods,
        )
```

**Snippet 2: SessionManager — thread-safe session storage with DB persistence**
```python
# From acp_adapter/session.py
class SessionManager:
    """Thread-safe manager for ACP sessions backed by AIAgent instances.
    
    Sessions held in-memory for fast access AND persisted to shared SessionDB
    so they survive process restarts and are searchable via session_search.
    """
    
    def create_session(self, cwd: str = ".") -> SessionState:
        session_id = str(uuid.uuid4())
        agent = self._make_agent(session_id=session_id, cwd=cwd)
        state = SessionState(
            session_id=session_id,
            agent=agent,
            cwd=cwd,
            model=getattr(agent, "model", "") or "",
            cancel_event=threading.Event(),
        )
        with self._lock:
            self._sessions[session_id] = state
        _register_task_cwd(session_id, cwd)  # tool access scoped to cwd
        self._persist(state)
        return state
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Fetch session from memory; if not found, restore from DB."""
        with self._lock:
            state = self._sessions.get(session_id)
        if state:
            return state
        # Attempt to restore from database
        return self._restore(session_id)
```

**Snippet 3: Permission callback bridges ACP approval to hermes approval**
```python
# From acp_adapter/permissions.py
def make_approval_callback(
    request_permission_fn: Callable,
    loop: asyncio.AbstractEventLoop,
    session_id: str,
    timeout: float = 60.0,
) -> Callable[[str, str], str]:
    """Return a hermes-compatible approval_callback(command, description) -> str
    that bridges to ACP client's request_permission call."""
    
    def _callback(command: str, description: str) -> str:
        options = [
            PermissionOption(option_id="allow_once", kind="allow_once", name="Allow once"),
            PermissionOption(option_id="allow_always", kind="allow_always", name="Allow always"),
            PermissionOption(option_id="deny", kind="reject_once", name="Deny"),
        ]
        
        coro = request_permission_fn(
            session_id=session_id,
            tool_call=tool_call,
            options=options,
        )
        
        try:
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            response = future.result(timeout=timeout)
        except (FutureTimeout, Exception):
            return "deny"
        
        outcome = response.outcome
        if isinstance(outcome, AllowedOutcome):
            option_id = outcome.option_id
            for opt in options:
                if opt.option_id == option_id:
                    return _KIND_TO_HERMES.get(opt.kind, "deny")
        return "deny"
    
    return _callback
```

**Snippet 4: Tool kind mapping for semantic categorization**
```python
# From acp_adapter/tools.py
TOOL_KIND_MAP: Dict[str, ToolKind] = {
    # File operations
    "read_file": "read",
    "write_file": "edit",
    "patch": "edit",
    "search_files": "search",
    # Terminal / execution
    "terminal": "execute",
    "process": "execute",
    # Web / fetch
    "web_search": "fetch",
    "web_extract": "fetch",
    # Browser
    "browser_navigate": "fetch",
    "browser_click": "execute",
    # Thinking
    "_thinking": "think",
}

def get_tool_kind(tool_name: str) -> ToolKind:
    """Return ACP ToolKind for a hermes tool, defaulting to 'other'."""
    return TOOL_KIND_MAP.get(tool_name, "other")
```

### Data Flow

```
Editor/IDE connects to ACP server (stdio or TCP)
            ↓
initialize() — negotiate protocol, detect provider auth
            ↓
create_session() — new AIAgent + SessionState, persist to DB
            ↓
message() — user prompt → AIAgent.run() in thread pool
            ↓
AIAgent calls tool → tool_progress_cb() emits ACP ToolCallStart/Progress
            ↓
finish_message() — AIAgent stops, convert result to ACP format
            ↓
SessionManager persists history to DB
            ↓
Editor receives messages + tool updates over ACP connection
            ↓
For tool approval: editor sends request_permission → make_approval_callback()
            ↓
For session load/fork: restore from DB → merge history → continue
```

Sessions are **bidirectional**: editor sends prompts, Hermes sends tool calls, editor can approve/deny permissions.

### Config/Knobs

- **`~/.hermes/state.db`** — SessionDB path; stores all persisted sessions (location can be overridden via SessionDB config)
- **Hermes runtime provider** — Detected via `hermes_cli.runtime_provider.resolve_runtime_provider()` for ACP authentication
- **MCP servers** — Can be registered per-session via initialize/new_session messages; refreshes tool surface after registration
- **Model/temperature** — Can be switched per-session via `set_session_model()`
- **System prompt** — Hermes' existing system prompt used (not customizable per ACP session to avoid security confusion)

### Interactions with other modules

- **Depends on**: AIAgent from `run_agent.py`, SessionDB from `hermes_state.py`, tool execution (`model_tools.handle_function_call()`), auth detection (`hermes_cli`), MCP tool registration (`tools.mcp_tool`), terminal tool env overrides (`tools.terminal_tool`)
- **Provides**: ACP server interface that editors can connect to
- **Used by**: Cursor, VSCode with ACP plugin, any ACP-compatible editor
- **Interacts with**: Approval system (permissions.py bridges to hermes approvals), event streaming (callbacks push updates to client)

### Architectural Patterns and WHY

1. **Thread pool execution for AIAgent** — AIAgent is synchronous; runs in `ThreadPoolExecutor(max_workers=4)` so ACP event loop stays responsive. Callbacks use `asyncio.run_coroutine_threadsafe()` to push updates back to main loop.
2. **Session persistence to DB** — Sessions survive ACP server restart. Editor reconnects, `load_session()` restores history from DB, continues. Entire conversation is recoverable.
3. **Permission callback bridge** — ACP approval UI is different from hermes' CLI approval. Callback adapts one to the other (option_id → hermes action string).
4. **Tool kind mapping** — Classifies tools semantically (read, edit, execute, fetch, think). Editor UI can color/group them accordingly.
5. **MCP server registration per-session** — Tools can be added dynamically after session creation. Refresh happens via `_register_session_mcp_servers()` after MCP registration.

### Design Decisions

1. **Sessions are first-class ACP citizens** — Each session has its own AIAgent, history, and state. Unlike a simple request/response API, sessions enable multi-turn conversations and tool iteration.
2. **Persistent sessions survive server restart** — Sessions stored in SessionDB so editor reconnection after ACP server crash resumes the conversation. Improves UX and doesn't lose work.
3. **Slash commands (/help, /model, /tools, etc.)** — Parsed as pseudo-tools by the agent loop. Keeps agent API clean (only tool_calls); CLI-like commands are implemented as special message patterns.
4. **Threading isolation** — AIAgent runs in worker thread, ACP loop on main thread. Prevents blocking. Approved permissions use `asyncio.run_coroutine_threadsafe()` to coordinate between threads.
5. **Stderr for logging, stdout for ACP JSON-RPC** — Entry point explicitly routes logging to stderr. Ensures ACP JSON-RPC frames on stdout aren't corrupted by log messages.
6. **Lazy SessionDB initialization** — SessionDB created on first session create/restore, not at ACP server startup. Allows ACP to start even if `.hermes/state.db` is corrupted; error surfaces when session is first needed.

### Existence Rationale

- **Why ACP, not a custom protocol?** ACP is a standard that other AI agents support (Claude, OpenAI Assistants, etc.). Using it makes Hermes compatible with ACP-aware editors like Cursor.
- **Why persistent sessions?** Users expect conversations to survive app restart. Hermes can't guarantee in-memory state persistence; DB persistence is a safety net.
- **Why thread pool, not async AIAgent?** AIAgent is synchronous and uses sync tooling (subprocess, file I/O). Wrapping in a thread is simpler than rewriting the whole agent.
- **Why permission callbacks?** Hermes has approval flows for sensitive operations (terminal, system calls, etc.). ACP editors need to request approval from the user in their UI, not from Hermes' CLI.

### Error Philosophy

- **Tool errors are reported to editor** — If a tool fails, error is sent to editor as a ToolCallProgress update. Editor can display failure; agent can retry.
- **Session restore failures are soft-errors** — If a session can't be restored from DB, `load_session()` returns an error but doesn't crash the ACP server. Editor can create a new session instead.
- **MCP registration failures don't crash** — If MCP registration fails, warning is logged and tool surface is refreshed without new tools. Agent continues working with existing tools.
- **Approval timeouts → auto-deny** — If editor doesn't respond to approval request within 60s (configurable), request auto-denies. Prevents agent from hanging.

### Evolution Clues

- **MCP server per-session registration** — Suggests future support for dynamic tool addition without server restart.
- **SessionDB abstraction** — Suggests plans to support alternate backends (e.g., cloud sync, shared state across multiple Hermes instances).
- **Tool kind mapping** — Editor can semantically group tools; suggests future UI work to filter/organize tools by category.
- **Slash commands** — Parsed as patterns, not hardcoded. Suggests future plugin system for custom commands.

---

## Cross-Module Interactions Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    hermes-agent architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  config.yaml                                                     │
│  ├─ context.engine: "compressor"  ────────→  plugins/           │
│  ├─ memory.provider: "honcho"     ────────→  context_engine/,   │
│  └─ cron.wrap_response: true      ────────→  memory/             │
│                                                                   │
│  run_agent.py (CLI)                                              │
│  ├─ loads context engine via plugins.context_engine             │
│  ├─ loads memory provider via plugins.memory                    │
│  └─ exposes tools via model_tools                               │
│                                                                   │
│  environments/ (RL training)                                     │
│  ├─ uses AIAgent loop (from run_agent.py)                       │
│  ├─ uses model_tools.handle_function_call() for execution       │
│  ├─ uses toolset_distributions for tool selection               │
│  ├─ creates ToolContext for reward verifiers                    │
│  └─ integrates with Atropos framework                           │
│                                                                   │
│  cron/ (scheduled tasks)                                         │
│  ├─ launches AIAgent (fresh session per job)                    │
│  ├─ reads cron config from config.yaml                          │
│  ├─ uses send_message_tool for delivery                         │
│  ├─ persists to ~/.hermes/cron/jobs.json                        │
│  └─ invoked by gateway daemon every 60 seconds                  │
│                                                                   │
│  acp_adapter/ (editor protocol)                                  │
│  ├─ wraps AIAgent in ACP interface                              │
│  ├─ SessionManager ↔ SessionDB persistence                      │
│  ├─ Tool execution in ThreadPoolExecutor                        │
│  ├─ Event callbacks for streaming updates                       │
│  └─ Bridges permissions to approval callbacks                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Shared State and Boundaries

- **Config as single source of truth** — `config.yaml` drives plugin selection, cron settings, agent behavior. No hardcoded choices.
- **Hermes home directory** — `~/.hermes/` contains all persistent state: cron jobs, sessions, memory stores, plugin configs.
- **AIAgent as core abstraction** — All modules use the same AIAgent class. Ensures consistent tool execution across CLI, RL, cron, and ACP.
- **Tool execution isolation** — Tasks/sessions have unique IDs; tool state (terminal, browser) is scoped to task_id. Prevents cross-contamination.
- **Error handling cascade** — Low-level errors (tool failure) are captured, logged, and passed up; high-level code decides if it's a failure state.

---

## Summary Table

| Module | Purpose | Persistence | Active Scope | Primary Users |
|--------|---------|-------------|--------------|---------------|
| **plugins/** | Plugin discovery & loading | plugin.yaml, config.yaml | Runtime (1 context + 1 memory) | AIAgent init, CLI help |
| **environments/** | RL training integration | None (ephemeral) | Batch rollouts | Training pipelines, benchmarks |
| **cron/** | Scheduled task execution | jobs.json, output/ | Recurring/one-shot | Gateway daemon, CLI |
| **acp_adapter/** | Editor protocol bridge | SessionDB (state.db) | Per-session | Editors (Cursor, VSCode) |