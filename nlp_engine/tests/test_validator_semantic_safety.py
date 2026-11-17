
"""Regression tests for safety when validating semantic rewrite candidates."""

import pytest

from nlp_engine.validator import validate_optimization


@pytest.mark.parametrize(
    ("original", "optimized", "risk"),
    [
        (
            "Do not store user passwords; use bcrypt.",
            "Store user passwords; use bcrypt.",
            "negation",
        ),
        (
            "Return exactly 5 examples.",
            "Return exactly 3 examples.",
            "numeric constraint",
        ),
        (
            "Use HTTPStatus and preserve client_id.",
            "Use status and preserve the client id.",
            "identifiers",
        ),
        (
            "Use this exact code: `result = calculate_total(items)`",
            "Use this exact code: `result = calculate_sum(items)`",
            "protected code",
        ),
        (
            "Keep response time below 500 milliseconds.",
            "Keep response time above 500 milliseconds.",
            "comparison direction",
        ),
        (
            "Return only the top 3 results.",
            "Return all 3 results.",
            "scope",
        ),
        (
            "Include all records except deleted records.",
            "Include all records, including deleted records.",
            "exception",
        ),
        (
            "Validate the input before generating the report.",
            "Generate the report before validating the input.",
            "sequence",
        ),
    ],
)
def test_validator_rejects_candidates_that_change_important_information(
    original,
    optimized,
    risk,
):
    result = validate_optimization(original, optimized)

    assert not result.is_valid, (
        f"Validator accepted a candidate that changed {risk}: "
        f"{optimized!r}"
    )


def test_validator_rejects_reversed_sequence_without_ordering_marker():
    original = (
        "Validate the input before generating the report."
    )
    optimized = (
        "Generate the report. Validate the input."
    )

    result = validate_optimization(original, optimized)

    assert not result.is_valid


def test_validator_rejects_reordered_multi_step_workflow():
    original = (
        "First clean the data. "
        "Then train the model. "
        "Finally evaluate it."
    )
    optimized = (
        "First evaluate the model. "
        "Then train it. "
        "Finally clean the data."
    )

    result = validate_optimization(original, optimized)

    assert not result.is_valid


def test_validator_rejects_removing_a_required_condition():
    original = "Only deploy if all tests pass."
    optimized = "Deploy after the tests run."

    result = validate_optimization(original, optimized)

    assert not result.is_valid


def test_validator_accepts_an_unchanged_prompt():
    prompt = (
        "Explain database indexing. "
        "Include one practical example."
    )

    result = validate_optimization(prompt, prompt)

    assert result.is_valid
