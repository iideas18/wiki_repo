# hermes_cli/ — CLI Interface

## Purpose
The hermes_cli/ module provides the unified command-line interface and terminal UI for Hermes Agent. It orchestrates interactive chat sessions, configuration management, authentication flows, model selection, gateway lifecycle, tool/skill discovery, and multi-profile support.

## Key Design Decisions
1. Command Registry as decoupled data - all consumers subscribe to COMMAND_REGISTRY
2. Profile pre-parse before imports - set HERMES_HOME env before any module loads
3. Auth store file locking with timeout - fcntl/msvcrt cross-process lock
4. Managed mode via env + marker - NixOS/Homebrew detection
5. Provider identity separate from runtime credentials - separation of concerns
6. Curses graceful degradation - curses -> text -> defaults for any terminal
7. Config atomicity - tmpfile -> fsync -> atomic rename
8. OAuth device code flow for Nous Portal - short-lived keys per session

## Architecture
Argparse entry point routes to cmd_* handlers. Provider resolution pipeline with priority chain. Credential pool with multi-key rotation.

## Error Philosophy
Fail with clear guidance. Suggest close matches for unknown providers/models. Return defaults when non-TTY. Timeout and retry for locked resources.
