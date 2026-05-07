# Phase 1B Deep Analysis — `output_parsers/`

## Existence rationale

`output_parsers/` turns **raw LLM text into typed Python values**: a Pydantic instance, a JSON dict, a list, an enum, a regex match group. The module exists because LLMs are unreliable serialisers — they emit JSON with markdown fences, forget closing braces, hallucinate fields, and occasionally refuse the format. The parsers wrap a forgiving extraction step in a `Runnable` so they slot into LCEL pipelines (`prompt | llm | parser`); two of them — `OutputFixingParser` and `RetryOutputParser` — go further, calling the LLM **again** with the failure to self-correct.

## Design decisions

| Decision | Choice | Alternatives | Rationale |
|---|---|---|---|
| Parser is a Runnable | `BaseOutputParser` is `Runnable[str, T]` | Plain function | Composes with LCEL; gets callbacks for free |
| `format_instructions` method | Each parser produces the prompt fragment that tells the LLM how to format its output | Manual prompt engineering | Keeps schema and instructions in sync (Pydantic-derived JSON-schema is the truth) |
| `parse_with_prompt` for self-correcting parsers | RetryOutputParser receives original prompt + LLM output to retry | Retry without context | Without the prompt, the corrector LLM doesn't know the target |
| Pydantic-based structure parser | `PydanticOutputParser[T]` validates against `T.schema()` | hand-written validators | Free validation + descriptive error messages |
| JSON markdown extraction | `parse_json_markdown` strips ```json fences before json.loads | strict json.loads | LLMs love markdown; tolerate it |

## Algorithm deep-dives

### 1. Retry vs Fix

`OutputFixingParser`:
1. `parse(text)` → on `OutputParserException`, call LLM with template "fix this output that failed to parse" + parser's `format_instructions` + the bad text.
2. Re-parse the fix.
3. Up to N retries.

`RetryOutputParser`:
1. Same flow, but the retry prompt also includes the *original prompt* — useful when failure was caused by misunderstanding the request, not just bad formatting.

The split matters: `Fix` is cheap (one extra LLM call with only the bad text + instructions), `Retry` is more expensive but recovers from semantic errors.

### 2. PydanticOutputParser

**Trace.**
1. `format_instructions` = boilerplate + `json.dumps(model.schema())` + example.
2. `parse(text)`:
    - Strip markdown fences.
    - `json.loads`.
    - `Model(**parsed)` — Pydantic v1 raises `ValidationError`.
    - On any exception → wrap in `OutputParserException(message, llm_output=text)`.

The `OutputParserException.send_to_llm = True` flag tells `OutputFixingParser` whether the error is recoverable (default yes).

## Error philosophy

**Strict but recoverable.** `parse` raises a typed exception with the offending text attached so a wrapping retry/fix parser can self-heal. Final raise is structured (`OutputParserException`) so chains can handle it specifically.
