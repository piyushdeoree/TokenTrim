"""Regression tests for semantic preservation during prompt optimization."""

import pytest

from nlp_engine import optimize_prompt


@pytest.mark.parametrize("prompt,required_phrases", [
    (
        "If the input is empty, return an error. "
        "Otherwise, summarize the report.",
        ["if", "input", "empty", "error", "otherwise", "summarize", "report"],
    ),
    (
        "Unless the user asks for examples, "
        "do not include examples.",
        ["unless", "user", "examples", "do not include examples"],
    ),
    (
        "Generate a chart only when at least 10 records are available.",
        ["only when", "at least 10", "records"],
    ),
])
def test_conditional_meaning_is_preserved(prompt, required_phrases):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required_phrases:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required_phrases", [
    (
        "Compare Python and Java for memory usage. "
        "Recommend Python only if memory usage is lower.",
        ["python", "java", "only if", "memory usage", "lower"],
    ),
    (
        "Use more than 5 examples, but fewer than 10.",
        ["more than 5", "fewer than 10"],
    ),
])
def test_comparison_meaning_is_preserved(prompt, required_phrases):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required_phrases:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required_phrases", [
    (
        "Include every transaction, including successful "
        "and failed transactions.",
        ["every", "successful", "failed"],
    ),
    (
        "Return only the top 3 results, not the full list.",
        ["only", "top 3", "not", "full list"],
    ),
])
def test_scope_and_completeness_are_preserved(prompt, required_phrases):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required_phrases:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required_phrases", [
    (
        "Before generating the report, validate the input. "
        "After validation, calculate the totals.",
        ["before", "validate", "after", "calculate", "totals"],
    ),
    (
        "First clean the data. Then train the model. "
        "Finally evaluate it.",
        ["first", "clean", "then", "train", "finally", "evaluate"],
    ),
])
def test_instruction_sequence_is_preserved(prompt, required_phrases):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required_phrases:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required_phrases", [
    (
        "Summarize all chapters except the introduction "
        "and appendix.",
        ["all chapters", "except", "introduction", "appendix"],
    ),
    (
        "Include all records, excluding deleted records.",
        ["all records", "excluding", "deleted records"],
    ),
])
def test_exceptions_are_preserved(prompt, required_phrases):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required_phrases:
        assert phrase.lower() in optimized