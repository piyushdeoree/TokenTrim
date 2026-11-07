# cost_engine

Cost Intelligence module (Person 2) for the *AI Cost Intelligence and Prompt Optimization Platform for LLMs*.

Pipeline: `token data → output prediction → cost calculation → forecasting → model comparison → model recommendation`

## Quick start

```bash
pip install -r cost_engine/requirements.txt
python -m cost_engine.data.generate_synthetic --rows 5000   # SYNTHETIC data, dev only
python -m cost_engine.prediction                            # trains + writes metrics
pytest cost_engine/tests -v
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

Prices live only in `data/pricing.json` (per 1M tokens). **The shipped values are illustrative placeholders. Verify them against each provider's pricing page and update `_meta.last_verified` before reporting real costs.** Update at runtime with `upsert_pricing(ModelPricing(...))` or edit the JSON and call `reload_pricing()`.

## Data

`data/synthetic_prompts.csv` is **synthetic** (every row has `data_source = SYNTHETIC`). It is generated from hand-written assumptions in `data/generate_synthetic.py`. To use real logs, save them as `data/historical_prompts.csv` with the same columns; `train()` prefers that file automatically.

## Notes for integrators

- "estimated" always means output tokens were predicted; none of these values are provider invoices.
- If no trained predictor exists, `predict_output_tokens` falls back to `output = input` and says so in `source`.
- `data/artifacts/` (trained model, metrics) is generated; consider adding it to `.gitignore` and training in `scripts/setup.sh`.
