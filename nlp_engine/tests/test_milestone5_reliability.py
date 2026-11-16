"""Public-pipeline reliability cases for large and difficult prompts.

These checks focus on observable safety behavior. They do not impose latency
targets or change the engine's conservative clause-count policy.
"""

from __future__ import annotations

import importlib

import pytest

from nlp_engine import analyze_prompt_detailed


MODEL = "tokentrim-milestone5-reliability"


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        "   \t\r\n",
        "\r\n\t\r\n",
    ],
    ids=("empty", "whitespace-only", "newline-only"),
)
def test_empty_inputs_fail_at_public_boundary(prompt):
    with pytest.raises(ValueError):
        analyze_prompt_detailed(prompt, MODEL)


@pytest.mark.parametrize(
    "prompt",
    [
        "word",
        "One complete sentence.",
        "!!! ???",
        "   Keep café text as provided.  ",
        "  Support English and සිංහල together.\r\n\r\nKeep this line.  ",
    ],
    ids=("word", "sentence", "punctuation", "unicode", "mixed-scripts"),
)
def test_minimal_or_uneditable_inputs_keep_exact_original(prompt):
    result = analyze_prompt_detailed(prompt, MODEL)

    assert result.final.optimized_prompt == prompt
    assert result.final.tokens_saved == 0
    assert not result.optimization_accepted


@pytest.mark.parametrize(
    "prompt",
    [
        "\tNotes: preserve indentation.\r\n\r\n- Keep this list.\r\n",
        "## Requirements\n\n1. Preserve order.\n2. Return JSON only.\n",
        "  Context: first line\n\tsecond line\r\n\r\nFinal line.  ",
    ],
    ids=("crlf-list", "markdown-numbered-list", "mixed-whitespace"),
)
def test_formatted_noop_inputs_return_exact_original(prompt):
    result = analyze_prompt_detailed(prompt, MODEL)

    assert not result.optimization_accepted
    assert result.final.optimized_prompt == prompt
    assert result.final.tokens_saved == 0


@pytest.mark.parametrize("clause_count", [299, 300, 301])
def test_clause_guard_is_predictable_at_and_beyond_boundary(clause_count):
    clause = "Explain database indexing."
    prompt = " ".join([clause] * clause_count)
    result = analyze_prompt_detailed(prompt, MODEL)

    if clause_count <= 300:
        assert result.optimization_accepted
        assert result.final.optimized_prompt.count("Explain database indexing") == 1
        assert result.final.tokens_saved > 0
    else:
        # The existing guard intentionally declines pairwise duplicate work.
        # The public API must then use the exact original as its no-op result.
        assert not result.optimization_accepted
        assert result.final.optimized_prompt == prompt
        assert result.final.tokens_saved == 0


@pytest.mark.parametrize(
    "prompt,required",
    [
        (
            "## Global\nUse UTC timestamps.\n\n## Import exception\n"
            "For imported legacy rows, retain their original timezone.\n",
            ("Use UTC timestamps", "retain their original timezone"),
        ),
        (
            "### API contract\nReturn JSON for /v1/users.\n\n"
            "### Error contract\nReturn CSV diagnostics for /v1/errors.\n",
            ("JSON", "/v1/users", "CSV", "/v1/errors"),
        ),
        (
            "Use exactly 5 workers for image jobs.\n"
            "Use exactly 10 workers for video jobs.\n",
            ("exactly 5 workers", "exactly 10 workers"),
        ),
    ],
    ids=("section-scope", "different-formats-and-endpoints", "different-values"),
)
def test_scoped_or_similar_requirements_remain_distinct(prompt, required):
    result = analyze_prompt_detailed(prompt, MODEL)
    output = result.final.optimized_prompt

    for phrase in required:
        assert phrase.lower() in output.lower()


@pytest.mark.parametrize(
    "prompt",
    [
        "Include security details. Do not include security details.",
        "Return exactly 5 records. Return exactly 10 records.",
        "Return JSON only. Return XML only.",
        "Validate the input before writing the report. "
        "Write the report before validating the input.",
        "If the account is active, permit access. "
        "Unless the account is active, deny access.",
    ],
    ids=("opposite-polarity", "contradictory-counts", "conflicting-formats", "conflicting-order", "condition-exception"),
)
def test_contradictions_and_logical_distinctions_are_not_resolved(prompt):
    result = analyze_prompt_detailed(prompt, MODEL)

    # These short prompts have no safe verbosity or duplicate reduction.
    assert not result.optimization_accepted
    assert result.final.optimized_prompt == prompt
    assert result.final.tokens_saved == 0


def test_technical_literals_survive_safe_duplicate_removal():
    prompt = (
        "Please summarize the report. Please summarize the report.\n"
        "Keep src/api/user_route.py and call "
        "https://api.example.test/v2/users with POST.\n"
        "Use get_user_by_id(user_id), preserve client_id, and keep this code:\n"
        "```python\nreturn {\"status\": \"ok\"}\n```"
    )

    result = analyze_prompt_detailed(prompt, MODEL)
    output = result.final.optimized_prompt

    assert result.optimization_accepted
    assert output.lower().count("summarize the report") == 1
    for literal in (
        "src/api/user_route.py",
        "https://api.example.test/v2/users",
        "get_user_by_id(user_id)",
        "client_id",
        'return {"status": "ok"}',
    ):
        assert literal in output


def test_very_large_multisection_input_completes_without_losing_sections():
    sections = [
        f"## Section {index}\n"
        f"For section {index}, preserve requirement R{index:04d} and value {index}."
        for index in range(1, 301)
    ]
    prompt = "\n\n".join(sections)

    result = analyze_prompt_detailed(prompt, MODEL)

    assert not result.optimization_accepted
    assert result.final.optimized_prompt == prompt
    assert result.final.tokens_saved == 0
    assert len(prompt) > 20_000


def test_512k_character_prompt_returns_safe_original_fallback():
    paragraph = "The reference documentation describes stable record processing. "
    prompt = "Context: " + paragraph * (524_288 // len(paragraph) + 1)
    prompt = prompt[:524_288]

    result = analyze_prompt_detailed(prompt, MODEL)

    assert len(prompt) == 524_288
    assert not result.optimization_accepted
    assert result.final.optimized_prompt == prompt
    assert result.final.tokens_saved == 0


def test_semantic_encoding_failure_falls_back_to_lexical_public_pipeline(monkeypatch):
    semantic = importlib.import_module("nlp_engine.semantic_similarity")

    class BrokenModel:
        def encode(self, *_args, **_kwargs):
            raise RuntimeError("local model encode failure")

    monkeypatch.setenv(semantic.ENABLE_ENV, "true")
    monkeypatch.setattr(semantic, "get_semantic_model", lambda: BrokenModel())

    prompt = "Please summarize the report. Please summarize the report."
    result = analyze_prompt_detailed(prompt, MODEL)

    assert result.optimization_accepted
    assert result.final.optimized_prompt.lower().count("summarize the report") == 1
    assert result.final.tokens_saved > 0


def test_repeated_public_analysis_is_deterministic():
    prompt = (
        "Please summarize the report. Please summarize the report.\n"
        "Return exactly 3 recommendations in JSON."
    )

    first = analyze_prompt_detailed(prompt, MODEL)
    second = analyze_prompt_detailed(prompt, MODEL)

    assert first.final.model_dump() == second.final.model_dump()
    assert first.validation.model_dump() == second.validation.model_dump()
    assert first.optimization_accepted == second.optimization_accepted
