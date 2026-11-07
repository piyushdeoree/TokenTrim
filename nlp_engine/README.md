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

Put the `nlp_engine/` folder in the backend project (it must be importable as `nlp_engine`).
Tested on Python 3.12 (uses only standard typing/dataclass features, but older versions are untested). No model downloads, no NLTK corpora, no network access at runtime
(except `tiktoken` fetching its vocabulary file once on first use - see section 5).

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

* `analyze_prompt(prompt, model)` is **synchronous and CPU-bound** (typically milliseconds;
  a 68,000-token prompt took ~2 s). In an `async def` endpoint run it in a thread pool
  (`await run_in_threadpool(analyze_prompt, ...)`) or just declare the endpoint with plain `def`.
* It is stateless and thread-safe; no database, no files, no global mutable state besides
  small caches.
* Requires `pydantic>=2` (uses `model_dump`).

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
| `issues[].type` | one of `redundancy`, `repeated_phrase`, `verbosity`, `duplicate_constraint`, `excessive_context`, `formatting`, `conflict`, `complexity` |
| `issues[].severity` | `low` / `medium` / `high` |
| `optimized_prompt` | the optimized prompt, **or the original prompt unchanged** if no safe optimization exists or the safety check rejected it |

Notes for Person 4 (frontend): `type` is a closed set (above) so it can be mapped to icons/colours.
`conflict` issues are *warnings only* - the engine never resolves conflicts automatically.
`excessive_context` is also a warning only - context is never removed automatically.

### Behaviour you should know about

* **Empty / whitespace prompt** -> `ValueError` (map to HTTP 422).
* **Unknown model name** -> still works, token counts fall back to a labelled estimate.
* **Optimization rejected by the safety check** -> `optimized_prompt == original`, `tokens_saved == 0`,
  and a suggestion explains that the check rejected it.
* The input prompt is never modified in place and nothing is logged or stored.

## 3. Optional extras (not part of the contract)

```python
from nlp_engine import analyze_prompt_detailed, tokenizer_info

d = analyze_prompt_detailed(prompt, "gpt-4o")   # Pydantic object: features, evidence per issue,
d.features, d.issues[0].evidence                #   list of applied changes, validation metrics
d.final.changes, d.validation.metrics

tokenizer_info("claude-sonnet-4-5")             # -> method="heuristic_estimate", exact=False, note=...
```

**Integration question for the team:** because Claude/Gemini token counts are *estimates*
(section 5), it may be worth adding one optional field such as `token_count_method`
(`"tiktoken:o200k_base"` / `"heuristic_estimate"`) to the response so the UI can show
"≈" for estimates. It is **not** in the contract today; `tokenizer_info(model)` already provides it
if you decide to add it.

### Optional LLM-assisted rewriting

```python
def my_rewriter(prompt: str) -> str:      # Person 3 owns the API key / client
    ...                                    # call any LLM, return the rewritten prompt

analyze_prompt(prompt, "gpt-4o", llm_rewriter=my_rewriter)
```

The LLM output is only a *candidate*: it must pass the same validator as the rule-based
output, and the candidate with the larger saving among the valid ones wins. If the rewriter
raises or returns something lossy, it is silently ignored. Default behaviour (no rewriter) is
fully deterministic and makes no network calls.

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
  tests/           pytest suite + the 10 required scenarios + run_evaluation.py
  docs/DOCUMENTATION.md   problem, methodology, limitations (for the report)
```

## 5. Token counting: exact vs estimate (important)

| model family | method | exact? |
|---|---|---|
| OpenAI (`gpt-*`, `o1/o3/o4`) | `tiktoken` encoding for that model | **yes** (when `tiktoken` can load the vocabulary) |
| Anthropic Claude | heuristic estimate | **no** |
| Google Gemini | heuristic estimate | **no** |
| unknown model | heuristic estimate | **no** |
| OpenAI model but `tiktoken` missing/offline | heuristic estimate | **no** |

Claude and Gemini only offer exact counting through their web APIs (API key + network call),
not as an offline tokenizer, so nothing is invented: the engine uses a documented heuristic
(~4 characters per word-piece, ~3 digits per number-piece) and says so via `tokenizer_info()`.
`tiktoken` downloads its vocabulary file the first time an encoding is used; if the backend runs
in an offline environment, pre-warm it (or set `TIKTOKEN_CACHE_DIR`).

**Adding an exact tokenizer later** (e.g. a wrapper around Anthropic's `count_tokens` endpoint):

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
pytest nlp_engine/tests -v                 # 46 tests, ~4 s
python -m nlp_engine.tests.run_evaluation  # measures the 10 scenarios, writes tests/evaluation_results.md
```

## 7. What this module does *not* promise

* It does **not** guarantee semantic equivalence. The validator checks for *detectable* information
  loss (numbers, names, code, URLs, constraints, output format, keywords), nothing more.
* It is **English-only**; text in other scripts is left untouched.
* Heuristic thresholds/weights are design choices, not trained values; no accuracy figures are claimed.

See `docs/DOCUMENTATION.md` for the full methodology and limitations.
