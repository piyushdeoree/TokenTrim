"""Exercise redundancy examples through the public analysis pipeline."""

import json

import pytest

from nlp_engine.analyzer import analyze_prompt_detailed
from nlp_engine.tests.benchmark_runner import DATASET_PATH

REALISTIC_DATASET_PATH = DATASET_PATH.with_name("realistic_evaluation_dataset.json")

with DATASET_PATH.open(encoding="utf-8") as dataset_file:
    BENCHMARK_CASES = json.load(dataset_file)

with REALISTIC_DATASET_PATH.open(encoding="utf-8") as dataset_file:
    REALISTIC_CASES = json.load(dataset_file)


def _analyze_without_semantic_model(prompt, monkeypatch):
    monkeypatch.setattr(
        "nlp_engine.redundancy.semantic_similarity_matrix",
        lambda _texts: None,
    )
    return analyze_prompt_detailed(prompt, model="unknown-test-model")

@pytest.mark.parametrize("case", BENCHMARK_CASES, ids=lambda case: case["id"])
def test_full_pipeline_matches_redundancy_expectation(case, monkeypatch):
    """Ensure segmentation, detection, optimization, and validation agree."""
    result = _analyze_without_semantic_model(case["text"], monkeypatch)

    assert result.validation.is_valid

    if case["expected"] == "duplicate_detected":
        assert result.optimization_accepted, (
            f"{case['id']}: expected a safe duplicate removal; "
            f"candidate={result.candidate.optimized_prompt!r}, "
            f"issues={[issue.type for issue in result.issues]}"
        )
        assert result.final.tokens_saved > 0

    elif case["expected"] == "similarity_detected":
        assert any(issue.type == "redundancy" for issue in result.issues), (
            f"{case['id']}: expected a similarity advisory"
        )
        assert not result.optimization_accepted
        assert result.final.optimized_prompt == case["text"]

    elif case["expected"] == "preserve_both":
        assert not result.optimization_accepted
        assert result.final.optimized_prompt == case["text"]

    else:
        pytest.fail(f"Unsupported expectation: {case['expected']!r}")


def test_technical_02_removes_only_the_second_emit_directive(monkeypatch):
    case = next(case for case in REALISTIC_CASES if case["id"] == "technical_02")
    result = _analyze_without_semantic_model(case["prompt"], monkeypatch)
    optimized = result.final.optimized_prompt

    assert result.optimization_accepted
    assert result.validation.is_valid
    assert result.final.tokens_saved > 0
    assert optimized.count("Emit one UTF-8 JSON object per line.") == 1
    assert "Output contract: Emit one UTF-8 JSON object per line." in optimized
    assert "Schema requirements:" in optimized
    assert "`record_id`, `observed_at`, and `value`" in optimized
    assert "RFC 3339 UTC form" in optimized
    assert "Do not emit a header row." in optimized
    assert "- Emit one UTF-8 JSON object per line." not in optimized


@pytest.mark.parametrize(
    "prompt",
    [
        (
            "Emit one JSON object per account for ingestion. "
            "Emit a CSV summary for the audit team."
        ),
        (
            "Emit a JSON result only when validation succeeds. "
            "Emit a plain-text error only when validation fails."
        ),
        "Emit the successful result as JSON. Emit the audit log as CSV.",
    ],
    ids=["distinct-emissions", "conditional-emissions", "different-formats"],
)
def test_distinct_or_conditional_emit_instructions_are_preserved(prompt, monkeypatch):
    result = _analyze_without_semantic_model(prompt, monkeypatch)

    assert not result.optimization_accepted
    assert result.final.optimized_prompt == prompt
