# Hermes Agent — Project Overview

## Project Metadata

| Attribute | Value |
|-----------|-------|
| **Project Name** | Hermes Agent |
| **Current Version** | 0.9.0 |
| **Author/Organization** | Nous Research |
| **License** | MIT |
| **Repository** | `https://github.com/NousResearch/hermes-agent` |
| **Python Requirement** | ≥3.11 |
| **Description** | The self-improving AI agent — creates skills from experience, improves them during use, and runs anywhere |

### Project Scale
- **Total Python Files:** 870
- **Root-Level Code:** ~29,558 lines across 15 core modules
- **Module Distribution:**
  - `agent/` — 28 files (AI engine, prompting, memory, formatting)
  - `tools/` — 70 files (tool implementations, registry, environments)
  - `hermes_cli/` — 48 files (CLI subcommands, config, UI)
  - `gateway/` — 41 files (messaging platform adapters)
  - `tests/` — Extensive pytest suite across 8 test categories
- **Skills:** 26 bundled categories, 14 optional categories

---

## Root-Level Files Analysis

### **cli.py** (447 KB — Main CLI Interface)
**Purpose:**  
Interactive terminal UI for Hermes with full TUI support (multiline editing, command autocomplete, streaming output, conversation persistence).

**Key Classes/Functions:**
- `HermesCLI` — Main CLI orchestrator with asyncio event loop management
- `_load_config_from_files()` — Loads user config from `~/.hermes/config.yaml`
- `_prefill_messages()` — Loads ephemeral context from JSON files
- `Keybindings` — Slash command and keyboard control setup
- `_spinner()` — Terminal spinner for async operations

**Important Constants:**
- `DEFAULT_MODEL` — Default LLM (e.g., "anthropic/claude-opus-4.6")
- Session history stored in `~/.hermes/sessions/<session_id>.json`

**Module Connections:**
- Imports `run_agent.AIAgent` for conversation loop
- Uses `hermes_logging.setup_logging()` for logger initialization
- Imports from `agent.usage_pricing` for token cost tracking
- Loads config from `hermes_cli.config` defaults
- Delegates tool calls via `model_tools.handle_function_call()`

---

### **run_agent.py** (552 KB — Core Agent Engine)
**Purpose:**  
The heart of Hermes: implements the `AIAgent` class that manages the conversation loop, LLM dispatch, tool execution, context compression, and trajectory saving.

**Key Classes/Functions:**
- `AIAgent.__init__()` — Initialize agent with model, toolsets, memory, logging
- `AIAgent.chat(message)` → `str` — Single-turn conversation (CLI/gateway entry point)
- `_call_model()` — LLM API dispatch (OpenAI, Anthropic, OpenRouter, etc.)
- `_execute_tools()` — Orchestrate tool execution with parallel delegation
- `ContextCompressor` — Auto-compress context when approaching token limits
- `_build_system_prompt()` — Dynamic system prompt assembly (skills, context files, memory)

**Important Constants:**
- `MAX_ITERATIONS` — Safety limit on tool-call loops (default: 90)
- `SYSTEM_PROMPT` — Hermes base prompt (injected into all conversations)
- `TOOL_USE_ENFORCEMENT_MODELS` — Models that need explicit tool-use guidance
- `REASONING_EFFORT_MODELS` — Models supporting extended thinking (o1, 4o-mini)

**Module Connections:**
- Core dependency on `model_tools` for tool dispatch
- Uses `agent.prompt_builder` for system prompt assembly
- Integrates `agent.memory_manager` for persistent memory
- Calls `agent.context_compressor` for token budget management
- Dispatches via `agent.anthropic_adapter`, `agent.auxiliary_client`
- Saves trajectories via `agent.trajectory`
- Manages tool cleanup: `tools.terminal_tool.cleanup_vm()`, `tools.browser_tool.cleanup_browser()`

---

### **hermes_constants.py** (10 KB — Shared Constants, Import-Safe)
**Purpose:**  
Centralized constants and path helpers without external dependencies—safe to import from anywhere without circular-dependency risk.

**Key Functions:**
- `get_hermes_home()` → `Path` — Returns `$HERMES_HOME` or `~/.hermes`
- `get_default_hermes_root()` → `Path` — Root for profile-level operations
- `display_hermes_home()` → `str` — User-friendly display (e.g., `~/.hermes`)
- `get_optional_skills_dir()` → `Path` — Optional skills location
- `is_container()`, `is_wsl()`, `is_termux()` → `bool` — Platform detection
- `apply_ipv4_preference()` — Monkey-patch socket to prefer IPv4

