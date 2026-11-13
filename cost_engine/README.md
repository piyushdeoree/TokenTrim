# cost_engine

Cost Intelligence module (Person 2) for the *AI Cost Intelligence and Prompt Optimization Platform for LLMs*.

Pipeline: `token data → output prediction → cost calculation → forecasting → model comparison → model recommendation`

## Quick start

```bash
pip install -r cost_engine/requirements.txt
python -m cost_engine.data.generate_synthetic --rows 5000   # SYNTHETIC data, dev only
python -m cost_engine.prediction                            # trains + writes metrics
python -m pytest cost_engine/tests -v
```

Run commands from the repo root so `cost_engine` is importable.

## Public API (for FastAPI)

```python
from cost_engine import (estimate_cost, estimate_cost_api, predict_output_tokens,
                         forecast_cost, compare_models, recommend_model, calculate_savings)

pred = predict_output_tokens(1200, task_type="summarization", model="gpt-4o")
est  = estimate_cost("gpt-4o", 1200, pred["predicted_output_tokens"], prediction_source=pred["source"])
cmp_ = compare_models(1200, pred["predicted_output_tokens"])
rec  = recommend_model(1200, pred["predicted_output_tokens"], task_type="summarization",
                       required_quality="medium", current_model="gpt-4o")
fc   = forecast_cost([12.1, 13.4, 11.8, ...], "30_days")
sav  = calculate_savings("gpt-4o", original_tokens=1200, optimized_tokens=900)   # Person 1 values
```

| Function | Returns |
|---|---|
| `estimate_cost` | `model, input_tokens, predicted_output_tokens, total_tokens, input_cost, output_cost, estimated_cost` (+ `prediction_source`) |
| `estimate_cost_api` | same, with section-10 names (`estimated_input_cost`, ...) |
| `predict_output_tokens` | `predicted_output_tokens, source` (+ warnings) |
| `forecast_cost` | `historical_cost, forecast, forecast_period, estimated_future_cost, method, backtest` |
| `compare_models` | `models` / `comparisons`, `cheapest_model` |
| `recommend_model` | `recommended_model, reason, estimated_saving` |

All functions raise `ValueError` / `TypeError` / `UnknownModelError` on bad input; map these to HTTP 422/404 in FastAPI.

## Pricing

Prices live in `data/pricing.json`; the single authoritative price-version history is `data/pricing_history.json`, and provider refresh reports are stored in `data/pricing_refresh_state.json`. **Bundled prices are illustrative and unverified.**

Provider-specific adapters parse official sources:

