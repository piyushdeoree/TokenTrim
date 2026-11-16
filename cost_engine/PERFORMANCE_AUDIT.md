# Performance and accuracy audit

## Scope and existing architecture

The engine is a Python package backed by JSON files. `pricing.py` loads and validates model records, then keeps them in an in-memory registry. Provider adapters fetch registered official pages and parse provider-specific formats; the refresh engine validates complete provider snapshots before updating catalogue and history. `calculator.py` performs per-token cost arithmetic, `prediction.py` loads a persisted sklearn pipeline, `comparison.py` and `recommendation.py` rank current catalogue entries, and `forecasting.py` performs small NumPy projections from supplied history. Analytics, display currency conversion, and the optional NLP adapter are separate modules.

Existing capabilities preserved include the estimate/savings API, a trained-model prediction path and ratio fallback, three candidate regressors with a mean baseline, auto-selected forecasting and holdout backtesting, provider-specific official refresh, pricing versions/history/freshness, model recommendation, and NLP prompt comparison. Official pricing refresh is opt-in and does not run in the ordinary calculation path.

## Findings before this upgrade

1. The registry already cached JSON reads, but lookup still scanned for provider filters, state access was not fully synchronized, and public values exposed mutable nested dictionaries/lists.
2. Comparison performed duplicate lookups and cost setup for each model. There was no batch cost API.
3. The model pipeline was cached, but concurrent first loads could deserialize more than once, every prediction attempted to read metrics JSON, and metric extraction used a path the trainer did not write.
4. Persisted estimator objects did not record the training scikit-learn version or an artifact checksum. A version mismatch could trigger `InconsistentVersionWarning` during unpickle.
5. Training did not reject short/incomplete/non-finite data. The repository has no real historical dataset; the present 5,000-row dataset is labeled synthetic.
6. Cache-write tokens were charged in addition to the ordinary input rate for the same tokens. Tier fields were stored but not consistently selected or rejected by calculation.
7. Forecasting accepted ordered values but did not provide dated daily/weekly/monthly usage aggregation or fill missing dates. Analytics summarized spend but did not flag an observed daily increase.
8. Currency conversion swallowed refresh exceptions without reporting them, and cached values were not comprehensively validated.

## Changes made

- Added provider-to-model indexing, synchronized reload/upsert/get paths, detached public pricing objects, explicit cache diagnostics, rollback on failed persistence, and a guard against late older verified snapshots replacing newer verified data.
- Added `calculate_cost_batch` with per-record success/error results and one pricing snapshot per unique model/version. Comparison and recommendation now reuse an internal pricing snapshot rather than performing duplicate public lookup/conversion. The final traced microbenchmark did not show a batch speed gain; performance figures varied widely between runs.
- Kept Decimal calculations through cost arithmetic, validated finite float response conversion, prevented cached/write token overlap, and applied cache-write rates instead of charging those tokens twice at the standard input rate.
- Applied requested published tiers only when the record exposes complete applicable values. Unsupported tier/cache combinations produce an unavailable/error response.
- Added prediction input validation, model-load locking/caching, artifact schema and exact sklearn version metadata, SHA-256 preflight, explicit error logging/fallback, and selected held-out metrics embedded with the model. The sidecar and artifact are both required for preflight verification.
- Added dated aggregation with gap filling, grouped projections for daily/weekly/monthly records, additional analytics input validation and daily increase flags, and guarded currency-rate refresh/cache handling.
- Added repeatable local benchmarks and fixture-free unit tests for the new reliability paths.

## Accuracy and reliability limits

- The packaged price catalogue has illustrative unverified rates until a successful official refresh confirms model identifiers and rates.
- The synthetic dataset was already present and was used to refresh the artifact for sklearn 1.9.1 compatibility. Its held-out metrics compare model candidates against that synthetic generator only; they are not evidence of production accuracy.
- Three historical points are only a minimum to produce a forecast. Ranges are heuristic holdout-error/history-spread bands, not calibrated confidence intervals.
- Parser metadata retains a number of provider-specific variants, but the shared calculator does not automatically select context thresholds, every cache-write duration, regional uplift, storage charge, or all combinations. Unsupported choices fail closed.
- Unusual cost increases are threshold signals with no causal explanation. Potential savings are left null without a priced counterfactual.
- The local JSON registry synchronizes threads in one process. Multi-process backend workers need shared storage/locking and cache invalidation integration.
- Microbenchmarks are local, Python-allocation-traced results; they do not model production concurrency, network calls, or database costs. See `PERFORMANCE_BENCHMARKS.md` for the measured baseline and current numbers, including paths that did not improve.
