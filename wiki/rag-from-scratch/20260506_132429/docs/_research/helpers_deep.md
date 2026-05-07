# Phase 1B — Deep Analysis: `helpers/`

## Existence Rationale

`helpers/` is the **infrastructure boundary** between every lesson and the
outside world (terminal, OpenAI, llama.cpp). Without it, every `example.js`
would re-implement chalk-coloured headers, ora spinners, OpenAI API
boilerplate, and llama.cpp model-loading. By centralising these, the
lessons can focus on *the concept being taught* without drowning in setup
boilerplate.

Crucially, `helpers/` is **not** a candidate for promotion to `src/`. The
`src/` library is what a downstream consumer imports; helpers are what
**the demos** rely on for chrome and CLI ergonomics. They're stylistic, not
architectural.

## Files

| File | LOC | Role |
|------|-----|------|
| `output-helper.js` | 85 | `OutputHelper` static class with chalk/ora wrappers, `runExample()`, chunk preview |
| `openai-prompter.js` | 28 | `OpenAIClient` thin wrapper around `openai.responses.create()` |
| `llama-prompter.js` | 39 | `LlamaPrompter` simpler local-LLM wrapper (used directly by 06/05_query_rewriting) |

## Design Decisions Analysis

| Decision | Choice Made | Alternatives | Inferred Rationale |
|----------|-------------|--------------|---------------------|
| OutputHelper as static class | All methods static, no state | Module of free functions; instance-based logger | Static keeps call-sites short (`OutputHelper.log.info(…)`); also matches the "namespace pattern" common in JS demos. |
| Two LLM wrappers (`LlamaPrompter` + `LlamaCpp`) | Coexisting | Pick one | `LlamaPrompter` is simpler — it skips `BaseLLM` inheritance and grammar plumbing, so a learner can read 39 lines and understand the call. `LlamaCpp` is what a *library* would expose. |
| OpenAI via `responses.create` | New "Responses API" | Chat completions API | Matches OpenAI's most recent recommended interface. |
| `dotenv/config` import-side effect | At top of `openai-prompter.js` | Manual `process.env` checks | Reads `.env` automatically — every lesson "just works" if the user copied `.env_example`. |
| Spinners via ora | `withSpinner(message, fn)` higher-order | Inline `console.log` | Long ops (model load, batch embed) show progress; failure auto-reports `spinner.fail(msg)`. |

## Algorithm Deep-Dives

### `OutputHelper.runExample(title, fn, subtitle)`

A higher-order pattern that wraps every lesson body:

```javascript
static async runExample(title, fn, subtitle = '') {
  this.createHeader(title, subtitle);
  const t0 = Date.now();
  try {
    await fn();
    console.log(chalk.green(`\nCompleted in ${(Date.now() - t0) / 1000}s\n`));
  } catch (e) {
    console.error(chalk.red(`Failed: ${e.message}`));
  }
}
```

**Why this matters.** Every lesson ends up wrapped in this — it's the *demo
shell*. Result: consistent visual formatting across 15 lessons, automatic
timing, error capture. Without it, each lesson would re-implement try/catch
+ timing + header.

### `OutputHelper.analyzeChunks(chunks)`

Returns `{avg, min, max, median}` over chunk character lengths. Sorts in-place
(buggy if reused — but lesson code throws away the array immediately).

## Error Philosophy

`helpers/` **isolates the error**: `withSpinner` calls `spinner.fail(err.message)`
then re-throws, so the lesson's outer `runExample` catch block reports it
nicely. `OpenAIClient.send()` logs and re-throws — the reader sees the
network error in red and the stack trace in standard error.

## Performance Characteristics

Negligible. These are CLI-output utilities. The only meaningful cost is the
ora spinner's render loop (~60Hz) which is invisible compared to the model
calls underneath.

## Evolution Clues

- `LlamaPrompter` and `src/llms/LlamaCpp` overlap heavily — the former is
  simpler and used directly by examples; the latter is the library form.
  The duplication suggests the author hasn't yet decided whether examples
  should use the library or stay standalone. Current answer: **standalone for
  early lessons; library for later**.
- `OutputHelper.formatChunkPreview` references `chunk.metadata.loc.pageNumber`
  — that schema came from `PDFLoader`. Tight coupling, but acceptable
  because the helper exists *for* the lessons that consume PDF output.