**Important Constants:**
- `OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"`
- `VALID_REASONING_EFFORTS = ("minimal", "low", "medium", "high", "xhigh")`
- Well-known paths: `get_config_path()`, `get_skills_dir()`, `get_env_path()`

**Module Connections:**
- **Zero dependencies** — imported by nearly every module in the project
- Used by `hermes_logging`, `hermes_time`, `hermes_state` for config/path resolution

---

### **hermes_logging.py** (13 KB — Centralized Logging)
**Purpose:**  
Single-entry-point logging setup ensuring all logs go to `~/.hermes/logs/` with session context, redaction, and component-based routing.

**Key Functions:**
- `setup_logging(mode, hermes_home, log_level, ...)` → `Path` — Configure all handlers (idempotent)
- `setup_verbose_logging()` — Enable DEBUG console output for `--verbose` mode
- `set_session_context(session_id)` → `None` — Tag logs with session ID
- `clear_session_context()` → `None` — Clear session tag

**Important Configuration:**
- **Log files:** `agent.log` (INFO+), `errors.log` (WARNING+), `gateway.log` (gateway only)
- **Rotation:** 5 MB max, 3 backups by default (configurable)
- **Noisy loggers suppressed:** `openai`, `httpx`, `urllib3`, `asyncio`, etc.
- `COMPONENT_PREFIXES` — Route records to correct log file by logger name

**Module Connections:**
- Called by `cli.py:main()` and `gateway/run.py` on startup
- Uses `RedactingFormatter` from `agent.redact` to strip secrets
- Reads config from `hermes_constants.get_config_path()`

---

### **hermes_state.py** (49 KB — Session Persistence)
**Purpose:**  
SQLite-backed session store with FTS5 full-text search for querying past conversations and user memory.

**Key Classes:**
- `SessionDB` — Low-level SQLite interface (create, read, search sessions)
- `Session` — Single conversation with message history, metadata, skill interactions
- `SessionEntry` — Individual message in a session

**Important Methods:**
- `SessionDB.create_session()` — Initialize new conversation
- `SessionDB.get_session()` — Retrieve full history
- `SessionDB.search(query)` → `List[Session]` — FTS5 full-text search
- `SessionDB.save_message()` — Append message to session
- `Session.to_dict()` → dict — Serialize to JSON

**Module Connections:**
- Manages `~/.hermes/sessions/` directory and SQLite database
- Used by `run_agent.AIAgent` to persist conversation history
- Queried by `/session_search` tool and `/insights` command
- Memory context built by `agent.memory_manager` from SessionDB

---

### **hermes_time.py** (3 KB — Timezone-Aware Clock)
**Purpose:**  
Single `now()` function returning timezone-aware datetime based on user config (IANA timezone).

**Key Functions:**
- `now()` → `datetime` — Get current time in user's timezone (or server-local if not configured)
- `get_timezone()` → `Optional[ZoneInfo]` — Resolved ZoneInfo (cached)
- `reset_cache()` — Force re-resolution (after config changes)

**Resolution Order:**
1. `HERMES_TIMEZONE` environment variable
2. `timezone` key in `~/.hermes/config.yaml`
3. Server local time (fallback)

**Module Connections:**
- Used by `agent/`, `tools/`, and `cron/` for consistent time handling
- Never crashes due to bad timezone — logs warning and falls back safely

---

### **model_tools.py** (24 KB — Tool Orchestration Layer)
**Purpose:**  
Thin orchestration over `tools.registry`—discovers all tools, exposes public API consumed by `run_agent.py`, `cli.py`, `batch_runner.py`.

**Key Functions:**
- `_discover_tools()` — Import all tool modules to trigger `registry.register()` calls
- `get_tool_definitions(enabled_toolsets, disabled_toolsets, ...)` → `list` — Get tool schemas for LLM
- `handle_function_call(function_name, function_args, task_id, ...)` → `str` — Execute tool, return result
- `get_all_tool_names()` → `list` — All available tools
- `get_available_toolsets()` → `dict` — Toolsets with descriptions
- `check_toolset_requirements()` → `dict` — Verify dependencies (fal_client, browserbase, etc.)

**Important State:**
- `TOOL_TO_TOOLSET_MAP` — Maps each tool to its category (used by `batch_runner.py`)
- `_tool_loop` — Global persistent event loop (prevents "Event loop is closed" errors)
- `_run_async()` — Bridge sync→async, handles running loops, worker threads, main thread

**Module Connections:**
- Imports `tools.registry` (central registry, no other tool files directly)
- Triggers lazy imports of all tool modules (web_tools, terminal_tool, file_tools, etc.)
- Called by `run_agent.AIAgent` to get tool definitions and dispatch tool calls
- Consumed by `batch_runner.py` and RL environments

---

