"""Regression coverage for exact input fallback and rewrite callback boundaries."""

from __future__ import annotations

import importlib

import pytest

from nlp_engine import analyze_prompt, analyze_prompt_detailed
from nlp_engine.models import OptimizationResult
from nlp_engine.tokenizer import count_tokens_only


ANALYZER = importlib.import_module("nlp_engine.analyzer")
TEST_MODEL = "tokentrim-public-boundary-test"


@pytest.mark.parametrize(
    "prompt",
    [
        "  Explain indexing.",
        "Explain indexing.  ",
        "  Explain indexing.  ",
        "\tExplain indexing.\n\nA second paragraph stays separate.  ",
        "\tExplain indexing.\n\n\n\tKeep the final line intact.\t",
    ],
    ids=("leading", "trailing", "both", "paragraphs", "tabs-and-newlines"),
)
def test_no_optimization_returns_exact_original_whitespace(prompt):
    result = analyze_prompt(prompt, TEST_MODEL)

    assert result["optimized_prompt"] == prompt
    assert result["tokens_saved"] == 0


def test_no_token_savings_returns_exact_original_input():
    prompt = "  Explain indexing.  "

    detailed = analyze_prompt_detailed(prompt, TEST_MODEL)

    assert not detailed.optimization_accepted
    assert detailed.final.optimized_prompt == prompt
    assert detailed.final.original_tokens == count_tokens_only(prompt, TEST_MODEL)
    assert detailed.final.tokens_saved == 0


def test_rejected_optimization_returns_exact_original_input(monkeypatch):
    prompt = "  Please summarize the report.\nPlease summarize the report.  "

    def reject_candidate(_original, _candidate):
        from nlp_engine.models import ValidationResult

        return ValidationResult(
            is_valid=False,
            reasons=["rejected by boundary regression test"],
            metrics={},
        )

    monkeypatch.setattr(ANALYZER, "validate_optimization", reject_candidate)
    detailed = analyze_prompt_detailed(prompt, TEST_MODEL)

    assert not detailed.optimization_accepted
    assert not detailed.validation.is_valid
    assert detailed.final.optimized_prompt == prompt
    assert detailed.final.original_tokens == count_tokens_only(prompt, TEST_MODEL)
    assert detailed.final.tokens_saved == 0


def test_accepted_optimization_is_validated_against_exact_original(monkeypatch):
    prompt = (
        "  Please summarize the report.\n"
        "Please summarize the report.\n"
        "Return JSON.  "
    )
    original_validator = ANALYZER.validate_optimization
    validated_originals = []

    def recording_validator(original, candidate):
        validated_originals.append(original)
        return original_validator(original, candidate)

    monkeypatch.setattr(ANALYZER, "validate_optimization", recording_validator)
    detailed = analyze_prompt_detailed(prompt, TEST_MODEL)

    assert detailed.optimization_accepted
    assert detailed.validation.is_valid
    assert prompt in validated_originals
    assert "Return JSON" in detailed.final.optimized_prompt
    assert detailed.final.original_tokens == count_tokens_only(prompt, TEST_MODEL)
    assert detailed.final.tokens_saved > 0


def test_accepted_candidate_counts_the_exact_untrimmed_original(monkeypatch):
    optimizer_module = importlib.import_module("nlp_engine.optimizer")
    prompt = (
        "  Please summarize the report.\n"
        "Please summarize the report.  "
    )
    monkeypatch.setattr(
        optimizer_module,
        "count_tokens_only",
        lambda text, _model=None: len(text),
    )

    detailed = analyze_prompt_detailed(prompt, TEST_MODEL)

    assert detailed.optimization_accepted
    assert detailed.final.original_tokens == len(prompt)
    assert detailed.final.optimized_tokens == len(detailed.final.optimized_prompt)
    assert detailed.final.tokens_saved == (
        detailed.final.original_tokens - detailed.final.optimized_tokens
    )


@pytest.mark.parametrize(
    "callback_result",
    ["", " \n\t ", None, b"Explain briefly.", 17, ["Explain briefly."]],
    ids=("empty", "whitespace", "none", "bytes", "integer", "other-type"),
)
def test_invalid_callback_results_are_rejected_without_crashing(callback_result):
    prompt = "  Explain indexing.  "

    detailed = analyze_prompt_detailed(
        prompt,
        TEST_MODEL,
        llm_rewriter=lambda _request: callback_result,
    )

    assert not detailed.optimization_accepted
    assert detailed.final.optimized_prompt == prompt
    assert detailed.final.tokens_saved == 0


def test_callback_exception_falls_back_to_exact_original():
    prompt = "\tExplain indexing.\n\n"

    def failing_callback(_request):
        raise RuntimeError("local callback failure")

    detailed = analyze_prompt_detailed(
        prompt,
        TEST_MODEL,
        llm_rewriter=failing_callback,
    )

    assert not detailed.optimization_accepted
    assert detailed.final.optimized_prompt == prompt
    assert detailed.final.tokens_saved == 0


def test_valid_string_callback_candidate_remains_eligible(monkeypatch):
    prompt = "You are a helpful assistant. Return the result."
    rewrite = "Return the result."
    token_count = count_tokens_only(prompt, TEST_MODEL)

    def unchanged_heuristic(candidate_prompt, _analysis):
        return OptimizationResult(
            optimized_prompt=candidate_prompt,
            original_tokens=token_count,
            optimized_tokens=token_count,
            tokens_saved=0,
            reduction_percentage=0.0,
            changes=[],
            method="heuristic",
        )

    monkeypatch.setattr(ANALYZER, "optimize_prompt", unchanged_heuristic)
    detailed = analyze_prompt_detailed(
        prompt,
        TEST_MODEL,
        llm_rewriter=lambda _request: rewrite,
    )

    assert detailed.optimization_accepted
    assert detailed.final.method == "llm"
    assert detailed.final.optimized_prompt == rewrite
    assert detailed.validation.is_valid
    assert detailed.final.tokens_saved > 0


def test_invalid_callback_keeps_valid_heuristic_candidate():
    prompt = (
        "  Please summarize the report.\n"
        "Please summarize the report.  "
    )

    detailed = analyze_prompt_detailed(
        prompt,
        TEST_MODEL,
        llm_rewriter=lambda _request: b"Summarize the report.",
    )

    assert detailed.optimization_accepted
    assert detailed.final.method == "heuristic"
    assert detailed.validation.is_valid
    assert detailed.final.optimized_prompt.lower().count("summarize the report") == 1
    assert detailed.final.original_tokens == count_tokens_only(prompt, TEST_MODEL)
