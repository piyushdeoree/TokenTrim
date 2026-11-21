# Cost Engine implementation audit

Audit scope: all Python modules, tests, fixtures, pricing data, predictor artifacts, and package documentation under `cost_engine/`. No changes were made outside that directory for this upgrade.

## Architecture and preserved interfaces

- `pricing.py` owns the JSON-backed catalogue, `Decimal` rates, version history, status/freshness, and the synchronized process-local registry. Provider-specific adapters and `pricing_engine.py` fetch official pricing, validate a complete provider snapshot, and update the registry all-or-nothing.
- `calculator.py` maintains the existing estimate/savings interfaces and provides actual-token `calculate_cost` plus per-row-isolated `calculate_cost_batch`. Amount arithmetic uses `Decimal`; float fields remain at the compatibility/API boundary.
- `prediction.py` retains its baseline, Random Forest, Gradient Boosting evaluation, selected estimator, and ratio fallback. The process reuses a validated artifact and now uses the selected model's held-out MAE for the reported range. `data/output_predictor_metadata.json` is kept outside the ignored generated-artifact directory so compatibility metadata ships with the source change.
- `forecasting.py`, `comparison.py`, `recommendation.py`, `analytics.py`, `currency.py`, and `nlp_adapter.py` retain their existing entry points while adding dated aggregation, daily/weekly/monthly projections, unavailable-price reporting, spend summaries, and guarded display conversion.
- Public compatibility exports remain available from `cost_engine`. Backend/NLP storage or routing changes remain outside this package and are listed in `INTEGRATION_REQUIREMENTS.md`.

## Findings from the audit

### Performance

- The registry was already cached in memory, so calculations did not read JSON repeatedly. It lacked provider indexing and complete synchronization; public records also exposed mutable nested data. A provider index and lock-protected detached public snapshots now protect consistency. Internal calculations use stable read-only registry snapshots.
- Comparison previously fetched each candidate through separate public and calculator paths. It now resolves one pricing snapshot per model and computes from it.
- There was no batch calculation interface. The new API validates records independently and reuses the price snapshot for each unique model/version. The current benchmark does **not** show it faster than the former repeated-single-call baseline; see the measured results and limitation in `PERFORMANCE_BENCHMARKS.md`.
- Prediction already cached the estimator, but did not synchronize concurrent loads, performed a metrics-file read for each prediction, and looked up held-out MAE at a path that the trainer did not emit. Model metrics now travel with the loaded artifact; compatibility metadata is checked before unpickling.
- Forecasting, analytics, and recommendation remain small in-memory operations. Their Python-level allocation latency is measured; no broad speed claim is made.

### Accuracy and reliability

- All catalogue money values and calculation intermediates are `Decimal`. Compatibility floats are checked for finite representability. Cache-write input tokens now use the write rate in place of standard input rate; cached and cache-write token counts cannot overlap or exceed input tokens.
- Batch, standard, and other named published tiers are selected only when complete rates exist. Unpublished combinations fail explicitly. Context-dependent variants that cannot be selected unambiguously remain visible as parser metadata.
- Public registry reads are detached. `reload_pricing()` atomically replaces the current cache after a valid disk parse; a failed reload leaves the old registry and history intact. Upserts update the provider index and refuse to replace newer verified prices with older verified snapshots.
- Existing official refresh behavior remains provider-isolated and fail-closed; failed source retrieval/parsing leaves the last valid provider data intact. Shipped catalogue values remain unverified examples.
- Training validates required feature columns, minimum row count, missing/non-finite/negative values, and integral output token counts. Training data is not created by the trainer. The repository has no `historical_prompts.csv`; the existing fallback dataset is labeled synthetic, and its metrics do not measure real-world quality.
- Artifact sidecar metadata stores the exact scikit-learn version and SHA-256. Runtime version/hash mismatches avoid pickle loading, produce a visible log message, and use the configured fallback. Legacy metadata-free artifacts are explicitly logged and may emit scikit-learn's warning during loading; warnings are not suppressed.
- Aggregation validates finite non-negative costs and fills absent periods with zero inside the observed date range. Forecast ranges are heuristic, not statistically calibrated confidence intervals. Currency conversion validates response/cache values, serializes refreshes, preserves a prior valid rate on failure, and reports refresh failure through logging.

## Baseline and current verification

The pre-change full suite passed **68 tests with 3 optional live tests skipped**. The baseline benchmark used the same script/methodology later added to `tests/benchmark_suite.py`; measured baseline and current results are recorded in `PERFORMANCE_BENCHMARKS.md`.

The persisted predictor metadata records scikit-learn 1.9.1. The ignored `backend/.venv` was created with Python 3.12 and the corrected requirements, including scikit-learn 1.9.1; the trained predictor loads and model-specific tests pass in that environment without `InconsistentVersionWarning`. The system-wide `python` remains Python 3.14.6 with scikit-learn 1.9.0; there the runtime validates metadata before unpickling, logs the version mismatch and safely uses the configured ratio fallback. Nine model-specific tests skip only when run under that mismatched system interpreter.

The final requested test command completed with **82 passed, 3 skipped** (the three optional live provider tests). `python -m cost_engine.tests.benchmark_suite` also completed; its measured baseline/current values and known regressions are in `PERFORMANCE_BENCHMARKS.md`. Current timings varied considerably between repeated runs on this shared Windows host.

## Explicit limitations

- No real historical usage dataset is present, so prediction accuracy cannot be validated against actual usage.
- `quality_tier` remains editable subjective metadata; it is not a model-evaluation score.
- Provider parser variants are retained when available, but context-threshold-specific pricing, all cache-write durations, regional modifiers, storage charges, and provider-specific combinations are not universally selectable through the common calculator.
- Forecasts need at least three periods and remain weak with short histories. The uncertainty range is an error-based heuristic.
- A local JSON registry is not a multi-process database. Backend integration requiring durable concurrent writes needs centralized storage and versioned schema/API support.
- Performance results are microbenchmarks under Python allocation tracing on one environment; they are not production throughput guarantees.
