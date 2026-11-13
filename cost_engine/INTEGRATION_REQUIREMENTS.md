# Backend integration requirements

The engine remains independently callable; no backend or migration changes are included.

## Available calls

```python
from cost_engine import (
    compare_prompt_cost, compare_models, forecast_cost, refresh_pricing,
    refresh_openai_pricing, refresh_anthropic_pricing, refresh_google_pricing,
    get_pricing_history, get_pricing_version,
    predict_output_tokens, estimate_cost,
)

prediction = predict_output_tokens(input_tokens, model=model, prompt_text=prompt)
estimate = estimate_cost(model, input_tokens, prediction["predicted_output_tokens"])
prompt_comparison = compare_prompt_cost(prompt, model,
    expected_output_tokens=prediction["predicted_output_tokens"])
alternatives = compare_models(input_tokens, expected_output_tokens, provider=None)
```

`refresh_pricing()` is intended for an administrative/background operation, not a request path. It refreshes providers due by `COST_ENGINE_REFRESH_INTERVAL_HOURS` (default 24); pass `force=True` to attempt all sources immediately. Provider-specific refresh functions always attempt that source. The result reports each provider independently. Prices live in `data/pricing.json`, history in `data/pricing_history.json`, and refresh reports in `data/pricing_refresh_state.json`. Use `get_pricing_history()` and `get_pricing_version()` to inspect/use historical prices. Manual records remain unverified; a source URL cannot promote them.

## Existing persistence and API work needed

- The current backend `models` and `model_pricing` tables can supply its current model/rates, and `usage_records`/`cost_records` preserve estimated usage, but they do not persist provider pricing source, effective date, version history, cached token counts, cache-write/batch detail, or exchange-rate snapshots.
- Add a pricing-version table (model/provider, all rate fields, currency, tier, context, effective date, source URL, verification status/time, version, changed fields) and an active-version reference. Preserve prior versions rather than overwriting them.
- Add usage attributes for cached input and cache-write tokens, batch mode, pricing version, and estimate status if those billing dimensions are needed.
- Add authenticated administrative refresh and catalogue-read endpoints. A normal estimate endpoint should pass prompt text/model/token assumptions to the engine and return the serialized breakdown plus pricing freshness/status; do not fetch pricing synchronously on every estimate.
- The existing service passes `input_price_per_1k` and `output_price_per_1k` only when using stubs. The real engine call currently ignores those arguments. For the live engine, resolve rates by model from its catalogue or change the service to pass a validated pricing object in a later backend-only integration task.
- Forecast endpoints should pass ordered dated actual usage records and retain the engine's assumptions and forecast interval. Do not mix estimated forecasts with actual historical sums.
- `compare_prompt_cost` imports only the existing public `nlp_engine.analyze_prompt` function and expects `original_tokens`, `optimized_tokens`, and `optimized_prompt` in its dict.
- Source adapters are in `cost_engine/pricing_adapters/`. They fetch only the registered OpenAI, Anthropic, and Google official sources, then validate complete provider snapshots before updating the catalogue.

No backend files, models, routes, or migrations were modified in this work.
