"""Public package exports and return-contract regression tests."""

from __future__ import annotations

import importlib
import subprocess
import sys

from nlp_engine import (
    AnalysisResponse,
    BaseTokenCounter,
    DetailedAnalysis,
    Issue,
    OptimizationResult,
    PromptRequest,
    TokenizerInfo,
    ValidationResult,
    analyze_prompt,
    analyze_prompt_detailed,
    build_analysis,
    count_tokens,
    optimize_prompt,
    register_tokenizer,
    tokenizer_info,
    validate_optimization,
)
from nlp_engine import __all__ as package_exports
from nlp_engine import __version__
from nlp_engine.models import PromptAnalysis


TEST_MODEL = "tokentrim-public-api-contract-unknown"


def test_existing_and_approved_additive_root_exports_are_available():
    expected = {
        "analyze_prompt", "analyze_prompt_detailed", "build_analysis",
        "optimize_prompt", "validate_optimization", "count_tokens",
        "tokenizer_info", "register_tokenizer", "PromptRequest",
        "AnalysisResponse", "Issue", "DetailedAnalysis", "OptimizationResult",
        "ValidationResult", "TokenizerInfo", "BaseTokenCounter",
    }

    assert expected <= set(package_exports)
    assert all(name in globals() for name in expected)
    assert isinstance(__version__, str)


def test_root_import_does_not_load_the_optional_sentence_transformer_model():
    code = (
        "import sys; import nlp_engine; "
        "import nlp_engine.semantic_similarity as semantic; "
        "assert semantic._cached_model is None; "
        "assert not semantic._model_load_attempted; "
        "assert 'sentence_transformers' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_public_function_return_types_match_the_documented_contracts():
    prompt = "Please summarize the report. Please summarize the report."

    response = analyze_prompt("Explain indexing.", TEST_MODEL)
    detailed = analyze_prompt_detailed(prompt, TEST_MODEL)
    analysis = build_analysis("Explain indexing.", TEST_MODEL)
    candidate = optimize_prompt(prompt, model=TEST_MODEL)
    validation = validate_optimization(prompt, candidate.optimized_prompt)
    token_stats = count_tokens("Explain indexing.", TEST_MODEL)
    info = tokenizer_info(TEST_MODEL)

    assert isinstance(response, dict)
    assert set(response) == set(AnalysisResponse.model_fields)
    assert isinstance(detailed, DetailedAnalysis)
    assert isinstance(analysis, PromptAnalysis)  # deliberately not a package-root export
    assert isinstance(candidate, OptimizationResult)
    assert isinstance(validation, ValidationResult)
    assert set(token_stats) == {
        "input_tokens", "word_count", "character_count", "sentence_count"
    }
    assert isinstance(info, TokenizerInfo)
    assert isinstance(PromptRequest(prompt="Explain indexing."), PromptRequest)
    assert isinstance(Issue(type="general", severity="low", description="example"), Issue)


def test_optimize_prompt_exposes_a_candidate_and_validation_is_separate(monkeypatch):
    prompt = "Use exactly 7 workers."
    optimizer_module = importlib.import_module("nlp_engine.optimizer")

    def unsafe_test_rewrite(segments):
        for segment in segments:
            segment.text = segment.text.replace("7", "")
        return segments, []

    monkeypatch.setattr(optimizer_module, "rewrite_segments", unsafe_test_rewrite)

    candidate = optimize_prompt(prompt, model=TEST_MODEL)
    validation = validate_optimization(prompt, candidate.optimized_prompt)

    assert isinstance(candidate, OptimizationResult)
    assert candidate.method == "heuristic"
    assert "7" not in candidate.optimized_prompt
    assert isinstance(validation, ValidationResult)
    assert not validation.is_valid


def test_unaccepted_detailed_analysis_returns_the_exact_original_prompt():
    prompt = "  Explain indexing.\n\n  "

    detailed = analyze_prompt_detailed(prompt, TEST_MODEL)

    assert not detailed.optimization_accepted
    assert detailed.final.optimized_prompt == prompt
    assert detailed.final.tokens_saved == 0


def test_tokenizer_metadata_labels_exact_and_estimated_counts():
    exact_model = "tokentrim-public-api-contract-exact"

    class ExactCounter(BaseTokenCounter):
        def __init__(self, model: str):
            self.info = TokenizerInfo(
                model=model,
                family="custom",
                method="contract_test_counter",
                exact=True,
                note="Deterministic test counter.",
            )

        def count(self, text: str) -> int:
            return len(text.split())

    register_tokenizer(
        "public-api-contract-test",
        lambda model: model == exact_model,
        ExactCounter,
    )

    exact_info = tokenizer_info(exact_model)
    estimated_info = tokenizer_info(TEST_MODEL)

    assert exact_info.exact is True
    assert exact_info.method == "contract_test_counter"
    assert count_tokens("one two", exact_model)["input_tokens"] == 2
    assert estimated_info.exact is False
    assert estimated_info.method == "heuristic_estimate"


def test_llm_callback_failure_keeps_the_safe_heuristic_fallback():
    prompt = "  Please summarize the report.\nPlease summarize the report.  "

    def failing_callback(_rewrite_request: str) -> str:
        raise RuntimeError("local callback failure")

    detailed = analyze_prompt_detailed(prompt, TEST_MODEL, failing_callback)

    assert detailed.optimization_accepted
    assert detailed.final.method == "heuristic"
    assert detailed.validation.is_valid
    assert detailed.final.tokens_saved > 0
