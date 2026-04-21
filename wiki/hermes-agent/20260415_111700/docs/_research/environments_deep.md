# environments/ — RL Training Environments

## Purpose
RL training environments for Hermes agent models with Atropos integration. Includes base environment, agent loop for trajectory generation, benchmark environments, and 11 tool call parsers.

## Key Design Decisions
1. Atropos base class for standardized RL interface
2. Separate tool call parsers per LLM format for accuracy
3. AgentLoop extracted for reuse across environments
4. ToolContext for sandboxed execution within environments
