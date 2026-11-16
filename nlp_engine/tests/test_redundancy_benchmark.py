"""Regression tests for the curated redundancy evaluation dataset."""

import json

import pytest

from nlp_engine.tests.benchmark_runner import DATASET_PATH, evaluate_case


with DATASET_PATH.open(encoding="utf-8") as dataset_file:
    BENCHMARK_CASES = json.load(dataset_file)


@pytest.mark.parametrize("case", BENCHMARK_CASES, ids=lambda case: case["id"])
def test_redundancy_benchmark_case(case, monkeypatch):
    """Keep expected duplicate, similarity, and preservation behavior covered."""
    # Exercise the default CPU lexical path without loading an optional model.
    monkeypatch.setattr(
        "nlp_engine.redundancy.semantic_similarity_matrix",
        lambda _texts: None,
    )

    result = evaluate_case(case)

    assert result["passed"], (
        f"{case['id']}: expected {case['expected']}, got {result['actual']} "
        f"(removals={result['removal_count']}, "
        f"pairs={result['pair_details']})"
    )

    if case["expected"] == "preserve_both":
        assert result["removal_count"] == 0
