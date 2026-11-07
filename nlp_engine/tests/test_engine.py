"""pytest suite. Run from the PARENT directory of nlp_engine: pytest nlp_engine/tests -v"""

import pytest

from nlp_engine import (
    analyze_prompt,
    analyze_prompt_detailed,
    count_tokens,
    optimize_prompt,
    register_tokenizer,
    tokenizer_info,
    validate_optimization,
)
from nlp_engine.tokenizer import BaseTokenCounter, TokenizerInfo
from nlp_engine.textutils import protect_spans, unprotect

from .test_cases import CASES

CONTRACT_KEYS = {
    "original_tokens", "optimized_tokens", "tokens_saved",
    "reduction_percentage", "word_count", "complexity_score",
    "issues", "suggestions", "optimized_prompt"
}


# ------------------------- the 10 required scenarios -------------------------

@pytest.mark.parametrize("case", CASES, ids=[f"{c['id']:02d}-{c['name']}" for c in CASES])
def test_scenarios(case):
    d = analyze_prompt_detailed(case["prompt"], "gpt-4o")
    opt = d.final.optimized_prompt

    for needle in case["must_contain"]:
        assert needle in opt, f"lost: {needle[:60]!r}"

    assert d.final.tokens_saved == d.final.original_tokens - d.final.optimized_tokens >= 0
    assert d.final.optimized_tokens <= d.final.original_tokens

    if case["expect_change"] is True:
        assert d.final.tokens_saved > 0 and d.optimization_accepted
    elif case["expect_change"] is False:
        assert opt == case["prompt"].strip() and d.final.tokens_saved == 0
    else:
        assert (not d.optimization_accepted) or d.final.tokens_saved > 0


def test_spec_example_content():
    out = analyze_prompt(CASES[6]["prompt"], "gpt-4o")["optimized_prompt"]
    assert "You are an expert assistant" not in out
    assert out.lower().count("analyze") == 1
    assert "I would like you to" not in out and "carefully" not in out


def test_second_pass_changes_nothing():
    for c in CASES:
        once = analyze_prompt(c["prompt"])["optimized_prompt"]
        twice = analyze_prompt(once)
        assert twice["tokens_saved"] == 0, c["name"]


# ------------------------------- output contract -----------------------------

def test_output_contract():
    r = analyze_prompt("Please summarize this text.", "gpt-4o")
    assert set(r) == CONTRACT_KEYS
    assert isinstance(r["issues"], list) and all(
        set(i) == {"type", "severity", "description"} for i in r["issues"]
    )
    assert 0 <= r["complexity_score"] <= 100
    assert r["reduction_percentage"] == round(
        100 * r["tokens_saved"] / r["original_tokens"], 2
    )


@pytest.mark.parametrize("bad", ["", "   ", "\n"])
def test_empty_prompt_rejected(bad):
    with pytest.raises(ValueError):
        analyze_prompt(bad)


def test_optimize_prompt_signature():
    p = "Please analyze it carefully and provide me with a detailed summary."
    res = optimize_prompt(p)
    assert res.optimized_tokens <= res.original_tokens
    assert res.optimized_prompt.startswith("Analyze it") or "summary" in res.optimized_prompt


# --------------------------------- tokenizer ---------------------------------

def test_count_tokens_fields():
    r = count_tokens("Hello world. How are you?", "gpt-4o")
    assert set(r) == {"input_tokens", "word_count", "character_count", "sentence_count"}
    assert r["word_count"] == 5 and r["character_count"] == 25 and r["sentence_count"] == 2
    assert r["input_tokens"] > 0


@pytest.mark.parametrize("model", ["claude-sonnet-4-5", "gemini-2.0-flash", "some-unknown-model"])
def test_non_openai_models_are_labelled_estimates(model):
    info = tokenizer_info(model)
    assert info.exact is False and info.method == "heuristic_estimate" and info.note


def test_openai_method_is_labelled():
    info = tokenizer_info("gpt-4o")
    assert (info.exact and info.method.startswith("tiktoken:")) or \
           (not info.exact and info.method == "heuristic_estimate")


