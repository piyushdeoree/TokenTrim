"""Behavior checks for request-local validation work reuse."""

from nlp_engine.textutils import content_stems, is_negated, prepare_prompt
from nlp_engine.validator import (
    _best_constraint_coverage,
    _constraint_coverage_scores,
    _entities,
    _entities_from_segments,
)


def test_entity_extraction_from_prepared_segments_matches_text_path():
    prompts = [
        "Use `source_timestamp` with ApiClient and HTTP.",
        "## Output\nReturn JSON with customerId and AWS S3.",
        "Keep https://example.com/v1 and `/var/data/input.csv` unchanged.",
        "Ordinary words only.",
    ]

    for prompt in prompts:
        prepared = prepare_prompt(prompt.strip())
        assert _entities_from_segments(prepared.segments) == _entities(prompt)


def test_batched_constraint_scores_match_original_per_constraint_calculation():
    original_constraints = [
        "Do not delete archived records.",
        "Only retry a request when status is 503.",
        "Preserve the original account identifier.",
        "Never expose the API key.",
    ]
    candidate_segments = [
        "Delete archived records after review.",
        "Do not delete archived records without approval.",
        "Retry only when status is 503.",
        "Preserve the original account identifier and API key.",
        "Never expose the API key in logs.",
        "---",
    ]
    constraint_data = [
        (
            {stem for stem in content_stems(text) if not stem.startswith("qzph")},
            is_negated(text),
        )
        for text in original_constraints
    ]

    actual = _constraint_coverage_scores(constraint_data, candidate_segments)
    expected = [
        _best_constraint_coverage(text, candidate_segments)
        for text in original_constraints
    ]

    assert actual == expected


def test_constraint_scores_are_isolated_between_validation_inputs():
    first_constraints = [({"account", "identifier"}, False)]
    second_constraints = [({"payment", "amount"}, True)]

    first = _constraint_coverage_scores(
        first_constraints,
        ["Preserve the account identifier."],
    )
    second = _constraint_coverage_scores(
        second_constraints,
        ["Do not change the payment amount."],
    )
    repeated_first = _constraint_coverage_scores(
        first_constraints,
        ["Preserve the account identifier."],
    )

    assert first == repeated_first
    assert second != first