### **toolsets.py** (22 KB — Tool Grouping System)
**Purpose:**  
Defines logical groupings of tools (e.g., "web", "terminal", "full_stack") that can be composed and toggled per conversation/platform.

**Key Functions:**
- `get_toolset(name)` → `list` — Get tools for a toolset
- `resolve_toolset(name)` → `set` — Resolve with transitive includes
- `validate_toolset(name)` — Check if valid
- `get_all_toolsets()` → `dict` — List all available toolsets

**Core Toolsets Defined:**
- **Basic:** web, search, vision, image_gen, terminal, moa, skills, browser, cronjob, messaging, rl, file
- **Composite:** safe, full_stack, research, coding, creative
- Each toolset specifies: `description`, `tools: [list]`, `includes: [other_toolsets]`

**Important Shared List:**
- `_HERMES_CORE_TOOLS` — Core tools available on all platforms (edited once, used everywhere)

**Module Connections:**
- Imported by `model_tools` for toolset resolution
- Used by `run_agent.AIAgent.__init__()` to configure available tools
- Queried by `cli.py` for toolset browsing (`/tools` command)

---

### **toolset_distributions.py** (12 KB — Data Generation Configurations)
**Purpose:**  
Probability distributions over toolsets for batch data generation—control which tools are available during trajectory generation.

**Key Functions:**
- `get_distribution(name)` → `dict` — Retrieve distribution spec
- `list_distributions()` → `list` — Available distributions
- `sample_toolsets_from_distribution(dist_name)` → `list` — Sample toolsets based on probabilities
- `validate_distribution(name)` → `bool` — Check validity

**Distributions Defined:**
- **default** — All tools 100% (baseline)
- **image_gen** — 90% image, 90% vision, 55% web, 45% terminal, 10% moa
- **research** — 90% web, 70% browser, 50% vision, 40% moa, 10% terminal
- **science** — 94% web/terminal/file, 65% vision, 50% browser
- **development** — 80% terminal/file, 60% moa, 30% web
- **safe** — All except terminal
- **minimal** — Bare essentials (no web, browser, terminal)

**Module Connections:**
- Used by `batch_runner.py` to sample toolsets per prompt
- Enables research experiments with varying tool availability

---

### **utils.py** (5 KB — Shared Utilities)
**Purpose:**  
Collection of cross-cutting utility functions: atomic file I/O, JSON/YAML helpers, environment variable parsing.

**Key Functions:**
- `is_truthy_value(value, default=False)` → `bool` — Coerce bool-ish values
- `env_var_enabled(name, default="")` → `bool` — Check if env var is truthy
- `atomic_json_write(path, data, ...)` — Write JSON atomically (temp file + fsync + replace)
- `atomic_yaml_write(path, data, ...)` — Write YAML atomically
- `safe_json_loads(text, default=None)` → `Any` — Parse JSON with fallback

**Constants:**
- `TRUTHY_STRINGS = {"1", "true", "yes", "on"}` — Standard truthy set

**Module Connections:**
- Used throughout for safe file I/O, config loading, environment variable parsing

---

### **batch_runner.py** (55 KB — Parallel Batch Processing)
**Purpose:**  
Generate trajectories from large prompt datasets using multiprocessing—enables large-scale training data collection with checkpointing and resume.

**Key Functions:**
- `main(dataset_file, batch_size, run_name, output_dir, ...)` — CLI entry point
- `_process_batch(batch, worker_id)` → `list` — Worker function for parallel execution
- `_extract_tool_stats(messages)` → `dict` — Parse tool usage from message history
- `_normalize_tool_stats(tool_stats)` — Ensure consistent schema across runs
- `run_batch(dataset_file, batch_size, ...)` — Orchestrate batches with checkpointing

**CLI Arguments:**
- `--dataset_file` — JSONL with `{"prompt": "..."}` entries
- `--batch_size` — Prompts per batch (parallelized)
- `--run_name` — Output directory name
- `--distribution` — Toolset distribution to use
- `--resume` — Skip completed batches

**Module Connections:**
- Uses `AIAgent` from `run_agent` to generate trajectories
- Imports `TOOL_TO_TOOLSET_MAP` from `model_tools`
- Samples toolsets via `toolset_distributions`
- Aggregates tool statistics for training dataset quality assessment

---

### **trajectory_compressor.py** (63 KB — Token Budget Compression)
**Purpose:**  
Post-process trajectories to compress them within a target token budget while preserving training signal—replaces middle turns with LLM-generated summaries.

**Key Strategy:**
1. Protect first turns (system, human, first GPT, first tool)
2. Protect last N turns (final conclusions)
3. Compress only MIDDLE turns (starting from 2nd tool response)
4. Replace compressed region with single human summary
5. Keep remaining tool calls intact

