# test — Deep Analysis (Phase 1B)

## 1. Existence Rationale

The `test/` directory is where **behavioural parity** across SDKs is enforced. A bug in tool dispatch that manifests only in Python — but not in TypeScript — would be invisible without a cross-SDK conformance suite. `test/snapshots/` stores YAML fixtures describing scenario → expected event stream; `test/harness/` runs each scenario against every SDK and diffs against the snapshot. Without this, the four SDKs would inevitably drift, forcing integrators to test against all four independently.

## 2. Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|---|---|---|---|
| Fixture format | YAML | JSON, TOML, per-language test code | YAML is human-readable, allows multi-line prompts without escaping, supports comments; non-technical reviewers (PMs, docs writers) can inspect scenarios |
| Snapshot style | diffable YAML trees, checked in | video capture, per-run JSON blobs | Reviewable in PRs; failures show WHICH event differs, not just "output differs" |
| Harness location | `test/harness/` — separate from snapshots | `test/<sdk>/` per-SDK | Single driver means the exact same scenario definition reaches all four SDKs; zero per-SDK harness code |
| Scenario organisation | per-feature folders (`tool_results/`, `permissions/`, `hooks_extended/`, etc.) | per-SDK folders | Mirrors the user's mental model (features), not the implementer's (languages); encourages "when adding a feature, add scenarios" |
| Granularity | many small scenarios (one per behaviour) | few long end-to-end scenarios | Small scenarios localise failures; long ones debug poorly |
| Event fidelity | `event_fidelity/` snapshot folder | always capture everything verbosely | Dedicated folder calls out "these tests specifically verify event ordering + payload shape" — contrast with feature tests that ignore noisy fields |

## 3. Algorithm Deep-Dives

### 3.1 Scenario execution flow

**Problem.** Given a YAML scenario, run it through one SDK and produce a deterministic event trace to compare with the expected snapshot.

**Trace.**
1. Parse YAML: extract initial prompt, custom tools, permission policy, follow-up messages, any hooks.
2. Spawn a CLI process using the SDK-specific adapter.
3. Register each declared tool with a deterministic handler (e.g., `get_weather` always returns `"cloudy 60F"`).
4. Install a permission handler that applies the declared policy (approve-all, deny-all, specific-tool).
5. Send the initial prompt; collect events until `session.idle`.
6. If follow-ups exist, send each in turn.
7. Normalise the event stream: strip non-deterministic fields (timestamps, IDs) by either removing them or replacing with `<placeholder>`.
8. Emit the normalised trace as YAML.
9. Diff against the expected snapshot; fail loudly on any mismatch.

**Why.** Alternatives: (a) record-and-replay — brittle; (b) assert specific events — misses changes in event order; (c) just count events — miss payload shape changes. Full diff with normalisation strikes the balance.

### 3.2 Normalisation strategy

Normalisation replaces non-deterministic values with placeholders:
- IDs (`sessionId`, `messageId`, `toolCallId`) → `<ID>`
- Timestamps → `<TIME>`
- Model names → may be `<MODEL>` or fixed to canonical (policy-dependent)
- Stack traces → `<STACK>`
- OS-specific paths → `<PATH>`

This is done by a recursive YAML walker with a known-field list.

## 4. Error Philosophy

Test failures print the unified diff. No attempt to auto-fix — a human must explicitly regenerate snapshots (typically via `--update-snapshots`) and review the diff in a PR. This gates changes with human review and prevents "green CI because test updated itself".

## 5. Performance Characteristics

- One scenario ≈ 2-5s (CLI spawn + model round-trip or recorded playback).
- ~hundreds of snapshots × four SDKs = minutes-scale CI run — acceptable.
- Snapshots run in parallel across SDKs but sequentially within an SDK (CLI subprocess reuse not implemented).

## 6. Evolution Clues

- Snapshot folder names like `ask_user`, `ask-user`, `askuser` (three variants) suggest legacy renames — historically `ask-user` may have been renamed and never consolidated.
- Folders like `mcp_and_agents` and `mcp-and-agents` are similar — another rename remnant.
- `session_lifecycle`, `session_fs`, `streaming_fidelity`, `event_fidelity`, `hooks_extended`, `system_message_transform`, `multi_client`, `permissions`, `skills`, `compaction`, `mcpservers` — a complete roll-call of every SDK feature, each with its own snapshot folder.
