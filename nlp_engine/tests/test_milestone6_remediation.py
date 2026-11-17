"""Regression tests for Milestone 6 remediation items.

Covers:
1. Single-pass PreparedPrompt reuse across tokenization, analysis, and validation.
2. O(N) exact-duplicate clause deduplication above the 300-clause pairwise limit.
3. Single-quoted literal protection (without mangling contractions or possessives).
4. Sub-clause-level constraint validation (preventing deleted negations from being
   masked by unrelated negations or unrelated candidate clause aggregation).
5. Thread-safe lazy semantic model initialization and tokenizer registry updates.
"""

from __future__ import annotations

import concurrent.futures
import importlib
import sys
import types

import pytest

from nlp_engine import (
    analyze_prompt,
    analyze_prompt_detailed,
    count_tokens,
    register_tokenizer,
    validate_optimization,
)
from nlp_engine.textutils import prepare_prompt, protect_spans
from nlp_engine.tokenizer import BaseTokenCounter, TokenizerInfo


MODEL = "tokentrim-milestone6-remediation"


def test_prepared_prompt_reuse_produces_equivalent_results():
    prompt = (
        "Please carefully summarize the quarterly financial report.\n"
        "Please carefully summarize the quarterly financial report.\n"
        "Ensure all revenue numbers from 2025 are preserved in JSON."
    )
    prepared = prepare_prompt(prompt)

    counts_direct = count_tokens(prompt, MODEL)
    counts_reused = count_tokens(prompt, MODEL, prepared=prepared)
    assert counts_reused == counts_direct

    optimized = (
        "Summarize the quarterly financial report.\n"
        "Ensure all revenue numbers from 2025 are preserved in JSON."
    )

    val_direct = validate_optimization(prompt, optimized)
    val_reused = validate_optimization(
        prompt,
        optimized,
        original_prepared=prepared,
    )
    assert val_reused.is_valid == val_direct.is_valid
    assert val_reused.reasons == val_direct.reasons
    assert val_reused.metrics == val_direct.metrics


def test_mismatched_prepared_prompt_is_ignored():
    prompt = "Summarize the report in JSON."
    wrong_prepared = prepare_prompt("Different text with three sentences. One. Two.")

    counts_direct = count_tokens(prompt, MODEL)
    counts_with_wrong = count_tokens(prompt, MODEL, prepared=wrong_prepared)
    assert counts_with_wrong == counts_direct


@pytest.mark.parametrize("clause_count", [299, 300, 301, 591, 2000])
def test_exact_duplicates_detected_linearly_at_and_above_300_clauses(clause_count):
    clause = "Explain database indexing."
    prompt = " ".join([clause] * clause_count)

    detailed = analyze_prompt_detailed(prompt, MODEL)
    assert detailed.optimization_accepted
    assert detailed.final.optimized_prompt.count("Explain database indexing") == 1
    assert detailed.final.tokens_saved > 0

    simple = analyze_prompt(prompt, MODEL)
    assert simple["optimized_prompt"].count("Explain database indexing") == 1
    assert simple["tokens_saved"] > 0


def test_non_duplicate_clauses_above_300_remain_unmodified():
    clauses = [f"Summarize section {idx} of the audit." for idx in range(1, 315)]
    prompt = " ".join(clauses)

    detailed = analyze_prompt_detailed(prompt, MODEL)
    assert not detailed.optimization_accepted
    assert detailed.final.optimized_prompt == prompt
    assert detailed.final.tokens_saved == 0


def test_large_clause_exact_duplicate_preserves_polarity_and_numbers():
    filler = [f"Include metric M{idx:04d} in the output." for idx in range(1, 306)]
    duplicates = [
        "Return exactly 5 records.",
        "Return exactly 5 records.",
        "Return exactly 10 records.",
        "Include audit logs.",
        "Do not include audit logs.",
    ]
    prompt = " ".join(filler + duplicates)

    detailed = analyze_prompt_detailed(prompt, MODEL)
    out = detailed.final.optimized_prompt

    assert detailed.optimization_accepted
    assert out.count("Return exactly 5 records.") == 1
    assert "Return exactly 10 records." in out
    assert "Include audit logs." in out
    assert "Do not include audit logs." in out


