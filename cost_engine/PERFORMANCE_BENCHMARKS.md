# Cost Engine performance benchmarks

## Method

Run from repository root with the project environment:

```powershell
. .\.fenv\Scripts\Activate.ps1
python -m cost_engine.tests.benchmark_suite
```

The suite uses `time.perf_counter_ns`, a warm-up, fixed in-process inputs, and Python `tracemalloc` peak allocation measurement. It measures pricing lookup, one calculation, 100-record calculation, prediction, comparison, 90-point forecast, and 100-record analytics. No network requests run. Fixed synthetic values exist only to make benchmark calls repeatable; they are not model training or forecasting history. Latencies include allocation tracing and should only be compared under the same interpreter, environment, machine load, and methodology. Memory is Python allocation peak, not total process RSS.

The baseline was measured before this upgrade with the same benchmark module. The batch baseline is repeated single-row calculations because no batch API existed then. Current benchmark is after the upgrade. Latency is the mean per measured call; batch latency is per 100-record batch. p99 is omitted for fewer than 100 samples. Windows host load varied substantially between current runs; values below are the final run and should not be treated as stable production estimates.

## Baseline and current measurements

| Operation | Samples | Baseline mean | Current mean | Baseline p50 / p95 / p99 | Current p50 / p95 / p99 | Current peak traced memory |
|---|---:|---:|---:|---:|---:|---:|
| Pricing lookup | 200 | 12.47 µs | 14.36 µs | 11.90 / 12.50 / 19.70 µs | 13.60 / 16.80 / 21.00 µs | 9,492 B |
| Single cost calculation | 200 | 53.09 µs | 77.47 µs | 50.70 / 58.20 / 114.20 µs | 72.50 / 94.40 / 174.70 µs | 9,111 B |
| Batch of 100 costs | 40 | 17.472 ms | 23.237 ms | 17.105 / 21.985 / n/a ms | 21.961 / 35.624 / n/a ms | 124,636 B |
| Output prediction | 50 | 135.679 ms | 121.678 ms | 128.858 / 168.657 / n/a ms | 119.748 / 143.335 / n/a ms | 412,451 B |
| Model comparison | 50 | 1.915 ms | 1.540 ms | 1.839 / 3.427 / n/a ms | 1.268 / 3.098 / n/a ms | 6,356 B |
| Forecast, 90 points | 50 | 1.923 ms | 2.033 ms | 1.772 / 2.946 / n/a ms | 1.820 / 2.959 / n/a ms | 18,780 B |
| Analytics, 100 records | 50 | 1.502 ms | 2.591 ms | 1.608 / 2.150 / n/a ms | 2.459 / 3.711 / n/a ms | 3,260 B |

Current batch throughput was **4,303 records/second** (mean of 100-record batches); the repeated-single baseline was **5,723 records/second**. The native batch function improves lookup reuse and failure isolation, but this run was slower. Do not claim it is faster.

## Interpretation

- Prediction and comparison means were lower in this run; comparison uses one registry snapshot per model, and prediction avoids per-call metrics reads. This does not establish a stable speed gain.
- Pricing lookup, single calculation, batch, forecasting, and analytics were slower in this run. The cost path retains Decimal validation, safe snapshots, and added reporting; no broad speed gain is claimed.
- Current runs showed substantial timing spread on this shared Windows host. Rerun several times on a controlled machine before using these numbers for capacity planning or claiming an optimization.
- The work improves correctness and failure isolation even where timing did not improve. Further optimization should profile production-representative traffic without tracing, retain Decimal arithmetic, and compare repeated warmed runs before making performance claims.
- Provider pricing refresh and currency refresh are network-bound and intentionally excluded from these local benchmarks.
