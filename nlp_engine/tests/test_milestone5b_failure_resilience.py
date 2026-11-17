"""Tests for Milestone 5B: Controlled Component Failures and Fallback Resilience.

Verifies that the NLP engine degrades gracefully to safe exact-original fallback
or pure lexical evaluation when tokenizers, semantic encoders, or LLM callbacks
fail, raise exceptions, return invalid outputs, or attempt unsafe modifications.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
import unittest.mock as mock
import pytest

from nlp_engine import (
    analyze_prompt,
    analyze_prompt_detailed,
    optimize_prompt,
    validate_optimization,
    DetailedAnalysis,
    OptimizationResult,
    ValidationResult,
    tokenizer_info,
    count_tokens,
)
from nlp_engine.optimizer import optimize_with_llm
from nlp_engine import semantic_similarity as semantic
from nlp_engine.models import Issue


# ---------------------------------------------------------------------------
# Test Data Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SAFE_PROMPT = (
    "Please implement a secure token cache with a 5-minute expiration time.\n"
    "Please implement a secure token cache with a 5-minute expiration time.\n"
    "Ensure cache keys are hashed with SHA-256."
)

SAMPLE_TECHNICAL_PROMPT = (
    "Connect to https://api.tokentrim.internal:8080/v1/costs using TLS 1.3.\n"
    "Store cache records in F:\\TokenTrim\\Cache\\records.db with permissions 0600.\n"
    "Do not disable SSL certificate verification under any circumstances."
)


class FakeFailingModel:
    def __init__(self, error=None):
        self.error = error or RuntimeError("Simulated encoder failure")

    def encode(self, texts, **kwargs):
        raise self.error


# ---------------------------------------------------------------------------
# D1. Tokenizer Failures
# ---------------------------------------------------------------------------

def test_tokenizer_fallback_to_heuristic_when_tiktoken_fails(monkeypatch):
    """When tiktoken is unavailable or raises, the tokenizer falls back to heuristic estimation."""
    from nlp_engine.tokenizer import get_counter
    get_counter.cache_clear()

    monkeypatch.setitem(sys.modules, "tiktoken", None)
    info = tokenizer_info("gpt-4o")
    assert info.exact is False
    assert info.method == "heuristic_estimate"

    stats = count_tokens("Testing heuristic fallback counting.", model="gpt-4o")
    assert stats["input_tokens"] > 0
    get_counter.cache_clear()


def test_tokenizer_failure_during_candidate_token_count_rejects_candidate():
    """When token counting fails during candidate evaluation, optimize_with_llm returns None."""
    with mock.patch("nlp_engine.optimizer.count_tokens_only", side_effect=RuntimeError("Token table fault")):
        res = optimize_with_llm(
            SAMPLE_SAFE_PROMPT,
            rewriter=lambda req: "Rewritten prompt",
            model="gpt-4o",
        )
        assert res is None


def test_tokenizer_failure_on_llm_candidate_token_count_rejects_candidate():
    """In analyze_prompt_detailed, if candidate token evaluation fails on LLM output, optimization falls back to original."""
    from nlp_engine.tokenizer import count_tokens_only
    orig_count = count_tokens_only(SAMPLE_SAFE_PROMPT, "gpt-4o")

    def selective_count(text, model="gpt-4o"):
        if "Rewritten" in text:
            raise RuntimeError("Candidate token evaluation failure")
        return orig_count

    with mock.patch("nlp_engine.optimizer.count_tokens_only", side_effect=selective_count):
        detailed = analyze_prompt_detailed(
            SAMPLE_SAFE_PROMPT,
            model="gpt-4o",
            llm_rewriter=lambda req: "Rewritten prompt",
        )
        assert isinstance(detailed, DetailedAnalysis)
        assert detailed.final.optimized_prompt == SAMPLE_SAFE_PROMPT
        assert detailed.optimization_accepted is False
        assert detailed.final.tokens_saved == 0


# ---------------------------------------------------------------------------
# D2. Semantic Encoder Failures
# ---------------------------------------------------------------------------

def test_semantic_model_load_exception_falls_back_to_lexical(monkeypatch):
    """If semantic model loading raises an exception, the pipeline degrades safely to lexical comparison."""
    monkeypatch.setenv(semantic.ENABLE_ENV, "true")

    class FakeSentenceTransformer:
        def __init__(self, model_name, device):
            raise RuntimeError("Model weights corrupted on disk")

    fake_module = SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    # get_semantic_model catches load failures and returns None
    assert semantic.get_semantic_model() is None

    # Pipeline operates cleanly without raising
    detailed = analyze_prompt_detailed(SAMPLE_SAFE_PROMPT, model="gpt-4o")
    assert isinstance(detailed, DetailedAnalysis)
    assert detailed.final.optimized_prompt is not None


def test_semantic_encoder_encode_exception_falls_back_to_lexical():
    """If the semantic encoder raises during matrix calculation, semantic_similarity_matrix returns None and pipeline degrades."""
    failing_model = FakeFailingModel(error=RuntimeError("CUDA out of memory during encoding"))
    result = semantic.semantic_similarity_matrix(["Sentence one", "Sentence two"], model=failing_model)
    assert result is None


def test_semantic_failure_never_authorizes_unsubsumed_deletion():
    """Even if semantic similarity matrix returns high scores, non-subsumed distinct requirements must NOT be deleted."""
    prompt = (
        "Cache timeout must be set to 300 seconds.\n"
        "Cache timeout must be set to 600 seconds."
    )
    fake_matrix = [[1.0, 0.99], [0.99, 1.0]]
    with mock.patch("nlp_engine.redundancy.semantic_similarity_matrix", return_value=fake_matrix):
        detailed = analyze_prompt_detailed(prompt, model="gpt-4o")
        assert "300" in detailed.final.optimized_prompt
        assert "600" in detailed.final.optimized_prompt


# ---------------------------------------------------------------------------
# D3. LLM Callback Failures
# ---------------------------------------------------------------------------

def test_llm_callback_exception_falls_back_to_exact_original():
    """When the LLM callback raises an arbitrary Exception, public pipeline falls back safely."""
    def failing_callback(req):
        raise ConnectionResetError("Remote LLM endpoint timed out")

    detailed = analyze_prompt_detailed(SAMPLE_TECHNICAL_PROMPT, model="gpt-4o", llm_rewriter=failing_callback)
    assert isinstance(detailed, DetailedAnalysis)
    assert detailed.final.optimized_prompt == SAMPLE_TECHNICAL_PROMPT
    assert detailed.final.tokens_saved == 0
    assert detailed.optimization_accepted is False


def test_llm_callback_empty_or_whitespace_returns_exact_original():
    """Empty or whitespace-only LLM output is rejected with exact-original fallback."""
    detailed = analyze_prompt_detailed(
        SAMPLE_TECHNICAL_PROMPT,
        model="gpt-4o",
        llm_rewriter=lambda req: "   \n\t  ",
    )
    assert detailed.final.optimized_prompt == SAMPLE_TECHNICAL_PROMPT
    assert detailed.optimization_accepted is False


def test_llm_callback_non_string_returns_exact_original():
    """Non-string LLM callback output is rejected with exact-original fallback."""
    detailed = analyze_prompt_detailed(
        SAMPLE_TECHNICAL_PROMPT,
        model="gpt-4o",
        llm_rewriter=lambda req: {"rewritten_prompt": "some content"},
    )
    assert detailed.final.optimized_prompt == SAMPLE_TECHNICAL_PROMPT
    assert detailed.optimization_accepted is False


def test_llm_callback_unsafe_negation_flip_is_rejected():
    """Candidate that flips negation polarity (removes 'Do not') must be rejected by validation."""
    unsafe_rewrite = (
        "Connect to https://api.tokentrim.internal:8080/v1/costs using TLS 1.3.\n"
        "Store cache records in F:\\TokenTrim\\Cache\\records.db with permissions 0600.\n"
        "Disable SSL certificate verification."
    )
    # Direct validation check
    val = validate_optimization(SAMPLE_TECHNICAL_PROMPT, unsafe_rewrite)
    assert val.is_valid is False
    assert any("not" in r.lower() or "lost" in r.lower() for r in val.reasons)

    # Full pipeline check
    detailed = analyze_prompt_detailed(
        SAMPLE_TECHNICAL_PROMPT,
        model="gpt-4o",
        llm_rewriter=lambda req: unsafe_rewrite,
    )
    assert detailed.final.optimized_prompt == SAMPLE_TECHNICAL_PROMPT
    assert detailed.optimization_accepted is False


def test_llm_callback_negative_token_savings_is_rejected():
    """Candidate that adds unnecessary verbosity (negative token savings) must be rejected."""
    verbose_rewrite = (
        SAMPLE_TECHNICAL_PROMPT
        + "\nFurthermore, please make absolutely certain that every single guideline above is followed to the letter without omission."
    )
    detailed = analyze_prompt_detailed(
        SAMPLE_TECHNICAL_PROMPT,
        model="gpt-4o",
        llm_rewriter=lambda req: verbose_rewrite,
    )
    assert detailed.final.optimized_prompt == SAMPLE_TECHNICAL_PROMPT
    assert detailed.optimization_accepted is False


def test_llm_callback_missing_technical_identifier_is_rejected():
    """Candidate omitting a technical identifier, URL, or filepath is rejected by validation."""
    identifier_dropped_rewrite = (
        "Connect to the cost API using TLS 1.3.\n"
        "Store cache records locally with permissions 0600.\n"
        "Do not disable SSL certificate verification under any circumstances."
    )
    # Direct validation check
    val = validate_optimization(SAMPLE_TECHNICAL_PROMPT, identifier_dropped_rewrite)
    assert val.is_valid is False
    assert any("url" in r.lower() or "code" in r.lower() or "identifier" in r.lower() or "lost" in r.lower() for r in val.reasons)

    # Full pipeline check
    detailed = analyze_prompt_detailed(
        SAMPLE_TECHNICAL_PROMPT,
        model="gpt-4o",
        llm_rewriter=lambda req: identifier_dropped_rewrite,
    )
    assert detailed.final.optimized_prompt == SAMPLE_TECHNICAL_PROMPT
    assert detailed.optimization_accepted is False


# ---------------------------------------------------------------------------
# D4. Repeated Failure Recovery & State Isolation
# ---------------------------------------------------------------------------

def test_repeated_failure_interleaved_with_successful_requests():
    """Alternating between failing and successful requests demonstrates no cross-request state leakage."""
    call_count = 0

    def alternating_llm_callback(req):
        nonlocal call_count
        call_count += 1
        if call_count % 2 == 1:
            raise RuntimeError(f"Simulated fault on call #{call_count}")
        return req.prompt

    for i in range(1, 7):
        res = analyze_prompt_detailed(
            SAMPLE_SAFE_PROMPT,
            model="gpt-4o",
            llm_rewriter=alternating_llm_callback,
        )
        assert isinstance(res, DetailedAnalysis)
        assert res.final.optimized_prompt is not None


# ---------------------------------------------------------------------------
# D5. Exact Preservation on Fallback
# ---------------------------------------------------------------------------

def test_exact_original_whitespace_and_crlf_preserved_on_all_failures():
    """Prompts with unusual whitespace, trailing spaces, and CRLF must be returned byte-for-byte on fallback."""
    crlf_prompt = "Line 1 with trailing space   \r\n\tLine 2 with tab.\r\n\r\nLine 3.\r\n"

    def exploding_callback(req):
        raise MemoryError("Out of memory in callback")

    detailed = analyze_prompt_detailed(crlf_prompt, model="gpt-4o", llm_rewriter=exploding_callback)
    assert detailed.final.optimized_prompt == crlf_prompt
    assert detailed.optimization_accepted is False
