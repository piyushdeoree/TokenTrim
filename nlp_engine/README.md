# nlp_engine - Prompt Analysis & Optimization Module

AI/NLP module of *"AI Cost Intelligence and Prompt Optimization Platform for LLMs"*.

```
PROMPT -> TOKEN ANALYSIS -> NLP ANALYSIS -> OPTIMIZATION -> VALIDATION -> OPTIMIZED PROMPT + TOKEN REDUCTION
```

**Out of scope (Person 2):** cost calculation, output-token prediction, forecasting, model recommendation.
This module only deals with prompt text and token counts.

---

## 1. Install

```bash
pip install -r nlp_engine/requirements.txt
```

Put the `nlp_engine/` folder in the consuming project (it must be importable as
`nlp_engine`). The current local verification environment is Python 3.13.5;
this project does not declare a supported Python-version range. The core
analysis does not download NLTK corpora. `tiktoken` may fetch an encoding file
on first use, and enabling the optional semantic model may download model files
if they are not already cached and network access is available.

## 2. Use it from FastAPI (Person 3)

```python
from fastapi import FastAPI, HTTPException
from nlp_engine import analyze_prompt, PromptRequest, AnalysisResponse

app = FastAPI()

@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze(req: PromptRequest):
    try:
        return analyze_prompt(req.prompt, req.model)      # plain dict, matches AnalysisResponse
    except ValueError as exc:                             # empty prompt
        raise HTTPException(status_code=422, detail=str(exc))
```

* `analyze_prompt(prompt, model)` is **synchronous and CPU-bound**. Runtime varies
  substantially with input size; see the standalone performance report for local
  measurements. In an `async def` endpoint run it in a thread pool
  (`await run_in_threadpool(analyze_prompt, ...)`) or just declare the endpoint with plain `def`.
* Per-call analysis state is local, but tokenizer registrations and the optional
  semantic-model cache are process-global. Concurrent calls are not documented
  as safe while registering tokenizers or during first-time semantic-model loading.
  Ordinary analysis does not persist prompts to a database or file.
* Requires `pydantic>=2` (uses `model_dump`).

### Public Python API

The package root exports `analyze_prompt`, `analyze_prompt_detailed`,
`build_analysis`, `optimize_prompt`, `validate_optimization`, `count_tokens`,
`tokenizer_info`, and `register_tokenizer`. It also exports `PromptRequest`,
`AnalysisResponse`, `Issue`, `DetailedAnalysis`, `OptimizationResult`,
`ValidationResult`, `TokenizerInfo`, and `BaseTokenCounter`.

`build_analysis()` remains exported for compatibility but is a lower-level
helper whose `PromptAnalysis` return type is internal and is not root-exported.
`optimize_prompt()` returns an `OptimizationResult` candidate; it does not
validate or accept that candidate. Use `analyze_prompt()` or
`analyze_prompt_detailed()` for the validated, savings-aware pipeline.

### Request

```json
{ "prompt": "user's original prompt", "model": "gpt-4o" }
```

### Response (the agreed contract - exactly these fields)

```json
{
  "original_tokens": 65,
  "optimized_tokens": 35,
  "tokens_saved": 30,
  "reduction_percentage": 46.15,
  "word_count": 38,
  "complexity_score": 10.2,
  "issues": [
    {"type": "redundancy", "severity": "medium", "description": "Repeated instruction detected"}
  ],
  "suggestions": ["Remove repeated instructions"],
  "optimized_prompt": "Analyze the following text. Provide a detailed summary. Ensure the summary is clear, concise, and easy to understand."
}
```

| field | meaning |
|---|---|
| `original_tokens` / `optimized_tokens` | token counts for the **selected model** (see section 5: exact vs estimate) |
| `tokens_saved`, `reduction_percentage` | never negative; `0` / `0.0` when nothing safe could be removed |
| `word_count` | words in the original prompt |
| `complexity_score` | 0-100 heuristic indicator (higher = more complex), see `docs/DOCUMENTATION.md` |
| `issues[].type` | a general string; current detectors use types such as `redundancy`, `repeated_phrase`, `verbosity`, `duplicate_constraint`, `excessive_context`, `formatting`, `conflict`, and `complexity`, but the model does not enforce a closed set |
| `issues[].severity` | `low` / `medium` / `high` |
| `optimized_prompt` | the optimized prompt, **or the original prompt unchanged** if no safe optimization exists or the safety check rejected it |