**Key Classes:**
- `CompressionConfig` — Configuration from YAML or defaults
- `TrajectoryCompressor` — Main compression logic with LLM summarization

**CLI Usage:**
```bash
python trajectory_compressor.py --input=data/my_run --target_max_tokens=16000
python trajectory_compressor.py --input=data/trajectories.jsonl --sample_percent=15
```

**Module Connections:**
- Uses OpenRouter API for summarization (configurable model)
- Integrates `hermes_constants` for paths and API endpoints
- Compatible with `batch_runner.py` output format

---

### **mcp_serve.py** (30 KB — MCP Server Bridge)
**Purpose:**  
Expose messaging conversations as MCP tools, enabling Claude Code, Cursor, Codex, and other MCP clients to list conversations, read history, send messages, poll events, manage approval requests.

**Key Functions:**
- `main(verbose=False)` — Start MCP stdio server
- `_load_sessions_index()` → `dict` — Load gateway sessions
- `_get_session_db()` — Get SessionDB instance
- `_load_channel_directory()` → `dict` — Load available messaging targets

**MCP Tools Exposed:**
- `conversations_list` — List all conversations
- `conversation_get` — Retrieve full history
- `messages_read` — Get recent messages
- `messages_send` — Send messages to platforms
- `events_poll`, `events_wait` — Polling for live events
- `permissions_list_open`, `permissions_respond` — Approval workflows
- `channels_list` — Platform-specific channels (Hermes extra)

**Module Connections:**
- Used by `hermes_cli` as `hermes mcp serve` subcommand
- Integrates `hermes_state.SessionDB` for conversation retrieval
- Routes to `gateway/session.py` for platform delivery

---

### **rl_cli.py** (16 KB — RL Training CLI)
**Purpose:**  
Dedicated runner for RL training workflows with extended timeouts, RL-focused prompts, full toolset including RL training tools.

**Key Configuration:**
- `RL_MAX_ITERATIONS = 200` — Allow long workflows
- `RL_SYSTEM_PROMPT` — Specialized prompt for RL engineering
- Extended timeouts for training checkpoints

**CLI Usage:**
```bash
python rl_cli.py "Train a model on GSM8k for math reasoning"
python rl_cli.py --interactive
python rl_cli.py --list-environments
```

**Module Connections:**
- Wraps `AIAgent` from `run_agent` with RL-specific configuration
- Imports RL tools from `tools.rl_training_tool`
- Integrates with Tinker-Atropos submodule (RL environment)
- Sets `TERMINAL_CWD` to tinker-atropos for command context

---

### **mini_swe_runner.py** (27 KB — SWE Benchmark Runner)
**Purpose:**  
Run SWE (Software Engineering) benchmarks using Hermes-Agent's execution environments, outputting trajectories in Hermes format compatible with `batch_runner.py` and `trajectory_compressor.py`.

**Key Features:**
- Environment factory supporting local, Docker, Modal execution
- Outputs trajectories with `<tool_call>/<tool_response>` XML format
- Compatible with SWE-bench dataset format

**CLI Usage:**
```bash
python mini_swe_runner.py --task "Create a hello world Python script" --env local
python mini_swe_runner.py --prompts_file prompts.jsonl --output_file trajectories.jsonl --env docker
```

**Module Connections:**
- Uses `environments/` backends for task execution
- Outputs Hermes trajectory format for downstream compression/training

---

### **AGENTS.md** (Development Guide)
**Contents:**
- Project structure walkthrough (40-line ASCII tree)
- File dependency chain (tools → model_tools → run_agent/cli/batch_runner)
- AIAgent class overview with key methods
- Conversation loop explanation
- Tool execution pipeline
- Memory system integration

**Key Architectural Insights:**
- tools/registry.py is a zero-dependency central hub
- Each tool file self-registers at import time
- model_tools triggers discovery and exposes public API
- run_agent implements the core conversation loop
- cli.py wraps run_agent with interactive terminal UI
- gateway/ wraps run_agent for messaging platforms

---

### **CONTRIBUTING.md** (100+ lines)
**Contents:**
- **Contribution priorities:** Bugs → compatibility → security → performance → skills → tools → docs
- **Skill vs Tool decision tree:**
  - Make a **Skill** when: expressible via instructions + shell + existing tools
  - Make a **Tool** when: requires Python integration, auth, binary data, real-time events
- **Development setup:** Git clone, uv venv, install extras, configure `~/.hermes/`
- **Directory structure:** Quick reference to all major modules
- **File dependency chain:** How imports flow
- **Testing:** Pytest suite organization
- **Code style:** Black, isort, type hints
- **Security considerations:** Shell injection, prompt injection, path traversal

