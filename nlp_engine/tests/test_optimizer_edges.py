"""Focused regression tests for optimizer clause splitting and redundancy."""

import pytest

from nlp_engine import optimize_prompt, analyze_prompt


@pytest.mark.parametrize("prompt,expected", [
    (
        "Explain database architecture; explain database architecture.",
        "Explain database architecture.",
    ),
    (
        "Summarize the report, summarize the report, and list its key findings.",
        "Summarize the report and list its key findings.",
    ),
    (
        "Write a report. Write a report. Then translate it into French.",
        "Write a report. Then translate it into French.",
    ),
    (
        "Explain the topic: include examples; include examples.",
        "Explain the topic and include examples.",
    ),
])
def test_duplicate_clause_optimization(prompt, expected):
    result = optimize_prompt(prompt)
    assert result.optimized_prompt == expected


@pytest.mark.parametrize("prompt,required", [
    (
        "Summarize the report. Translate it into French.",
        ["Summarize", "Translate"],
    ),
    (
        "Explain the topic. Include examples. List the key findings.",
        ["Explain", "Include", "List"],
    ),
    (
        "Compare Python and Java. Recommend one for beginners.",
        ["Compare", "Recommend"],
    ),
])
def test_distinct_instructions_are_preserved(prompt, required):
    result = optimize_prompt(prompt)

    for instruction in required:
        assert instruction.lower() in result.optimized_prompt.lower()


@pytest.mark.parametrize("prompt", [
    "Include security details. Do not include security details.",
    "Return exactly 5 examples. Return exactly 10 examples.",
    "Write in English. Translate the result into French.",
])
def test_distinct_constraints_are_not_removed(prompt):
    result = analyze_prompt(prompt)
    optimized = result["optimized_prompt"].lower()

    if "security" in prompt.lower():
        assert "include security" in optimized
        assert "do not include security" in optimized

    elif "exactly" in prompt.lower():
        assert "5 examples" in optimized
        assert "10 examples" in optimized

    elif "english" in prompt.lower():
        assert "english" in optimized
        assert "french" in optimized


def test_optimization_is_idempotent_for_duplicate_clauses():
    prompt = (
        "Explain database architecture; "
        "explain database architecture."
    )

    once = optimize_prompt(prompt).optimized_prompt
    twice = optimize_prompt(once).optimized_prompt

    assert twice == once


def test_duplicate_removal_does_not_remove_unique_followup():
    prompt = (
        "Write a report. "
        "Write a report. "
        "Then translate it into French."
    )

    result = optimize_prompt(prompt).optimized_prompt

    assert result.count("Write a report") == 1
    assert "translate it into french" in result.lower()