`conflict` issues are *warnings only* - the engine never resolves conflicts automatically.
`excessive_context` is also a warning only - context is never removed automatically.

### Behaviour you should know about

* **Empty / whitespace prompt** -> `ValueError` (map to HTTP 422).
* **Unknown model name** -> still works, token counts fall back to a labelled estimate.
* **Optimization rejected by the safety check** -> `optimized_prompt == original`, `tokens_saved == 0`,
  and a suggestion explains that the check rejected it.
* If no candidate is accepted, the final prompt is the exact original string,
  including leading/trailing whitespace and line breaks. Accepted candidates
  are validated against the exact original input.
* There is no documented maximum prompt size; larger prompts can take much
  longer and use more memory. See the measured standalone benchmark before
  selecting deployment limits.

## 3. Optional extras (not part of the contract)

```python
from nlp_engine import (
    DetailedAnalysis, OptimizationResult, ValidationResult, TokenizerInfo,
    analyze_prompt_detailed, tokenizer_info,
)

d = analyze_prompt_detailed(prompt, "gpt-4o")   # Pydantic object: features, evidence per issue,
d.features, d.issues[0].evidence                #   list of applied changes, validation metrics
d.final.changes, d.validation.metrics

tokenizer_info("claude-sonnet-4-5")             # -> method="heuristic_estimate", exact=False, note=...
```

`count_tokens()` returns four integer statistics and does not include tokenizer
metadata. Use `tokenizer_info(model)` for `method`, `exact`, and `note`, or
`detailed.token_stats` for metadata alongside the analysis. The simple response
shape is unchanged and does not identify exact versus estimated counts.

`DetailedAnalysis` exposes measured features, issue evidence, suggestions, the
reported candidate, its validation result, the final result, and
`optimization_accepted`. When a candidate is accepted, `candidate` and
`validation` describe the selected winning candidate. When no candidate is
accepted, they describe the first (heuristic) candidate and its validation;
they do not contain a validation record for every LLM candidate considered.
`final` is the accepted result or an unchanged copy of the original prompt with
zero savings. `OptimizationResult` contains the candidate/final prompt, counts
for original and rewritten text, nonnegative token savings, percentage, change
descriptions, and the method (`heuristic`, `llm`, or `none`).

### Optional LLM-assisted rewriting

```python
def my_rewriter(rewrite_request: str) -> str:  # receives full request, not raw prompt
    ...                                    # call any LLM, return the rewritten prompt

analyze_prompt(prompt, "gpt-4o", llm_rewriter=my_rewriter)
```

The callback receives a complete rewrite request containing the JSON-encoded
original prompt and preservation rules. Its non-empty string response is only a
candidate: it must pass the same validator and save tokens. A callback exception,
empty response, non-string result, or token-counting failure is ignored; the
heuristic candidate remains available, and the original prompt is returned if
no candidate qualifies. The engine itself makes no provider call. Default
behaviour (no callback) is deterministic and makes no network calls.

## 4. Package layout

```
nlp_engine/
  __init__.py      public API: analyze_prompt, analyze_prompt_detailed, optimize_prompt, ...
  config.py        every threshold, word list, weight and rewrite rule (documented)
  textutils.py     masking of code/URLs/quotes/JSON, sentence segmentation, classification, rewrite rules
  tokenizer.py     count_tokens(prompt, model) + tokenizer registry
  redundancy.py    repeated instructions, duplicate constraints, repeated phrases
  analyzer.py      verbosity / context / formatting / conflict detectors + analyze_prompt()
  complexity.py    complexity features and 0-100 score
  optimizer.py     optimize_prompt(prompt, analysis) (+ optional LLM hook)
  validator.py     validate_optimization(original, optimized)
  models.py        Pydantic models (contract + detailed) and internal state
  tests/           pytest suite, evaluation corpora, and standalone benchmarks
  docs/DOCUMENTATION.md   problem, methodology, limitations (for the report)
```

## 5. Token counting: exact vs estimate (important)

| model family | method | exact? |
|---|---|---|
| Recognized OpenAI model (`gpt*`, `o1/o3/o4`, `text-*`, `chatgpt*`) | `tiktoken` encoding or configured prefix fallback | **yes** when an encoding loads |
| Anthropic Claude | heuristic estimate | **no** |
| Google Gemini | heuristic estimate | **no** |
| unknown model | heuristic estimate | **no** |
| OpenAI model but `tiktoken` missing/offline | heuristic estimate | **no** |

