# Cross-Module Synthesis — Hermes Agent

## End-to-End Flows

### Flow 1: Interactive CLI Chat
1. cli.py -> hermes_cli/main.py:cmd_chat() -> resolve provider (auth.py) -> credential pool
2. -> run_agent.py:run_agent() -> build system prompt (agent/prompt_builder.py)
3. -> inject context files, memory, skills -> LLM API call (openai/anthropic SDK)
4. -> tool call received -> tools/registry.py dispatches -> tool execution
5. -> result returned to LLM -> streaming response to CLI TUI
6. -> memory persistence -> session save -> display

### Flow 2: Messaging Gateway
1. Platform (Telegram/Discord/etc.) -> gateway/platforms/*.py adapter
2. -> normalize to MessageEvent -> dedup + batch -> session key construction
3. -> auth check (pairing) -> session load/create -> context injection
4. -> spawn agent subprocess -> stream consumer buffers tokens
5. -> progressive message edits -> final response -> session save

### Flow 3: Cron Scheduled Task
1. cron/scheduler.py checks croniter expressions -> job fires
2. -> spawn agent with job prompt -> tool execution
3. -> delivery router parses targets (origin/local/platform:id)
4. -> truncate if > 4000 chars -> deliver to platforms -> local fallback

### Flow 4: Skill Learning Loop
1. Agent completes complex task -> tools/skill_manager_tool.py creates skill
2. -> save to ~/.hermes/skills/ -> index in skills registry
3. -> next session: agent/skill_commands.py matches user intent
4. -> inject skill procedure into system prompt -> execute with improvements
5. -> skill self-improves from execution feedback

### Flow 5: MCP Server Integration
1. mcp_serve.py exposes Hermes as MCP server -> external clients connect
2. -> tool discovery via tools/registry.py -> tool invocation
3. -> acp_adapter/ handles ACP protocol translation

## Coupling Analysis

### Tight Coupling
- run_agent.py <-> agent/ — deeply intertwined; agent module extracted FROM run_agent
- hermes_cli/main.py <-> hermes_cli/config.py — config shapes all CLI behavior
- tools/terminal_tool.py <-> tools/environments/ — terminal dispatches to env backends

### Loose Coupling (Intentional)
- gateway/ <-> agent/ — subprocess boundary; gateway spawns agent as child process
- plugins/memory/ <-> agent/memory_manager.py — plugin interface; backends interchangeable
- cron/ <-> gateway/delivery.py — delivery router is pure function; cron just provides targets
- tools/ <-> agent/ — registry pattern; tools register themselves, agent discovers

## Architectural Philosophy

1. Extensibility over performance — Plugin system, adapter pattern, tool registry all prioritize adding new capabilities without modifying core
2. Run anywhere — 6 terminal backends (local, Docker, SSH, Daytona, Singularity, Modal); messaging gateway bridges platforms
3. Self-improvement — Skill learning loop, memory persistence, user modeling (Honcho)
4. Provider agnostic — 100+ LLM providers via unified SDK interface + model normalization
5. Privacy by default — PII redaction in gateway, credential file locking, path security for tools
6. Resilience — Retry with backoff everywhere, graceful degradation (curses -> text -> defaults)

## System Core
- Most stable: hermes_constants.py, utils.py, hermes_logging.py
- Most depended-upon: tools/registry.py, agent/prompt_builder.py, hermes_cli/config.py
- Added later: acp_adapter/ (newest), plugins/ (plugin ecosystem), gateway/platforms/ (expanding)