---

## Module Architecture Overview

### **agent/** (28 files)
The AI engine—prompt building, memory management, context compression, model routing, caching, formatting.

| File | Purpose |
|------|---------|
| `prompt_builder.py` | System prompt assembly (skills, context files, memory, environment hints) |
| `memory_manager.py` | User memory context building from SessionDB |
| `context_compressor.py` | Auto-compression when approaching token limits |
| `model_metadata.py` | Model context lengths, token estimation, provider detection |
| `auxiliary_client.py` | Separate LLM client for vision analysis, summarization (non-primary model) |
| `prompt_caching.py` | Anthropic prompt caching integration |
| `anthropic_adapter.py` | Anthropic-specific adaptations (extended thinking, vision, etc.) |
| `display.py` | Terminal formatting, KawaiiSpinner, tool preview rendering |
| `skill_utils.py` | Skill discovery, loading, validation |
| `skill_commands.py` | Slash command implementations (shared CLI/gateway) |
| `redact.py` | Secret masking for logs |
| `retry_utils.py` | Retry logic with exponential backoff |
| `error_classifier.py` | Categorize API errors for failover decisions |
| `smart_model_routing.py` | Multi-tier LLM failover strategy |
| `rate_limit_tracker.py` | Track API rate limits per provider |
| `usage_pricing.py` | Cost estimation per model |
| `models_dev.py` | models.dev registry integration |
| `trajectory.py` | Trajectory serialization for training data |

---

### **tools/** (70 files)
Tool implementations, registry, execution backends, safety features.

**Core Infrastructure:**
- `registry.py` — Central registry (schemas, handlers, dispatch)
- `approval.py` — Dangerous command detection and approval workflow

**Tool Categories:**
| Category | Examples |
|----------|----------|
| **Web** | web_tools.py (search, extract), web_providers.py |
| **Terminal/Execution** | terminal_tool.py, process_registry.py |
| **File I/O** | file_tools.py (read, write, patch, search) |
| **Vision/Media** | vision_tools.py, image_generation_tool.py, tts_tool.py |
| **Browser** | browser_tool.py (Browserbase automation), browser_providers.py |
| **Code** | code_execution_tool.py (sandbox), delegate_tool.py (subagents) |
| **Skill/Memory** | skills_tool.py, skill_manager_tool.py, memory_tool.py |
| **MCP** | mcp_tool.py (MCP client bridge) |
| **Scheduling** | cronjob_tools.py |
| **Advanced** | mixture_of_agents_tool.py (reasoning), rl_training_tool.py |

**Execution Backends (`environments/`):**
- `local/` — Direct execution on host
- `docker/` — Containerized execution
- `ssh/` — Remote execution
- `modal/` — Serverless (FaaS)
- `daytona/` — Daytona serverless
- `singularity/` — HPC container

---

### **gateway/** (41 files)
Messaging platform adapters, session management, platform-agnostic delivery.

| File | Purpose |
|------|---------|
| `run.py` | Main loop, slash commands, message dispatch |
| `session.py` | SessionStore — conversation persistence per platform |
| `config.py` | Gateway configuration, provider setup |
| `delivery.py` | Send messages to all platforms |
| `channel_directory.py` | Map platform channels to routing info |
| `pairing.py` | DM-based device pairing workflow |
| `stream_consumer.py` | Listen to platform webhooks/polling |
| `sticker_cache.py` | Cache stickers/emojis per platform |
| `status.py` | Platform connection status dashboard |
| `display_config.py` | Platform-specific UI settings |
| `platforms/` | Adapters: telegram.py, discord.py, slack.py, whatsapp.py, signal.py, homeassistant.py, qqbot.py |

---

### **hermes_cli/** (48 files)
CLI subcommands, configuration, interactive setup, model switching, skill/tool browsing.

| File | Purpose |
|------|---------|
| `main.py` | Entry point for `hermes` command |
| `config.py` | DEFAULT_CONFIG, config migration, validation |
| `setup.py` | Interactive setup wizard |
| `model_switch.py` | Shared `/model` command pipeline |
| `models.py` | Model catalog, provider model lists |
| `skills_hub.py` | `/skills` command (browse, search, install) |
| `tools_config.py` | Enable/disable tools per platform |
| `skin_engine.py` | Skin/theme engine (CLI visual customization) |
| `auth.py` | Provider credential resolution |
| `doctor.py` | Diagnostics (`hermes doctor`) |
| `backup.py` | Backup/restore (`hermes backup`) |
| `cron.py` | Cron job management (`hermes cron`) |
| `copilot_auth.py` | GitHub Copilot auth setup |

---

### **skills/** (26 Bundled Categories)
Pre-installed procedural memory organized by domain:

**Available Categories:**
- apple, autonomous-ai-agents, creative, data-science, devops, diagramming, dogfood
- domain, email, feeds, gaming, gifs, github, index-cache, inference-sh
- leisure, mcp, media, mlops, note-taking, productivity, red-teaming
- research, smart-home, social-media, software-development

Each skill is a `.md` file with:
- Instructions (natural language task definition)
- Examples (few-shot demonstrations)
- Meta-instructions (how/when to use)

---

### **optional-skills/** (14 Categories)
Non-bundled official skills requiring user discovery/install:

- autonomous-ai-agents, blockchain, communication, creative, devops
- email, health, mcp, migration, mlops, productivity, research, security

---

### **scripts/** (7 Tools)
Utility scripts for development, release, and analysis:

- `install.sh` — Installation script (cross-platform)
- `release.py` — Version bump and GitHub release automation
- `build_skills_index.py` — Build skills registry for hub
- `contributor_audit.py` — Analyze contributor stats
- `sample_and_compress.py` — Pipeline: sample trajectories → compress
- `discord-voice-doctor.py` — Discord voice troubleshooting
- `kill_modal.sh` — Cleanup Modal cloud resources

---

### **tests/** (Multiple Categories)
Comprehensive pytest suite organized by component:

| Directory | Coverage |
|-----------|----------|
| `agent/` | Prompt building, context compression, memory management |
| `tools/` | Individual tool tests (terminal, file, web, browser, etc.) |
| `cli/` | CLI command parsing, output formatting |
| `gateway/` | Platform adapters, session routing, message delivery |
| `hermes_cli/` | Config loading, model switching, setup wizard |
| `run_agent/` | Agent loop, tool dispatch, error handling |
| `skills/` | Skill loading, slash commands |
| `e2e/` | End-to-end workflows (full conversation → save → retrieve) |
| `integration/` | Cross-module integration (memory → context → prompt) |
| `environments/` | Execution backend testing (docker, ssh, modal) |
| `cron/` | Scheduler functionality |
| `acp/` | Agent Client Protocol (VS Code integration) |
| `plugins/memory/` | Memory plugin integration |

---

## Architecture Flow

### **Startup Flow (CLI)**

```
cli.py:main()
  ├─ Load config from ~/.hermes/config.yaml
  ├─ hermes_logging.setup_logging(mode="cli")
  ├─ hermes_cli.env_loader.load_hermes_dotenv()
  ├─ HermesCLI() instantiation
  │  ├─ Initialize asyncio event loop
  │  ├─ Setup prompt_toolkit UI
  │  └─ Load history from ~/.hermes/sessions/
  └─ User starts chatting
     └─ Each message → AIAgent.chat()
```

### **Conversation Loop (Single Turn)**

```
AIAgent.chat(user_message)
  ├─ Append to message history
  ├─ _call_model()  [LLM API dispatch]
  │  ├─ Fetch skill definitions
  │  ├─ Load memory context (SessionDB)
  │  ├─ Build system prompt (prompt_builder)
  │  ├─ Auto-compress context if needed
  │  └─ Call LLM (OpenAI/Anthropic/OpenRouter/custom)
  ├─ Parse LLM response for tool calls
  ├─ _execute_tools()  [For each tool call]
  │  ├─ Get tool schema from registry
  │  ├─ Validate arguments
  │  ├─ Execute handler (possibly async)
  │  ├─ Collect result
  │  └─ Append to message history
  ├─ Check if done (no more tool calls or max iterations reached)
  ├─ Save trajectory (if enabled)
  ├─ Return final LLM response
  └─ Display via CLI or send via gateway
```

### **Tool Execution Pipeline**

```
model_tools.handle_function_call(tool_name, args)
  ├─ Look up tool in registry
  ├─ Get handler function
  ├─ model_tools._run_async()  [Bridge sync→async if needed]
  │  ├─ Detect if running event loop already
  │  ├─ Use persistent loop for main thread
  │  ├─ Use per-worker loop for thread pool
  │  └─ Spawn fresh thread if loop already running (gateway)
  ├─ Execute handler
  ├─ Serialize result as XML `<tool_response>...</tool_response>`
  └─ Return to LLM
```

### **Gateway Flow (Messaging)**

```
gateway/run.py:main()
  ├─ Load config from ~/.hermes/config.yaml
  ├─ hermes_logging.setup_logging(mode="gateway")
  ├─ Initialize all platform adapters
  │  ├─ Telegram: setWebhook or polling
  │  ├─ Discord: connect bot token
  │  ├─ Slack: start socket mode
  │  └─ WhatsApp/Signal: webhooks
  ├─ gateway.session.SessionStore() — load all conversations
  └─ Wait for incoming messages
     └─ Per message: AIAgent.chat() (same loop as CLI)
        └─ gateway.delivery.send_response()  [Route to platform]
```