def test_custom_tokenizer_can_be_registered():
    class Dummy(BaseTokenCounter):
        info = TokenizerInfo("dummy-1", "custom", "dummy:whitespace", True, "test")

        def count(self, text):
            return len(text.split())

    register_tokenizer("dummy", lambda m: m.startswith("dummy-"), lambda m: Dummy())
    assert count_tokens("a b c d", "dummy-1")["input_tokens"] == 4
    assert tokenizer_info("dummy-1").method == "dummy:whitespace"


# ---------------------------------- validator --------------------------------

def test_validator_accepts_safe_rewrite():
    v = validate_optimization(
        "Please summarize the Q3 report in under 150 words.",
        "Summarize the Q3 report in under 150 words."
    )
    assert v.is_valid, v.reasons


@pytest.mark.parametrize("orig,bad,fragment", [
    ("Summarize the report in under 150 words.", "Summarize the report.", "Numbers lost"),
    ("Return the answer as JSON listing every city.", "Return the answer listing every city.", "format"),
    ("Summarize https://example.com/a in one line.", "Summarize the page in one line.", "URL"),
    ("Explain the idea. Do not use jargon.", "Explain the idea.", "Constraint"),
    ("Compare Postgres and MySQL for analytics.", "Compare the two databases for analytics.", "Named items"),
])
def test_validator_rejects_information_loss(orig, bad, fragment):
    v = validate_optimization(orig, bad)
    assert not v.is_valid
    assert any(fragment.lower() in r.lower() for r in v.reasons), v.reasons


def test_rejected_candidate_returns_original():
    p = "Please summarize the report in under 150 words."
    lossy = lambda text: "Summarize the report."
    d = analyze_prompt_detailed(p, "gpt-4o", llm_rewriter=lossy)
    assert "150 words" in d.final.optimized_prompt
    assert d.final.method != "llm"


def test_llm_hook_exceptions_are_ignored():
    def boom(_):
        raise RuntimeError("network down")

    r = analyze_prompt("Please summarize this text.", "gpt-4o", llm_rewriter=boom)
    assert r["optimized_prompt"]


# ------------------------------ individual detectors -------------------------

def _types(prompt):
    return {(i.type, i.severity) for i in analyze_prompt_detailed(prompt).issues}


def test_detects_conflicting_style():
    assert any(t == "conflict" for t, _ in _types(
        "Write a detailed but concise summary of the text."
    ))


def test_detects_direct_contradiction():
    assert ("conflict", "high") in _types(
        "Include examples in the answer. Do not include examples in the answer."
    )


def test_detects_numeric_limit_conflict():
    assert any(t == "conflict" for t, _ in _types(
        "Write at least 200 words. Keep it under 100 words."
    ))


@pytest.mark.parametrize("prompt,expected_conflict", [
    ("Write exactly 200 words. Keep it under 150 words.", True),
    ("Write exactly 100 words. Write at least 150 words.", True),
    ("Write exactly 200 words. Keep it under 250 words.", False),
])
def test_detects_exact_count_conflicts(prompt, expected_conflict):
    has_conflict = any(t == "conflict" for t, _ in _types(prompt))
    assert has_conflict == expected_conflict


def test_detects_conflict_with_multiple_minimum_limits():
    prompt = (
        "Write at least 100 words. "
        "Write at least 200 words. "
        "Keep it under 150 words."
    )
    assert any(t == "conflict" for t, _ in _types(prompt))


def test_detects_conflicting_formats():
    assert any(t == "conflict" for t, _ in _types(
        "Respond in JSON. Respond as plain text."
    ))


def test_detects_formatting_overload():
    p = "Use bullet points, bold the key terms, add headings, include a table and some emojis."
    assert any(t == "formatting" for t, _ in _types(p))


def test_detects_repeated_phrases():
    p = (
        "Write the report in a friendly tone for new customers. "
        "Explain pricing in a friendly tone for new customers. "
        "Close in a friendly tone for new customers."
    )
    assert any(t == "repeated_phrase" for t, _ in _types(p))