- OpenAI: [API pricing](https://developers.openai.com/api/docs/pricing), fetched from the documented Markdown representation. Standard, Batch, Flex, Fast, and Ultrafast token tables are extracted where present. Short/long context, cache read/write durations, and published regional modifiers are retained as tier conditions. The legacy calculator uses Standard short-context rates.
- Anthropic: [Claude Platform pricing](https://platform.claude.com/docs/en/about-claude/pricing), fetched from its docs Markdown representation. Standard rates, 5m/1h cache writes, cache hits, Batch, Fast, retired/limited availability, and prompt-length variants are parsed. Model IDs are normalized from the official model display names.
- Google Gemini: [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing), parsed from the official page's published Markdown layout or HTML tables. Standard, Batch, Flex, Priority, time-bound rates, cache-token rates, model IDs, context limits where published, and cache storage conditions are retained.

All prices are `Decimal` in memory and serialized to JSON as decimal strings. Source-format changes, incomplete/invalid rows, and wrong source/provider identities fail the provider snapshot closed. Other providers are still attempted; failure never overwrites that provider's last valid catalogue. Manual rates remain `manual_unverified`; a matching official URL cannot promote them.

Call `refresh_pricing()` to update providers whose 24-hour interval is due (`COST_ENGINE_REFRESH_INTERVAL_HOURS` configures the interval). Use `refresh_pricing(force=True)` for an immediate attempt, or `refresh_openai_pricing()`, `refresh_anthropic_pricing()`, and `refresh_google_pricing()` for one provider. There is no resident scheduler. A backend job can call these functions and inspect per-provider results, attempt/success timestamps, and changed model IDs.

Use `get_pricing_history(model)` to inspect prior versions and `get_pricing_version(model, version)` plus `calculate_cost(..., pricing_version=version)` to calculate against a preserved version. A new version is created only for a rate/tier/condition change. `pricing_freshness()` computes stale status dynamically from `last_verified` (30 days by default; `COST_ENGINE_PRICING_MAX_AGE_DAYS` configures it). Manual/unverified records are always marked stale for “live verified” use. Stale status is not persisted on the price record.

## Architecture and calculation

The legacy package modules remain public. Pricing records carry source, status, version, effective date, tier, context, and optional cache/batch rates. `calculate_cost` performs monetary arithmetic with `Decimal` and returns float fields for backwards-compatible API serialization. Cached input is a subset of input tokens and is removed from ordinary input billing before its cache rate is applied. Unsupported cache or cache-write rates are rejected; batch rates fall back to standard rates only when no batch rate is listed. All estimates remain estimates, not actual provider invoices.

`compare_prompt_cost(prompt, model, expected_output_tokens=...)` calls the existing `nlp_engine.analyze_prompt()` interface and uses the same output-token assumption and pricing version for original and optimized prompt estimates. Prediction returns a point estimate plus a broad fallback or held-out-MAE range; synthetic training artifacts are not validated against real provider behavior. Model comparison ranks cost only and reports freshness/source/context. Recommendation quality tiers remain subjective metadata, not measured capability.

Forecasting consumes caller-provided daily actual costs; `aggregate_usage_costs()` aggregates dated records daily, weekly, or monthly. Forecasts report a residual-based range when backtesting is possible and a standard-deviation fallback otherwise. Three points are the minimum; that is still too little history for a reliable forecast. `analyze_savings()` reports spend distribution and threshold findings without asserting an uncalculated model switch.

Optional `convert_usd_to_inr()` fetches a timestamped USD/INR rate from Frankfurter and caches the last valid rate. Failure returns the cached rate marked stale, or raises when no valid rate exists. Provider catalogue rates remain USD; INR is a separate display conversion.

Backend storage/API work is described in [INTEGRATION_REQUIREMENTS.md](INTEGRATION_REQUIREMENTS.md). The implementation audit is in [IMPLEMENTATION_AUDIT.md](IMPLEMENTATION_AUDIT.md).

## Data

`data/synthetic_prompts.csv` is **synthetic** (every row has `data_source = SYNTHETIC`). It is generated from hand-written assumptions in `data/generate_synthetic.py`. To use real logs, save them as `data/historical_prompts.csv` with the same columns; `train()` prefers that file automatically.

## Pricing parser tests and optional live check

Fixture tests use saved representative official layouts and require no network or API keys:

```bash
python -m pytest cost_engine/tests -v
```

An optional live smoke test is skipped by default. Run with `COST_ENGINE_RUN_LIVE_PRICING=1 python -m pytest cost_engine/tests/test_live_pricing.py -v`. It fetches official pages but does not write the catalogue.

Unsupported formats include account-specific/private rates, third-party cloud marketplace prices, and model-independent tool charges. Context-specific and provider tier variants are retained in metadata; the legacy calculator currently applies base Standard rates (or published Batch rates when requested), not every Fast/Flex/Priority, cache storage, regional, or threshold modifier.

## Notes for integrators

- "estimated" always means output tokens were predicted; none of these values are provider invoices.
- If no trained predictor exists, `predict_output_tokens` falls back to `output = input` and says so in `source`.
- `data/artifacts/` (trained model, metrics) is generated; consider adding it to `.gitignore` and training in `scripts/setup.sh`.
- The six bundled illustrative model records remain unverified until a successful official refresh matches those identifiers.
- Install: `pip install -r cost_engine/requirements.txt`. Tests: `python -m pytest cost_engine/tests -v`.