### **Batch Processing Pipeline**

```
batch_runner.py:main()
  ├─ Load JSONL dataset (each line: {"prompt": "..."})
  ├─ Split into batches
  ├─ Load/create checkpoint file
  ├─ For each batch (parallel via multiprocessing)
  │  ├─ toolset_distributions.sample_toolsets_from_distribution()
  │  ├─ For each prompt in batch
  │  │  └─ AIAgent.chat(prompt)
  │  └─ Extract tool_stats from messages
  ├─ Normalize tool stats (ensure all tools present)
  ├─ Save trajectories to JSONL
  └─ Update checkpoint, print summary
```

---

## Key Design Principles Observable from Code

### 1. **Single Responsibility with Clear Dependencies**
- `hermes_constants.py` has ZERO external dependencies
- `model_tools.py` orchestrates but doesn't duplicate tool logic
- `tools/registry.py` is the single source of truth for tools
- Each module imports only what it needs (not "import *")

### 2. **Import-Safe Core Foundation**
- Modules can be imported anywhere without risk of circular imports
- `hermes_constants`, `utils`, `hermes_time` carefully designed as safe foundations
- Lazy imports used for heavy dependencies (e.g., `agent.redact` in logging setup)

### 3. **Idempotent Setup Functions**
- `setup_logging(force=False)` — safe to call multiple times
- `_install_session_record_factory()` — guard against double-wrapping
- Enables robust multi-entry-point applications (CLI + gateway + cron)

### 4. **Profile-Aware Configuration**
- Single `HERMES_HOME` resolves all paths (env var → profile → default)
- Profiles isolated in `~/.hermes/profiles/<name>/`
- All paths use `get_hermes_home()` (one source of truth)

### 5. **Async Bridging Strategy**
- Persistent event loops prevent "Event loop is closed" errors
- Separate loops for: main thread, worker threads, async contexts
- `_run_async()` auto-detects context and routes accordingly

### 6. **Atomic File I/O**
- `atomic_json_write()` / `atomic_yaml_write()` ensure crash-safety
- Temp file → fsync → os.replace prevents partial writes
- Session data never left in corrupted state

### 7. **Session Context Propagation**
- LogRecord factory injects `session_id` into every log record
- Thread-local storage ensures context doesn't leak between conversations
- Enables post-hoc log filtering by conversation

### 8. **Tool Registry Pattern**
- Each tool module calls `registry.register()` at import time
- Central registry has ZERO tool-specific imports
- `_discover_tools()` triggers all registrations in one place
- New tools added: just create file + call `registry.register()` — no config needed

