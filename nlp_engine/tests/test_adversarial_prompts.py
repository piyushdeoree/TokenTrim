"""Adversarial regression tests for prompt optimization."""

import pytest

from nlp_engine import optimize_prompt


@pytest.mark.parametrize("prompt,required", [
    (
        'Do not replace "fraud" with "irregularity".',
        ["do not", "fraud", "irregularity"],
    ),
    (
        'The phrase "do not delete" is a required label. '
        "Include it exactly as written.",
        ["do not delete", "required label", "exactly"],
    ),
    (
        'Explain why "not secure" differs from "secure".',
        ["not secure", "secure"],
    ),
])
def test_negation_inside_quotes_is_preserved(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required", [
    (
        "If the user is authenticated, check whether the account is active. "
        "If it is active, allow access. Otherwise, deny access.",
        ["authenticated", "account is active", "allow access",
         "otherwise", "deny access"],
    ),
    (
        "If the dataset is clean, train the model unless it has fewer than "
        "100 records. If it has fewer than 100 records, collect more data.",
        ["if", "clean", "unless", "fewer than 100",
         "collect more data"],
    ),
])
def test_nested_conditions_and_exceptions(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required", [
    (
        "Use precision to evaluate the model. "
        "Use recall to evaluate the model.",
        ["precision", "recall"],
    ),
    (
        "Include active users. "
        "Exclude inactive users.",
        ["include active users", "exclude inactive users"],
    ),
    (
        "Summarize all transactions. "
        "Summarize only failed transactions.",
        ["all transactions", "only failed transactions"],
    ),
])
def test_similar_instructions_with_different_meanings(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required", [
    (
        "Explain the results, and compare them with the baseline.",
        ["explain", "compare", "baseline"],
    ),
    (
        "Analyze sales: include revenue, profit; exclude refunds.",
        ["analyze sales", "revenue", "profit", "exclude refunds"],
    ),
    (
        "Write a report. Do not summarize it; translate it into French.",
        ["report", "do not summarize", "translate", "french"],
    ),
])
def test_punctuation_and_conjunction_meaning(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required", [
    (
        "Keep response time below 500 milliseconds. "
        "Keep memory usage below 2 GB.",
        ["500 milliseconds", "2 gb"],
    ),
    (
        "Return between 5 and 10 examples. "
        "Each example must contain at least 2 sentences.",
        ["between 5 and 10", "at least 2 sentences"],
    ),
    (
        "Process data from 2020 to 2025. "
        "Exclude records before 2022.",
        ["2020", "2025", "before 2022"],
    ),
])
def test_mixed_numeric_constraints(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


@pytest.mark.parametrize("prompt,required", [
    (
        "Create a file at src/models/user_model.py. "
        "Do not rename user_model.py.",
        ["src/models/user_model.py", "do not rename"],
    ),
    (
        "Call the endpoint https://api.example.com/v1/users. "
        "Use the HTTP method POST.",
        ["https://api.example.com/v1/users", "post"],
    ),
    (
        "Use the function get_user_by_id(). "
        "Return user_id as the identifier.",
        ["get_user_by_id()", "user_id"],
    ),
])
def test_paths_urls_and_identifiers_are_preserved(prompt, required):
    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    for phrase in required:
        assert phrase.lower() in optimized


def test_code_block_is_preserved():
    prompt = '''Explain this Python code:

```python
def calculate_total(items):
    return sum(items)
```

Do not change the function name.'''

    optimized = optimize_prompt(prompt).optimized_prompt

    assert "def calculate_total(items):" in optimized
    assert "return sum(items)" in optimized
    assert "Do not change the function name" in optimized


def test_repeated_instruction_separated_by_context():
    prompt = (
        "Explain database normalization. "
        "Context: The database contains customer and order tables. "
        "Explain database normalization."
    )

    optimized = optimize_prompt(prompt).optimized_prompt.lower()

    assert optimized.count("explain database normalization") == 1
    assert "customer and order tables" in optimized


def test_adversarial_optimization_is_idempotent():
    prompt = (
        "If the input is valid, validate the schema. "
        "If validation succeeds, process the data. "
        "Do not process invalid data. "
        "Finally, save the output as JSON."
    )

    once = optimize_prompt(prompt).optimized_prompt
    twice = optimize_prompt(once).optimized_prompt

    assert twice == once
