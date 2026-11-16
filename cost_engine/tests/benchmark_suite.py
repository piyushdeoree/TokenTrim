"""Repeatable local microbenchmarks for cost-engine hot paths.

Run from the repository root with ``python -m cost_engine.tests.benchmark_suite``.
The workload is deterministic and synthetic; it is for timing only and is never
used for prediction training or forecasting.
"""
from __future__ import annotations

import json
import statistics
import time
import tracemalloc
from itertools import count

from cost_engine.analytics import analyze_savings
from cost_engine.calculator import calculate_cost
from cost_engine.comparison import compare_models
from cost_engine.forecasting import forecast_cost
from cost_engine.prediction import predict_output_tokens
from cost_engine.pricing import get_pricing


def _summary(samples_ns: list[int], *, calls_per_sample: int = 1) -> dict:
    ordered = sorted(samples_ns)

    def percentile(p: float) -> float:
        return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p))] / calls_per_sample / 1_000

    mean_us = statistics.fmean(samples_ns) / calls_per_sample / 1_000
    return {
        "sample_count": len(samples_ns),
        "mean_us_per_call": round(mean_us, 2),
        "p50_us": round(percentile(0.50), 2),
        "p95_us": round(percentile(0.95), 2),
        "p99_us": round(percentile(0.99), 2) if len(samples_ns) >= 100 else None,
    }


def _measure(fn, *, warmups: int = 20, repetitions: int = 200) -> tuple[dict, int]:
    for _ in range(warmups):
        fn()
    samples = []
    tracemalloc.start()
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        fn()
        samples.append(time.perf_counter_ns() - start)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result = _summary(samples)
    result["peak_tracemalloc_bytes"] = peak
    return result, repetitions


def run_benchmarks() -> dict:
    pricing_lookup, _ = _measure(lambda: get_pricing("gpt-4o"))
    single_cost, _ = _measure(lambda: calculate_cost("gpt-4o", 2_000, 800))

    records = [{"model": "gpt-4o", "input_tokens": 2_000, "output_tokens": 800} for _ in range(100)]
    batch_fn = getattr(__import__("cost_engine.calculator", fromlist=["calculate_cost_batch"]), "calculate_cost_batch", None)
    if batch_fn:
        batch_call = lambda: batch_fn(records)
        batch_implementation = "native_batch"
    else:
        batch_call = lambda: [calculate_cost(r["model"], r["input_tokens"], r["output_tokens"]) for r in records]
        batch_implementation = "repeated_single_calls_baseline"
    batch_cost, _ = _measure(batch_call, warmups=5, repetitions=40)
    batch_cost["records_per_second"] = round(100_000_000 / batch_cost["mean_us_per_call"], 2)
    batch_cost["records_per_batch"] = len(records)
    batch_cost["implementation"] = batch_implementation

    prediction, _ = _measure(lambda: predict_output_tokens(1_200, task_type="summarization", model="gpt-4o"), warmups=5, repetitions=50)
    unique_tokens = count(10_000)
    prediction_cache_miss, _ = _measure(
        lambda: predict_output_tokens(next(unique_tokens), task_type="summarization", model="gpt-4o"),
        warmups=5, repetitions=50,
    )
    comparison, _ = _measure(lambda: compare_models(2_000, 800), warmups=5, repetitions=50)
    history = [float(10 + (i % 7) * 0.25) for i in range(90)]
    forecasting, _ = _measure(lambda: forecast_cost(history, "30_days"), warmups=5, repetitions=50)
    analytics_records = [{"model": "gpt-4o", "provider": "openai", "cost": "0.002", "input_tokens": 2_000, "output_tokens": 800} for _ in range(100)]
    analytics, _ = _measure(lambda: analyze_savings(analytics_records), warmups=5, repetitions=50)

    return {
        "methodology": {
            "clock": "time.perf_counter_ns",
            "warmup": "20 calls for direct operations; 5 for higher-level operations",
            "workload": "deterministic in-process calls, fixed at 100 batch/analytics records and 90 forecast points",
            "memory": "tracemalloc peak for measured Python allocations (not total process RSS)",
        },
        "pricing_lookup": pricing_lookup,
        "single_cost_calculation": single_cost,
        "batch_100_cost_calculation": batch_cost,
        "output_prediction": prediction,
        "output_prediction_unique_input_cache_miss": prediction_cache_miss,
        "model_comparison": comparison,
        "forecasting": forecasting,
        "analytics_100_records": analytics,
    }


if __name__ == "__main__":
    print(json.dumps(run_benchmarks(), indent=2))
