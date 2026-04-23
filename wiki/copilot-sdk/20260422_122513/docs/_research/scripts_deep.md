# scripts — Deep Analysis (Phase 1B)

## 1. Existence Rationale

`scripts/` is the **contract enforcement layer**. It exists because four parallel SDKs can diverge silently: a TypeScript engineer adds a new field to an event; .NET lacks that field; user code compiles but crashes at runtime. By generating RPC bindings and event types from a single shared JSON Schema — the one the CLI itself publishes via `@github/copilot/schemas/*.json` — the SDKs cannot drift on the wire contract. The only divergence allowed is in business logic, which is verified by the conformance tests.

## 2. Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|---|---|---|---|
| Source of truth | JSON Schemas shipped with the CLI npm package | hand-maintained IDL, protobuf, Smithy | The CLI *already* emits these for its own validation — co-locating with consumption means no human sync step |
| Codegen language | TypeScript | Python, Go, bash | All codegen authors will know TS (reference SDK authors); `json-schema-to-typescript` and `quicktype` are npm-ecosystem-first |
| Language-specific emitters | four separate files (`typescript.ts`, `python.ts`, `go.ts`, `csharp.ts`) | one file with dispatch | Per-language idioms differ enough that a shared emitter would be more if/else than shared logic |
| Hand-patch regions | `corrections/` folder | full codegen + manual patches in PRs | Codegen can't produce idiomatic Go discriminated unions or C# polymorphic converters perfectly; corrections let the mostly-automatic output be "finished" |
| Deterministic output | alphabetical property sort in post-processing | emission order preserved | Determinism matters for code review — a reviewer should see only *semantic* diffs, not "the tool reordered things" noise |
| External tooling | `quicktype` via `execFile` for Py/Go/C# | native TS libraries for each lang | `quicktype` is the industry-standard multi-lang emitter; reinventing per-lang emitters wastes effort |
| `postProcessSchema` normalisation | boolean const → enum, nullable-ref fixups | accept whatever codegen emits | Quicktype chokes on `{ "const": true }` (treats as ambiguous); the post-process normalises weird-but-legal schema to common-subset schema |

## 3. Algorithm Deep-Dives

### 3.1 Schema post-processing pipeline

**Problem.** `api.schema.json` and `session-events.schema.json` are correct per JSON-Schema-Draft-7, but several emitters (`quicktype`, `json-schema-to-typescript`) have bugs or quirks around edge cases. Fixing emitters upstream is a multi-month effort; fixing the input is instant.

**Trace.**
1. Read JSON file.
2. `postProcessSchema`: recurse the tree. At every object:
   - If `const` is boolean, replace with `enum: [value]` (quicktype can't handle boolean const).
   - Sort `properties` keys alphabetically (deterministic output).
   - Recurse into each property.
3. `fixNullableRequiredRefsInApiSchema`: any field declared as `{ "$ref": "#/defs/X" }` that is also listed in `required: [...]` and whose referent has `nullable: true` is rewritten to `{ "oneOf": [ {"$ref":"..."}, {"type":"null"} ] }`. Without this, nullable required refs deserialise as "absent field" instead of "present null".
4. `withSharedDefinitions`: merge the schema's `definitions` and `$defs` into a single top-level `definitions` map so emitters see one namespace.
5. Emitter-specific: `typescript.ts` calls `json-schema-to-typescript`'s `compile()` on each relevant entry; `python.ts` etc. shell out to `quicktype --lang python --src-lang schema ...`.

**Complexity.** O(N) in schema node count. Runs once per language per regen.

**Why.** Normalising the schema upstream of the emitter means only ONE place knows about emitter quirks; adding a fifth language doesn't require re-tracing the same bugs.

### 3.2 RPC-method vs type discrimination

**Problem.** The API schema mixes plain types (like `Session`) with RPC methods (like `session.send`). Naïve codegen would emit a type called `SessionSend` instead of a method.

**Trace.**
1. `isRpcMethod(node)` checks for a special marker: the node has both `request` and `response` sub-schemas, or a `method` property with a dotted name.
2. `collectDefinitionCollections(schema)` walks the tree and partitions nodes into `{ rpcMethods: [...], types: [...] }`.
3. Per-language emitter handles each list with its own template: TS emits a discriminated `RpcMethod` union + factory function; Python emits a typed method on `ServerRpc`; Go emits generated functions on `ServerRpc` struct; C# emits partial class methods.

### 3.3 Handling experimental and deprecated RPCs

**Problem.** The protocol has some experimental RPCs that shouldn't be emitted to end users yet, and deprecated ones that should emit with warnings.

**Trace.**
1. Each RPC node may carry `"x-experimental": true` or `"x-deprecated": true` annotations.
2. `isNodeFullyExperimental(node)` + `isNodeFullyDeprecated(node)` bubble these flags through nested refs.
3. Emitter decides: experimental → emit to a separate `experimental` namespace (Python) or skip entirely (TypeScript until "stable"); deprecated → emit with `@deprecated` / `Obsolete` annotation.

## 4. Error Philosophy

Codegen either succeeds or throws. No partial output. Output is written via `writeGeneratedFile` which (a) verifies the target path is within an expected SDK directory, (b) writes a sentinel comment (`// This file is generated, do not edit`), (c) diffs against existing on-disk content and exits non-zero if `--check` mode is enabled (CI-friendly). This catches "someone forgot to regen before opening a PR".

## 5. Performance Characteristics

- Runs in ~3-8 seconds per language (Node startup + quicktype spawn dominates).
- `execFileAsync` parallelism: the four languages could run concurrently, but the current script runs them sequentially — CPU-cheap, so not a concern.
- Output files are small (~1-3k lines each), version controlled, diffable.

## 6. Evolution Clues

- `scripts/corrections/` has a `test/` subfolder — suggests patch regions were getting fragile and needed verification.
- `scripts/docs-validation/` co-located with codegen — both are "CI-enforced correctness" concerns.
- The presence of `quicktype` dependency but also `json-schema-to-typescript` suggests TypeScript gets the higher-fidelity lib while the other three use the general-purpose one.
- `utils.ts` is called `utils.ts` (not `schema-loader.ts` or `post-process.ts`) — classic "started small, grew" naming.
