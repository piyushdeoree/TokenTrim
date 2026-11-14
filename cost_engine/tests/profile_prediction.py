"""Profile one-row prediction stages with the canonical benchmark input.

Run with ``python -m cost_engine.tests.profile_prediction``. This script is
diagnostic only; it does not change the model or training data.
"""
from __future__ import annotations

import cProfile
import io
import pstats
import statistics
import time
import tracemalloc

import numpy as np
from cost_engine import prediction

INPUTS = (1_200,)
OPTIONS = {"task_type": "summarization", "model": "gpt-4o"}


def _measure(function, *, warmups=5, repetitions=50):
    for _ in range(warmups):
        function()
    samples = []
    tracemalloc.start()
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        function()
        samples.append(time.perf_counter_ns() - start)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    ordered = sorted(samples)
    return {
        "mean_us": round(statistics.fmean(samples) / 1_000, 2),
        "p50_us": round(ordered[int((len(ordered) - 1) * .50)] / 1_000, 2),
        "p95_us": round(ordered[int((len(ordered) - 1) * .95)] / 1_000, 2),
        "peak_tracemalloc_bytes": peak,
    }


def run_profile():
    prediction.reload_prediction_model()
    artifact = prediction._load()
    row = prediction.build_feature_row(INPUTS[0], **OPTIONS)
    pipeline = artifact["pipeline"]
    preprocessor = pipeline.named_steps["pre"]
    estimator = pipeline.named_steps["est"]
    transformed = preprocessor.transform(row)

    def direct_dense_input(feature_row):
        encoder = preprocessor.named_transformers_["cat"]
        categories = encoder.categories_
        values = [feature_row.iloc[0][name] for name in prediction.CATEGORICAL_FEATURES]
        numeric = [feature_row.iloc[0][name] for name in prediction.NUMERIC_FEATURES]
        vector = np.zeros((1, sum(len(items) for items in categories) + len(numeric)), dtype=encoder.dtype)
        offset = 0
        for value, learned_values in zip(values, categories):
            index = int(np.searchsorted(learned_values, value))
            if index < len(learned_values) and learned_values[index] == value:
                vector[0, offset + index] = 1
            offset += len(learned_values)
        vector[0, offset:] = numeric
        return vector

    dense_row = direct_dense_input(row)
    estimator = pipeline.named_steps["est"]
    original_n_jobs = getattr(estimator, "n_jobs", None)
    if original_n_jobs is not None: estimator.n_jobs = 1
    pipeline_prediction = pipeline.predict(row)
    direct_prediction = estimator.predict(dense_row)
    if original_n_jobs is not None: estimator.n_jobs = original_n_jobs
    if not np.array_equal(pipeline_prediction, direct_prediction):
        raise AssertionError(f"direct numeric input changed prediction: {pipeline_prediction} != {direct_prediction}")
    stages = {
        "cached_model_load": prediction._load,
        "feature_row_construction": lambda: prediction.build_feature_row(INPUTS[0], **OPTIONS),
        "preprocessing_transform": lambda: preprocessor.transform(row),
        "direct_dense_feature_encoding": lambda: direct_dense_input(row),
        "forest_inference_pretransformed": lambda: estimator.predict(transformed),
        "forest_inference_direct_dense": lambda: estimator.predict(dense_row),
        "pipeline_inference": lambda: pipeline.predict(row),
        "complete_prediction": lambda: prediction.predict_output_tokens(*INPUTS, **OPTIONS),
    }
    results = {name: _measure(function) for name, function in stages.items()}
    estimator = pipeline.named_steps["est"]
    original_n_jobs = getattr(estimator, "n_jobs", None)
    if original_n_jobs is not None:
        results["forest_parallelism_comparison"] = {}
        try:
            for n_jobs in (-1, 1):
                estimator.n_jobs = n_jobs
                results["forest_parallelism_comparison"][str(n_jobs)] = _measure(lambda: pipeline.predict(row))
        finally:
            estimator.n_jobs = original_n_jobs

    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(10):
        prediction.predict_output_tokens(*INPUTS, **OPTIONS)
    profiler.disable()
    output = io.StringIO()
    pstats.Stats(profiler, stream=output).strip_dirs().sort_stats("cumtime").print_stats(25)
    return results, output.getvalue()


if __name__ == "__main__":
    import json
    measures, profile = run_profile()
    print(json.dumps(measures, indent=2))
    print(profile)
