# gateway/ — Multi-Platform Messaging Gateway

## Purpose
The gateway module serves as a unified messaging bridge enabling autonomous communication across Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email, SMS, and 10+ other platforms through a single adapter abstraction.

## Key Design Decisions
1. Adapter Pattern over monolithic branching - maintainability at scale
2. Subprocess boundary between gateway and agent - crash isolation
3. Session key construction - deterministic routing from (platform, chat_id, thread_id, user_id)
4. Progressive streaming via queue-based consumer - rate limit resilience
5. Pairing codes for DM authorization - dynamic, no config edits needed
6. Conditional PII redaction - privacy balanced with functionality
7. Dual-layer storage (JSONL + SQLite) - backward compatibility
8. Message batching with adaptive delays - no self-interruption

## Architecture
GatewayRunner orchestrates 18+ platform adapters, SessionStore, DeliveryRouter, StreamConsumer, and HookRegistry.

## Error Philosophy
Resilience over perfection - Platform A failure does not affect Platform B. Exponential backoff on rate limits. Graceful degradation from progressive edits to final send.
