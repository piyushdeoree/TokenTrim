# Cost Engine implementation audit

## Existing capabilities

- The package exports model pricing lookup, cost estimation, prompt-token savings, output-token prediction, model cost comparison, rule-based model recommendation, and future cost forecasting.
- `data/pricing.json` contains six OpenAI, Anthropic, and Google model records with input/output rates, context windows, and subjective quality tiers. Its own metadata says every price is illustrative and unverified.
- `prediction.py` supports linear regression, random forest, and gradient boosting; it compares candidates with cross-validation on the training partition and reports held-out MAE, RMSE, and R2. The included artifact/CSV are generated from synthetic assumptions, not observed provider usage.
- `forecasting.py` supports moving average, exponential smoothing, and linear regression with a tail holdout backtest. It accepts an ordered list of daily values but has no date aggregation or uncertainty intervals.
- Existing tests cover the compatibility API, simple cost arithmetic, prediction fallback, comparison, recommendations, and forecasting.
- NLP public interface: `nlp_engine.analyze_prompt(prompt, model)` returns a dict including `original_tokens`, `optimized_tokens`, and `optimized_prompt`. Backend cost service expects the legacy `estimate_cost(model, input_tokens, predicted_output_tokens)` interface; its stub-only parameters are `input_price_per_1k` and `output_price_per_1k`.

## Gaps and defects

- Prices are floats, carry no source/effective date/version/status, and are never refreshed. Registry validation only checks model name and negative rates, allows duplicates to overwrite, and has no durable history or stale state.
- The calculator uses binary floating point and supports only ordinary input/output charges. It has no cached-token accounting, cache-write, batch, multi-currency, or explainable rate metadata. The backend stub price arguments are ignored by the real engine.
- Prompt savings accepts only token counts and computes input savings; there is no NLP adapter, full before/after estimate, or same-output comparison object.
- Output prediction rounds one point estimate, does not validate finite/integer inputs consistently, and has no prediction interval. A model artifact may have been trained on synthetic data.
- Comparison assumes all named models have valid pricing, has no provider filters, cached scenario, or context-window filtering. Recommendation includes hand-set quality tiers that are not validated quality measurements.
- Forecasting has no date aggregation, grouping, monthly estimate, or uncertainty range. It correctly rejects insufficient history rather than fabricating records.
- There is no currency conversion, pricing refresh scheduler, source-specific official page parser, or cost optimization analytics.
- The only test file covers core legacy behavior; there are no network-mocked source parser/history/integration tests.

## Dependencies

`requirements.txt` lists NumPy, pandas, scikit-learn, joblib, and pytest. Pricing refresh and currency support should use the Python standard library where possible; no HTTP client is currently declared. Tests are run through pytest.

## Integration requirements

- Keep `estimate_cost`, `predict_output_tokens`, `forecast_cost`, and other existing package exports intact. Add richer opt-in APIs.
- Backend integration can call the prompt comparison API with the NLP result, comparison API with model list and context, and refresh operation from an administrative job. Existing DB models persist usage and costs but have no pricing version history or source metadata.
- A backend that wants durable pricing versions needs schema/storage operations and an administrative refresh endpoint; details are in `INTEGRATION_REQUIREMENTS.md`.

## Proposed architecture

Preserve the current compact modules and legacy API. Extend shared dataclasses and the registry, keep Decimal-based calculations in the calculator, and add focused pricing retrieval/history, NLP adapter, currency, and analytics modules. Official source pages are treated as unverified until a source-specific parser extracts complete, validated model rows. Preserve last known valid records on any failure. Never promote the existing illustrative data to verified.

## Implementation sequence

1. Mark existing catalogue status accurately and add validated metadata/history primitives and official-source refresh adapters.
2. Implement Decimal cost breakdowns and preserve legacy dict/float response shapes.
3. Add NLP prompt cost comparison and output prediction intervals/fallback metadata.
4. Add context-aware cost comparison and structured savings analytics.
5. Add daily/monthly aggregation and forecast uncertainty; add optional cached exchange rates.
6. Add mocked tests and document the implemented limits and integration contract.

## Official pricing refresh follow-up status

- Separate OpenAI, Anthropic, and Google adapters now parse their official pricing representations. OpenAI Markdown includes Standard/Batch/Flex/Fast/Ultrafast and context/cache variants; Anthropic Markdown includes standard/cache/batch/fast and model availability/threshold conditions; Gemini parses per-model Standard/Batch/Flex/Priority tabs, HTML tables, and effective-date changes.
- Monetary rates are `Decimal` in memory and JSON decimal strings. `get_pricing()` retains its legacy float view, while internal calculator paths and registry persistence use Decimal.
- Refresh validates a complete provider response before atomic batch upsert, runs providers independently, observes the 24-hour interval unless forced, reports provider outcomes, and keeps previous records after a failed fetch/parse. Manual data cannot be marked verified.
- Catalogue records are in `data/pricing.json`; the one version history is `data/pricing_history.json`; refresh state is `data/pricing_refresh_state.json`. History versions are recorded only for rate/tier/condition changes and may be selected explicitly for historical calculations.
- Fixture tests cover provider parsing, invalid formats, refresh failures, independent provider success, unchanged/changed version behavior, and stale detection. Live smoke tests are isolated and skipped by default.
- Limits: the legacy calculator does not yet apply all provider-specific context/Fast/Flex/Priority/regional/cache-storage modifiers automatically. Prices with no source-published effective date retain it as unknown. Freshness is computed dynamically, not persisted.