def test_single_quoted_literals_protected_while_contractions_and_multiline_safe():
    prompt = (
        "Do not replace 'fraud_flag' or 'pending_review' in the user's records.\n"
        "Users' accounts don't change unless status is 'ACTIVE'.\n"
        "Please summarize the report. Please summarize the report."
    )
    prepared = prepare_prompt(prompt)
    assert prepared.unmask(prepared.masked) == prompt

    # Verify through public/functional optimization output that quoted literals are kept
    detailed = analyze_prompt_detailed(prompt, MODEL)
    out = detailed.final.optimized_prompt
    assert detailed.optimization_accepted
    assert "'fraud_flag'" in out
    assert "'pending_review'" in out
    assert "'ACTIVE'" in out


def test_overlapping_backticks_and_single_quotes_do_not_corrupt_spans():
    prompt = "Keep `SELECT * FROM users WHERE role = 'admin'` and 'literal_token' intact."
    prepared = prepare_prompt(prompt)
    assert prepared.unmask(prepared.masked) == prompt
    assert "`SELECT * FROM users WHERE role = 'admin'`" in prompt
    assert "'literal_token'" in prompt


def test_compound_constraint_rejects_deleted_negation_masked_by_unrelated_negation():
    original = (
        "Keep user data encrypted at rest and do not expose internal stack traces. "
        "Do not log raw credentials."
    )
    # Drops "do not expose internal stack traces" while another negation ("Do not log") exists
    lossy_candidate = "Keep user data encrypted at rest. Do not log raw credentials."

    validation = validate_optimization(original, lossy_candidate)
    assert not validation.is_valid
    assert any("Constraint" in reason or "negation" in reason for reason in validation.reasons)


def test_split_compound_constraints_with_matching_polarity_pass_validation():
    original = "Keep user data encrypted at rest and do not expose internal stack traces."
    valid_candidate = (
        "Keep user data encrypted at rest. Do not expose internal stack traces."
    )

    validation = validate_optimization(original, valid_candidate)
    assert validation.is_valid


def test_unrelated_candidate_clauses_cannot_aggregate_stems_to_pass_constraint():
    original = "Ensure every JSON response includes request_id and timestamp."
    fragmented_candidate = (
        "Ensure every response is valid. "
        "Log the request_id separately. "
        "Record the timestamp in metrics."
    )

    validation = validate_optimization(original, fragmented_candidate)
    assert not validation.is_valid


def test_concurrent_semantic_model_initialization_runs_once(monkeypatch):
    semantic = importlib.import_module("nlp_engine.semantic_similarity")
    monkeypatch.setenv(semantic.ENABLE_ENV, "true")
    monkeypatch.setattr(semantic, "_cached_model", None)
    monkeypatch.setattr(semantic, "_model_load_attempted", False)

    init_calls = []

    class FakeSentenceTransformer:
        def __init__(self, model_name, device="cpu", **_kwargs):
            init_calls.append((model_name, device))

        def encode(self, texts, **_kwargs):
            import numpy as np

            return np.ones((len(texts), 4), dtype=float)

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(semantic.get_semantic_model) for _ in range(16)]
        results = [fut.result() for fut in futures]

    assert len(init_calls) == 1
    assert all(res is results[0] and res is not None for res in results)


def test_concurrent_tokenizer_registry_updates_are_consistent():
    class FixedSevenCounter(BaseTokenCounter):
        info = TokenizerInfo("m6-custom", "custom", "fixed_7", True, "test counter")

        def count(self, text: str) -> int:
            return 7

    prefix = "m6-concurrent-model-"

    def worker(idx: int) -> int:
        model_name = f"{prefix}{idx}"
        register_tokenizer(
            f"tok-{idx}",
            lambda m, target=model_name: m == target,
            lambda _m: FixedSevenCounter(),
        )
        return count_tokens("hello world", model_name)["input_tokens"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(worker, range(12)))

    assert results == [7] * 12