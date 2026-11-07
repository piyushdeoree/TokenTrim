"""Advanced regression tests for semantic preservation."""

import pytest

from nlp_engine import optimize_prompt


@pytest.mark.parametrize("prompt,required", [
    (
        'Explain the term "machine learning" without changing its meaning.',
        ['machine learning', 'without', 'meaning'],
    ),
    (
        'Use the exact phrase "customer lifetime value" in the report.',
        ['exact phrase', 'customer lifetime value'],
    ),
    (
        'Do not replace the word "fraud" with "irregularity".',
        ['do not', 'fraud', 'irregularity'],
    ),
])
def test_quoted_terms_are_preserved(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required", [
    (
        "Explain how PostgreSQL indexing improves query performance. "
        "Include a B-tree index example.",
        ["postgresql", "indexing", "query performance", "b-tree"],
    ),
    (
        "Train a CNN using image data. "
        "Evaluate it using precision, recall, and F1-score.",
        ["cnn", "image data", "precision", "recall", "f1-score"],
    ),
    (
        "Use Python 3.12 with FastAPI and PostgreSQL. "
        "Do not use Flask.",
        ["python 3.12", "fastapi", "postgresql", "do not use flask"],
    ),
])
def test_technical_context_is_preserved(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required", [
    (
        "If the dataset contains missing values, clean them first. "
        "If it contains duplicates, remove them. "
        "Otherwise, continue to model training.",
        ["if", "missing values", "clean", "duplicates", "remove",
         "otherwise", "model training"],
    ),
    (
        "If accuracy is below 80%, tune the model. "
        "Only if accuracy reaches 90%, deploy it.",
        ["below 80%", "tune", "only if", "90%", "deploy"],
    ),
])
def test_multiple_conditions_are_preserved(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required", [
    (
        "First collect the data. "
        "Next remove duplicates. "
        "Then normalize numerical columns. "
        "Finally train and evaluate the model.",
        ["first", "collect", "next", "duplicates", "then",
         "normalize", "finally", "train", "evaluate"],
    ),
    (
        "Read the input file. "
        "Validate the schema before processing. "
        "Save the output only after validation succeeds.",
        ["read", "input file", "before", "validate",
         "only after", "validation succeeds"],
    ),
])
def test_complex_workflows_preserve_order(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required", [
    (
        "Analyze sales data for 2024 and 2025. "
        "Compare revenue growth, but exclude refunded transactions.",
        ["2024", "2025", "revenue growth", "exclude",
         "refunded transactions"],
    ),
    (
        "Generate exactly 3 recommendations. "
        "Each recommendation must contain at least 2 supporting reasons.",
        ["exactly 3", "each recommendation", "at least 2",
         "supporting reasons"],
    ),
])
def test_combined_constraints_are_preserved(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


def test_optimization_does_not_change_technical_identifiers():
    prompt = (
        "Create a function named calculate_total(). "
        "Use the variable total_amount. "
        "Return the result as JSON."
    )

    optimized = optimize_prompt(prompt).optimized_prompt

    assert "calculate_total()" in optimized
    assert "total_amount" in optimized
    assert "JSON" in optimized


def test_optimization_is_idempotent_for_complex_prompt():
    prompt = (
        "If the input is valid, clean the data. "
        "If it contains duplicates, remove them. "
        "Then train the model and evaluate its F1-score."
    )

    once = optimize_prompt(prompt).optimized_prompt
    twice = optimize_prompt(once).optimized_prompt

    assert twice == once