### 9. **Graceful Degradation**
- Optional dependencies wrapped in try/except (e.g., browser tools, MCP)
- Platform adapters independently fail (missing API key doesn't crash whole gateway)
- Noisy loggers selectively suppressed (no spam)

### 10. **Composition Over Inheritance**
- Toolsets composed from tools + other toolsets
- Distributions composed from toolsets
- Prompts composed from blocks (skills, memory, context, environment hints)
- No deep class hierarchies — mostly dataclasses and functions

---

## Cross-Module Dependencies (Import Analysis)

### **Core Import Tree**

```
hermes_constants.py  (ZERO external deps)
    ↑ (imported by almost everything)
    
hermes_logging.py
hermes_time.py
hermes_state.py
utils.py
model_tools.py
    ↑
    ├─ imports: tools.registry (central hub)
    ├─ triggers: tools/*.py imports (self-register)
    └─ exposed API consumed by:
        ├─ run_agent.py
        ├─ cli.py
        ├─ batch_runner.py
        ├─ rl_cli.py
        ├─ mini_swe_runner.py
        └─ gateway/run.py

run_agent.py
    ├─ imports: model_tools, agent/*, hermes_constants
    ├─ used by: cli.py, gateway/run.py, batch_runner.py, rl_cli.py
    └─ manages: AIAgent (core conversation loop)

cli.py
    ├─ imports: run_agent.AIAgent, hermes_cli/*, agent/*
    ├─ entry point: `hermes` command
    └─ manages: HermesCLI (interactive TUI)

gateway/run.py
    ├─ imports: run_agent.AIAgent, gateway/*, agent/*
    ├─ entry point: `hermes gateway`
    └─ manages: messaging platforms

batch_runner.py
    ├─ imports: run_agent.AIAgent, model_tools, toolset_distributions
    ├─ entry point: `python batch_runner.py`
    └─ produces: training trajectories (JSONL)

trajectory_compressor.py
    ├─ consumes: batch_runner output (JSONL)
    ├─ produces: compressed trajectories
    └─ entry point: `python trajectory_compressor.py`

mcp_serve.py
    ├─ imports: hermes_state.SessionDB
    ├─ entry point: `hermes mcp serve`
    └─ exposes: MCP tool interface
```

### **Agent Module Dependencies**

```
agent/prompt_builder.py  → constructs system prompt
agent/memory_manager.py  → loads from hermes_state.SessionDB
agent/context_compressor.py  → auto-truncates when over budget
agent/model_metadata.py  → context lengths, providers
agent/auxiliary_client.py  → secondary LLM (vision, summarization)
agent/anthropic_adapter.py  → Anthropic-specific (extended thinking)
...

All import from hermes_constants (paths, API endpoints)
```

### **Tool Registry Pattern**

```
tools/registry.py  (ZERO other-tool imports)
    ↑
tools/web_tools.py  → registry.register("web_search", ...)
tools/terminal_tool.py  → registry.register("terminal", ...)
tools/file_tools.py  → registry.register("read_file", ...)
... (all independently)
    ↑
model_tools._discover_tools()  [imports them all at once]
    ↑
model_tools.handle_function_call()  [dispatches]
```

---

## Configuration System

### **Config Hierarchy**

1. **Environment Variables** (highest priority)
   - `HERMES_HOME` — override home dir
   - `HERMES_TIMEZONE` — timezone override
   - `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, etc. — credentials
   - `HERMES_OPTIONAL_SKILLS` — override skills dir

2. **`~/.hermes/config.yaml`**
   ```yaml
   model:
     default: "anthropic/claude-opus-4.6"
     base_url: "https://openrouter.ai/api/v1"
   
   timezone: "America/New_York"
   
   tools:
     enabled_toolsets: ["web", "terminal", "file"]
     disabled_toolsets: []
   
   logging:
     level: "INFO"
     max_size_mb: 5
     backup_count: 3
   
   compression:
     enabled: true
     target_max_tokens: 100000
   ```

3. **`~/.hermes/.env`** — API keys and secrets
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   ANTHROPIC_API_KEY=sk-ant-...
   TELEGRAM_BOT_TOKEN=...
   ```

4. **CLI flags** (runtime overrides)
   ```bash
   hermes --model "gpt-4o-mini" --quiet
   ```

---

## Entry Points & Execution Modes

### **CLI (Interactive Terminal)**
```bash
hermes                           # Start interactive chat
hermes --model gpt-4o-mini      # Override model
hermes --quiet                  # Minimal output
hermes [task]                   # Single-shot execution
```

### **Gateway (Messaging Platforms)**
```bash
hermes gateway setup             # Interactive config
hermes gateway start             # Start telegram/discord/slack bot
hermes gateway status            # Check platform connections
```

### **Batch Processing (Training Data)**
```bash
python batch_runner.py \
  --dataset_file data.jsonl \
  --batch_size 10 \
  --run_name my_run \
  --distribution image_gen
```

### **Trajectory Compression**
```bash
python trajectory_compressor.py \
  --input data/my_run \
  --target_max_tokens 16000 \
  --sample_percent 15
```

### **RL Training**
```bash
python rl_cli.py "Train a model on math benchmarks"
python rl_cli.py --list-environments
```

### **MCP Server**
```bash
hermes mcp serve                 # Start MCP stdio server
hermes mcp serve --verbose       # Debug mode
```

### **Other CLI Commands**
```bash
hermes setup                     # Interactive setup wizard
hermes config set               # Set individual config value
hermes model                    # Switch models
hermes tools                    # Enable/disable tools
hermes skills                   # Skill hub
hermes cron                     # Scheduled tasks
hermes doctor                   # Diagnostics
hermes backup                   # Backup/restore
```

---

## Summary: Design Excellence Indicators

1. **Modularity:** Clear module boundaries, minimal coupling, reusable components
2. **Safety:** Atomic I/O, import-safe foundations, graceful degradation
3. **Extensibility:** Tool registry pattern, skill composability, platform adapters
4. **Robustness:** Retry logic, async bridging, session context, comprehensive logging
5. **Configuration:** Single source of truth per domain (hermes_home, config.yaml, .env)
6. **Scalability:** Multiprocessing support, async/await, serverless backends (Modal, Daytona)
7. **Developer Experience:** Clear project structure, contributing guide, self-documenting code
8. **Enterprise-Ready:** Multi-user profiles, audit logging, approval workflows, security hardening

The architecture reflects mature software design: strong separation of concerns, defensive programming, and strategic use of composition over inheritance. Hermes is built for production use, research reproducibility, and community contribution.