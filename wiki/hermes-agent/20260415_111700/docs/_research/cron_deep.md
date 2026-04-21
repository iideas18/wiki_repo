# cron/ — Scheduled Task System

## Purpose
Scheduled task system using croniter for cron expression evaluation. Jobs are natural-language prompts with delivery targets.

## Key Design Decisions
1. Natural language job definitions over code
2. Multi-target delivery (origin, local, platform:chat_id)
3. Croniter for standard cron expression parsing
4. Integration with gateway delivery router