def test_non_duplicate_similar_instructions_are_not_removed():
    p = "Summarize the text in French. Summarize the report in German."
    out = analyze_prompt(p)["optimized_prompt"]
    assert "French" in out and "German" in out


# ----------------------- NEW REDUNDANCY REGRESSION TESTS -----------------------

def test_instruction_and_question_are_not_merged():
    p = "Explain the database architecture. What is the database architecture?"
    out = analyze_prompt(p)["optimized_prompt"]

    assert "Explain" in out
    assert "What is" in out


def test_different_numbers_are_not_merged():
    p = "Return exactly 5 examples. Return exactly 10 examples."
    out = analyze_prompt(p)["optimized_prompt"]

    assert "5 examples" in out
    assert "10 examples" in out


def test_different_negation_is_not_merged():
    p = "Include security details. Do not include security details."
    out = analyze_prompt(p)["optimized_prompt"]

    assert "Include" in out
    assert "Do not include" in out


def test_distinct_instruction_verbs_are_not_merged():
    p = "Summarize the report. Translate the report into French."
    out = analyze_prompt(p)["optimized_prompt"]

    assert "Summarize" in out
    assert "Translate" in out


def test_repeated_phrases_across_sentences_are_detected():
    p = (
        "Write a report in a friendly tone for new customers. "
        "Prepare an explanation in a friendly tone for new customers."
    )
    assert any(t == "repeated_phrase" for t, _ in _types(p))


def test_negation_is_never_merged_away():
    p = "Include code examples. Do not include code examples."
    out = analyze_prompt(p)["optimized_prompt"]
    assert "Do not" in out and "Include" in out


def test_specific_persona_is_kept():
    out = analyze_prompt(
        "You are an expert Python developer. Review this function."
    )["optimized_prompt"]
    assert "expert Python developer" in out


def test_context_is_never_edited():
    ctx = "Please carefully note that I would like you to ignore this. Please ignore this."
    p = f"Summarize the following text.\n\nText:\n{ctx}"
    assert ctx in analyze_prompt(p)["optimized_prompt"]


def test_protect_spans_roundtrip():
    text = 'Use `x = 1` and see https://a.b/c, then "quoted text" and {"k": [1, 2]}.'
    masked, mapping = protect_spans(text)
    assert "https://" not in masked and "`x" not in masked
    assert unprotect(masked, mapping) == text


# ------------------------------ regression tests -----------------------------

def test_duplicate_list_items_are_merged_and_indentation_kept():
    p = (
        "Tasks:\n"
        "- Please summarize the text.\n"
        "- Please summarize the text.\n"
        "  - Make sure that it is short.\n"
        "1. Translate it to French."
    )
    d = analyze_prompt_detailed(p)
    assert d.optimization_accepted
    out = d.final.optimized_prompt
    assert out.count("ummarize") == 1
    assert "\n  - Ensure it is short." in out
    assert "1. Translate it to French." in out


def test_non_english_text_is_left_untouched():
    p = "\u8bf7\u7528\u4e2d\u6587\u603b\u7ed3\u8fd9\u6bb5\u6587\u5b57\u3002Please summarize this."
    assert analyze_prompt(p)["optimized_prompt"] == p


def test_large_prompt_completes_quickly():
    import time

    big = (
        "Please analyze the data carefully. "
        + "The sensor reading was stable and within the expected range. " * 3000
    )
    t = time.time()
    r = analyze_prompt(big, "gpt-4o")
    assert time.time() - t < 30
    assert "The sensor reading was stable" in r["optimized_prompt"]
    assert r["optimized_prompt"].count("The sensor reading") == 3000


def test_descriptive_text_with_within_is_not_a_constraint():
    d = analyze_prompt_detailed(
        "The reading was within the expected range. "
        "The reading was within the expected range."
    )
    assert not any(i.type == "duplicate_constraint" for i in d.issues)
