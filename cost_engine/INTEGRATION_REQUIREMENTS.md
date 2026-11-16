# Integration requirements

This upgrade changes only `cost_engine/`. It does not modify backend/NLP routes, persistence models, migrations, deployment startup, or schedulers.

## Existing call compatibility

The backend can continue using `estimate_cost(model, input_tokens, predicted_output_tokens)`, `predict_output_tokens(...)`, `forecast_cost(...)`, `compare_models(input_tokens, predicted_output_tokens, ...)`, and existing recommendation/savings entry points. Existing fields are preserved; richer metadata is additive.

For bulk known usage, the optional batch interface is:

```python
from cost_engine import calculate_cost_batch

rows = calculate_cost_batch([
    {"id": "usage-123", "model": "gpt-4o", "input_tokens": 1000, "output_tokens": 200},
    {"id": "usage-124", "model": "gpt-4o", "input_tokens": 900, "output_tokens": 150,
     "cached_input_tokens": 200, "pricing_version": 2},
])
```

Each item reports `index`, optional `id`, `ok`, and either a flattened cost breakdown or structured `error`. Each record is validated independently.

## Pricing refresh and persistence

`refresh_pricing()` is intended for an administrative/background job, not an estimate request. The engine does not start a scheduler. It attempts providers independently, honors the configured 24-hour interval unless forced, and retains the last valid records on failure. Provider outcomes and last-attempt/success times are stored in `cost_engine/data/pricing_refresh_state.json`.

The package uses JSON files (`pricing.json`, `pricing_history.json`) as a single-process local registry. `reload_pricing()` explicitly reloads the in-memory cache; successful upserts update it and the provider index immediately. Concurrent in-process access is synchronized. Multiple backend workers/processes do not share one memory cache and do not have transactional cross-process updates. Production multi-worker deployments should move active prices/history/refresh leases to shared database storage and publish cache invalidation/version messages.

Pricing status, source, freshness, and version can be inspected through `get_pricing`, `pricing_freshness`, `get_pricing_history`, and `get_pricing_version`. Only official adapter extraction can set `official_verified`; matching a source URL is insufficient. Bundled placeholder prices remain unverified. Estimates using them should be labeled accordingly.

## Historical cost and usage schema

The current backend persistence may not store price source, freshness, pricing version, cache-read/write counts, batch status, or the estimated-vs-actual distinction. To reproduce historical calculations, persist at least:

- `pricing_version` plus model/provider and currency.
- Input/output, cached-input, and cache-write token counts.
- Batch mode or named provider pricing tier when applicable.
- Whether the amount is a provider-reported actual charge or a catalogue-based estimate.
- Source and verification snapshot when auditability is required.

Without a stored pricing version, later recalculation can silently use a newer catalogue price. Use `calculate_cost(..., pricing_version=...)` when a stored version is available.

## Prediction artifacts

`cost_engine/data/artifacts/output_predictor.joblib` is paired with `cost_engine/data/output_predictor_metadata.json`. Deploy both together. Metadata pins the artifact schema, training scikit-learn version, feature schema, training-data source, selected held-out metrics, and artifact hash. A mismatch is logged and falls back to the configured ratio. After replacing files in a long-running process, call `reload_prediction_model()`.

The current included dataset is synthetic. Supply actual, consented usage rows in `data/historical_prompts.csv` only when they match the documented feature schema. The engine does not make synthetic examples from backend requests. Synthetic-trained metrics must not be presented as actual accuracy.

## Forecast and currency calls

For `forecast_usage_costs`, pass actual dated cost records and choose `frequency="daily"`, `"weekly"`, or `"monthly"`; the function aggregates only supplied records and fills absent periods within the observed range as zero. Forecast ranges are heuristic error bands. Keep estimates separate from actual spend in backend persistence/reporting.

`convert_usd_to_inr` is optional display conversion, requires network access only when refreshing the exchange-rate snapshot, and never changes catalogue USD rates. A failed refresh uses a last valid cached rate marked stale or raises if none exists.

## NLP interface

`compare_prompt_cost(prompt, model, expected_output_tokens=...)` imports the existing `nlp_engine.analyze_prompt` interface and expects `original_tokens`, `optimized_tokens`, and `optimized_prompt`. The backend can call this from a service that already has NLP access. No NLP changes are required by the cost-engine implementation.
