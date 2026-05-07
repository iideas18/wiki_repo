# Phase 1B Deep Analysis — `evaluation/`

## Existence rationale

`evaluation/` provides **quantitative scoring of LLM outputs** so users can answer "did my prompt/model change make things better?". It bundles ten flavours of evaluator — exact match, regex match, embedding distance, string distance, QA correctness, criteria (LLM judge), pairwise comparison, scoring, and trajectory eval (for agents) — under a uniform `load_evaluator(EvaluatorType.X)` API. Without it, every team would re-implement Levenshtein + cosine + LLM-as-judge from scratch.

## Design decisions

| Decision | Choice | Alternative | Rationale |
|---|---|---|---|
| Loader factory + enum | `load_evaluator(EvaluatorType.QA)` | Direct class instantiation | Single discoverable surface; supports lazy import of optional deps |
| `StringEvaluator` vs `PairwiseStringEvaluator` vs `AgentTrajectoryEvaluator` ABCs | Three contracts | One generic | Each takes different inputs (prediction vs A/B vs trajectory); separate ABCs prevent confusion |
| Criteria evaluator uses an LLM judge with CoT | LLM rates on `helpfulness`, `correctness`, etc., with chain-of-thought before score | Direct rating | CoT improves judge consistency (Anthropic eval studies); reduces "always 5/10" failure mode |
| Embedding distance pluggable | Cosine / Euclidean / Manhattan / Chebyshev / Hamming | Cosine only | Different embeddings calibrate differently; users pick |
| String distance via `rapidfuzz` (optional) | Lazy-import; raise if not installed | Bundle | Keeps the base install lightweight |

## Algorithm deep-dive — Criteria evaluator

**Trace.**
1. User picks a criterion (`"helpfulness"`, or a custom dict).
2. The judge LLM is shown the *input*, the *prediction*, optionally the *reference*, and the criterion description.
3. Prompt asks for *step-by-step reasoning* then a `Y/N` verdict.
4. A specialized output parser extracts the verdict from the CoT.
5. Returns `{"score": 1 if Y else 0, "value": Y/N, "reasoning": cot_text}`.

**Why CoT.** Without it, judge LLMs collapse to "Y" most of the time; with it, the model has to articulate *why*, which exposes failure modes the user can act on.

## Error philosophy

**Loud failures, no silent zeros.** A failed parser raises rather than returning 0 — silent zeros would corrupt aggregate metrics. Aggregation is the user's job (or LangSmith's).

## Sub-modules at a glance

- `criteria/` — LLM judge with chain-of-thought
- `qa/` — exact-match and LLM-checked answer correctness
- `string_distance/` — Levenshtein, Jaro-Winkler, etc. via rapidfuzz
- `embedding_distance/` — cosine / euclidean / manhattan / chebyshev / hamming
- `comparison/` — pairwise A/B with LLM judge
- `scoring/` — Likert-scale scoring with reasoning
- `agents/` — `TrajectoryEvalChain` scores the entire agent trajectory (correctness + tool use)
- `parsing/` — checks parser output validity
- `regex_match/`, `exact_match/` — deterministic matchers