This engine does not call provider token-count APIs. For Claude and Gemini, it uses a documented heuristic
(~4 characters per word-piece, ~3 digits per number-piece) and says so via `tokenizer_info()`.
`tiktoken` downloads its vocabulary file the first time an encoding is used; if the backend runs
in an offline environment, pre-warm it (or set `TIKTOKEN_CACHE_DIR`).

`tokenizer_info(model)` reports the selected method and whether it is exact.
`count_tokens()` returns only counts; it does not return this metadata. Token
counts cover the provided text, not provider-specific chat framing or billing
overhead. `sentence_count` is the number of layout-aware segments produced by
the rule-based segmenter (which can include list items), not a linguistic
sentence count.

Custom counters can be registered with `register_tokenizer()`. Registrations
are process-global, take precedence over built-in matching, clear the counter
cache, and remain active for the process lifetime; there is no unregister API.
The interface and metadata type are available from the package root or from
`nlp_engine.tokenizer`.

The optional semantic similarity model is separate from token counting. It is
disabled by default and requires the optional `sentence-transformers` package,
which is not installed by `nlp_engine/requirements.txt`. Configuration:

| Environment variable | Default | Purpose |
|---|---|---|
| `TOKENTRIM_ENABLE_SEMANTIC_MODEL` | `false` | Explicitly enable model-based similarity |
| `TOKENTRIM_SEMANTIC_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Model name or local model path |
| `TOKENTRIM_SEMANTIC_DEVICE` | `cpu` | Sentence-Transformers device, such as `cpu` or `cuda` |

Loading is lazy. If enabled and the model is not cached, the library may try to
download it. A missing dependency or load/encoding failure falls back to the
non-model analysis path. Semantic similarity is advisory and cannot authorize
deletion by itself.

Example custom counter:

```python
from nlp_engine.tokenizer import register_tokenizer, BaseTokenCounter, TokenizerInfo

class ClaudeApiCounter(BaseTokenCounter):
    info = TokenizerInfo("claude", "anthropic", "anthropic_count_tokens_api", True, "exact via API")
    def count(self, text: str) -> int: ...      # call the API

register_tokenizer("claude-api", lambda m: m.startswith("claude"), lambda m: ClaudeApiCounter())
```

Savings are always computed with the **same** counter for the original and the optimized prompt, so
the *difference* is consistent even when the absolute numbers are estimates.

## 6. Tests

From the folder that contains `nlp_engine/`:

```bash
python -m pytest nlp_engine/tests -v
python -m nlp_engine.tests.run_evaluation       # 10 baseline scenarios
python -m nlp_engine.tests.benchmark_runner     # 50-case redundancy benchmark
python -m nlp_engine.tests.run_realistic_evaluation  # 20 realistic public-pipeline cases
python -m nlp_engine.tests.run_performance_benchmark # standalone performance run (not pytest)
```

The performance benchmark writes a reproducible JSON result and Markdown report under
`nlp_engine/tests/`. It uses CPU-only workers, blocks network access, and defaults to an
offline probe for an already-cached semantic model. Use `--skip-local-model` to omit that
probe or `--scenario small_2k` for a focused run. Synthetic semantic-stub timings are
reported separately and do not represent pretrained-model performance.

The regression suite also runs the curated redundancy cases through the full
analysis, optimization, and validation pipeline. See
[`docs/NLP_ENGINE_ROADMAP.md`](docs/NLP_ENGINE_ROADMAP.md) for the current
completion gates and progress status.

The realistic evaluation writes
`nlp_engine/tests/realistic_evaluation_results.md`. It uses a fixed heuristic
token estimate and deterministic callback candidates; the report distinguishes
false removals from missed optimization opportunities and is not a general
accuracy claim.

## 7. What this module does *not* promise

* It does **not** guarantee semantic equivalence. The validator checks for *detectable* information
  loss (numbers, names, code, URLs, constraints, output format, keywords), nothing more.
* It is **English-only**; text in other scripts is left untouched.
* Heuristic thresholds/weights are design choices, not trained values; no accuracy figures are claimed.
* Protected-span recognition is pattern-based, not general quote parsing. It
  includes fenced and inline backticks, triple-double-quoted blocks, URLs,
  e-mail addresses, simple same-line double-quoted strings and curly-quoted
  strings (up to 500 characters), and balanced braces/brackets. General
  straight single-quoted strings are not protected by a dedicated pattern;
  do not treat every quoted form as guaranteed untouched.

See `docs/DOCUMENTATION.md` for the full methodology and limitations.
