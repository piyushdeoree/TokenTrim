"""Evaluate curated realistic prompts through the public NLP API.

Run from the repository root:

    python -m nlp_engine.tests.run_realistic_evaluation

The runner uses a fixed unknown model name, so token savings are explicitly
labelled heuristic estimates and do not depend on downloaded tokenizer files.
The optional sentence model is disabled for this evaluation to keep results
reproducible across machines.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import patch

from nlp_engine import analyze_prompt_detailed, tokenizer_info, validate_optimization


TEST_DIR = Path(__file__).resolve().parent
DATASET_PATH = TEST_DIR / "realistic_evaluation_dataset.json"
RESULT_PATH = TEST_DIR / "realistic_evaluation_results.md"
EVALUATION_MODEL = "tokentrim-evaluation-estimate"
EXPECTED_BEHAVIORS = {
    "accept_safe_optimization",
    "leave_unchanged",
    "reject_unsafe_candidate",
}


def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    """Load and minimally validate the reproducible evaluation corpus."""
    with path.open("r", encoding="utf-8") as dataset_file:
        dataset = json.load(dataset_file)

    if not isinstance(dataset, list) or not dataset:
        raise ValueError("The realistic evaluation dataset must be a non-empty JSON list")

    ids = set()
    required_keys = {
        "id", "category", "expected_behavior", "description", "prompt",
        "must_preserve",
    }

    for case in dataset:
        if not isinstance(case, dict) or not required_keys <= case.keys():
            raise ValueError(f"Evaluation case is missing required fields: {case!r}")
        if case["id"] in ids:
            raise ValueError(f"Duplicate evaluation case id: {case['id']!r}")
        ids.add(case["id"])

        if case["expected_behavior"] not in EXPECTED_BEHAVIORS:
            raise ValueError(
                f"Unsupported expected behavior in case {case['id']!r}: "
                f"{case['expected_behavior']!r}"
            )
        if not isinstance(case["prompt"], str) or not case["prompt"].strip():
            raise ValueError(f"Case {case['id']!r} has an empty prompt")
        if not isinstance(case["must_preserve"], list):
            raise ValueError(f"Case {case['id']!r} must_preserve must be a list")
        if case.get("added_in") not in (None, "milestone_3"):
            raise ValueError(f"Case {case['id']!r} has an unsupported added_in value")
        if "scenarios" in case and (
            not isinstance(case["scenarios"], list)
            or not case["scenarios"]
            or not all(isinstance(label, str) and label.strip() for label in case["scenarios"])
        ):
            raise ValueError(f"Case {case['id']!r} scenarios must be a non-empty list of labels")
        if (
            case["expected_behavior"] == "reject_unsafe_candidate"
            and not isinstance(case.get("llm_candidate"), str)
        ):
            raise ValueError(f"Case {case['id']!r} needs an llm_candidate")

    return dataset


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single case through the public detailed analysis and validator APIs."""
    prompt = case["prompt"]
    llm_candidate = case.get("llm_candidate")
    rewriter = (lambda _request: llm_candidate) if llm_candidate is not None else None

    result = analyze_prompt_detailed(
        prompt,
        model=EVALUATION_MODEL,
        llm_rewriter=rewriter,
    )

    llm_validation = (
        validate_optimization(prompt, llm_candidate)
        if llm_candidate is not None else None
    )

    final_prompt = result.final.optimized_prompt
    missing_required = [
        phrase for phrase in case["must_preserve"]
        if phrase.casefold() not in final_prompt.casefold()
    ]
    fallback_used = final_prompt == prompt

    if result.optimization_accepted:
        actual_behavior = "optimized"
    elif (
        llm_validation is not None
        and not llm_validation.is_valid
        and fallback_used
    ):
        actual_behavior = "unsafe_candidate_rejected"
    elif fallback_used:
        actual_behavior = "left_unchanged"
    else:
        actual_behavior = "fallback_changed_input"

    expected = case["expected_behavior"]
    false_removal = bool(result.optimization_accepted and missing_required)
    unexpected_optimization = bool(
        expected in {"leave_unchanged", "reject_unsafe_candidate"}
        and result.optimization_accepted
    )
    missed_opportunity = bool(
        expected == "accept_safe_optimization"
        and not (
            result.optimization_accepted
            and result.validation.is_valid
            and result.final.tokens_saved > 0
            and not missing_required
        )
    )

    if expected == "accept_safe_optimization":
        behavior_correct = (
            result.optimization_accepted
            and result.validation.is_valid
            and result.final.tokens_saved > 0
            and not missing_required
        )
    elif expected == "leave_unchanged":
        behavior_correct = fallback_used and not result.optimization_accepted
    else:
        behavior_correct = (
            llm_validation is not None
            and not llm_validation.is_valid
            and fallback_used
            and not result.optimization_accepted
        )

    return {
        "id": case["id"],
        "category": case["category"],
        "description": case["description"],
        "added_in": case.get("added_in"),
        "scenarios": case.get("scenarios", []),
        "expected_behavior": expected,
        "actual_behavior": actual_behavior,
        "behavior_correct": bool(behavior_correct),
        "original_prompt": prompt,
        "llm_candidate": llm_candidate,
        "final_prompt": final_prompt,
        "detected_issue_types": [issue.type for issue in result.issues],
        "candidate_changes": list(result.candidate.changes),
        "pipeline_validation": result.validation.model_dump(),
        "llm_candidate_validation": (
            llm_validation.model_dump() if llm_validation is not None else None
        ),
        "optimization_accepted": result.optimization_accepted,
        "fallback_used": fallback_used,
        "fallback_reason": (
            result.final.changes[0]
            if fallback_used and result.final.changes else None
        ),
        "original_tokens": result.final.original_tokens,
        "final_tokens": result.final.optimized_tokens,
        "tokens_saved": result.final.tokens_saved,
        "reduction_percentage": result.final.reduction_percentage,
        "missing_required_phrases": missing_required,
        "false_removal": false_removal,
        "unexpected_optimization": unexpected_optimization,
        "missed_opportunity": missed_opportunity,
        "exception": None,
    }


def _evaluation_exception(case: dict[str, Any], exc: Exception) -> dict[str, Any]:
    """Record an isolated case failure without treating it as engine fallback."""
    expected = case["expected_behavior"]
    return {
        "id": case["id"],
        "category": case["category"],
        "description": case["description"],
        "added_in": case.get("added_in"),
        "scenarios": case.get("scenarios", []),
        "expected_behavior": expected,
        "actual_behavior": "evaluation_exception",
        "behavior_correct": False,
        "original_prompt": case["prompt"],
        "llm_candidate": case.get("llm_candidate"),
        "final_prompt": None,
        "detected_issue_types": [],
        "candidate_changes": [],
        "pipeline_validation": {
            "is_valid": False,
            "reasons": ["Evaluation did not produce a pipeline result"],
            "metrics": {},
        },
        "llm_candidate_validation": None,
        "optimization_accepted": None,
        "fallback_used": None,
        "fallback_reason": None,
        "original_tokens": None,
        "final_tokens": None,
        "tokens_saved": None,
        "reduction_percentage": None,
        "missing_required_phrases": list(case["must_preserve"]),
        "false_removal": False,
        "unexpected_optimization": False,
        "missed_opportunity": expected == "accept_safe_optimization",
        "exception": f"{type(exc).__name__}: {exc}",
    }


def _render_case(result: dict[str, Any]) -> list[str]:
    pipeline_validation = result["pipeline_validation"]
    llm_validation = result["llm_candidate_validation"]
    final_prompt = result["final_prompt"]
    lines = [
        f"### {result['id']} — {result['category']}",
        "",
        f"- Cohort: `{'new in milestone 3' if result['added_in'] else 'original 20-case baseline'}`",
        f"- Scenarios: `{', '.join(result['scenarios']) or 'baseline case; no scenario tags'}`",
        f"- Rationale: {result['description']}",
        "",
        f"- Expected: `{result['expected_behavior']}`",
        f"- Actual: `{result['actual_behavior']}`",
        f"- Case result: `{'PASS' if result['behavior_correct'] else 'FAIL'}`",
        f"- Pipeline candidate validation: `{pipeline_validation['is_valid']}`",
        f"- LLM candidate validation: `{llm_validation['is_valid'] if llm_validation else 'not applicable'}`",
        f"- Optimization accepted: `{result['optimization_accepted']}`",
        f"- Detected issue types: `{result['detected_issue_types']}`",
        f"- Candidate changes: `{result['candidate_changes']}`",
        f"- Fallback used: `{result['fallback_used']}`",
        f"- Fallback reason: `{result['fallback_reason'] or 'not applicable'}`",
        f"- Tokens: {result['original_tokens']} → {result['final_tokens']} ",
        f"- Estimated tokens saved: **{result['tokens_saved']}**",
        f"- Reduction percentage: **{result['reduction_percentage']}%**",
        f"- False removal: `{result['false_removal']}`",
        f"- Unexpected optimization: `{result['unexpected_optimization']}`",
        f"- Missed optimization opportunity: `{result['missed_opportunity']}`",
        f"- Missing required phrases: `{result['missing_required_phrases']}`",
        "",
        "Original prompt:",
        "",
        "````text",
        result["original_prompt"],
        "````",
        "",
        "Final prompt:",
        "",
        "````text",
        final_prompt if final_prompt is not None else "[No pipeline result: see exception below]",
        "````",
        "",
    ]

    if result["llm_candidate"] is not None:
        lines.extend([
            "Injected LLM candidate:",
            "",
            "````text",
            result["llm_candidate"],
            "````",
            "",
        ])

    if pipeline_validation["reasons"]:
        lines.extend(["Pipeline validation reasons:", ""])
        lines.extend(f"- {reason}" for reason in pipeline_validation["reasons"])
        lines.append("")

    if llm_validation and llm_validation["reasons"]:
        lines.extend(["Rejected LLM candidate reasons:", ""])
        lines.extend(f"- {reason}" for reason in llm_validation["reasons"])
        lines.append("")

    if result["exception"]:
        lines.extend(["Evaluation exception:", "", f"- {result['exception']}", ""])

    return lines


def build_report(results: list[dict[str, Any]]) -> str:
    """Build the complete per-case report and separate safety/coverage counts."""
    categories = Counter(result["category"] for result in results)
    cohorts = Counter(
        "milestone_3_additions" if result["added_in"] else "original_baseline"
        for result in results
    )
    expected_outcomes = Counter(result["expected_behavior"] for result in results)
    scenarios = Counter(
        scenario
        for result in results
        for scenario in result["scenarios"]
    )
    expected_accepts = sum(
        r["expected_behavior"] == "accept_safe_optimization" for r in results
    )
    safe_accepted = sum(
        r["expected_behavior"] == "accept_safe_optimization"
        and r["optimization_accepted"]
        and r["pipeline_validation"]["is_valid"]
        and r["tokens_saved"] > 0
        and not r["missing_required_phrases"]
        for r in results
    )
    expected_unchanged = expected_outcomes["leave_unchanged"]
    expected_unsafe = expected_outcomes["reject_unsafe_candidate"]
    correctly_unchanged = sum(
        r["expected_behavior"] == "leave_unchanged"
        and r["fallback_used"]
        and not r["optimization_accepted"]
        for r in results
    )
    unsafe_rejected = sum(
        r["expected_behavior"] == "reject_unsafe_candidate"
        and r["llm_candidate_validation"] is not None
        and not r["llm_candidate_validation"]["is_valid"]
        and r["fallback_used"]
        and not r["optimization_accepted"]
        for r in results
    )
    false_removals = sum(r["false_removal"] for r in results)
    unexpected = sum(r["unexpected_optimization"] for r in results)
    missed = sum(r["missed_opportunity"] for r in results)
    exceptions = [r for r in results if r["exception"]]
    completed = [r for r in results if r["exception"] is None]
    total_original_tokens = sum(r["original_tokens"] for r in completed)
    total_final_tokens = sum(r["final_tokens"] for r in completed)
    total_saved = sum(r["tokens_saved"] for r in completed)
    aggregate_reduction = (
        round(100 * total_saved / total_original_tokens, 2)
        if total_original_tokens else 0.0
    )
    exact_original_fallbacks = sum(r["fallback_used"] is True for r in completed)
    failures = [r for r in results if not r["behavior_correct"]]
    info = tokenizer_info(EVALUATION_MODEL)

    lines = [
        "# TokenTrim Realistic NLP Evaluation",
        "",
        "## Reproducibility",
        "",
        "Run from the repository root with:",
        "",
        "```bash",
        "python -m nlp_engine.tests.run_realistic_evaluation",
        "```",
        "",
        f"- Dataset: `{DATASET_PATH.name}` ({len(results)} cases)",
        f"- Cohort counts: **{cohorts['original_baseline']}** original baseline; **{cohorts['milestone_3_additions']}** new in Milestone 3",
        f"- Token counter: `{info.method}`; exact: `{info.exact}`",
        "- Optional semantic model: disabled for this evaluation",
        "- LLM behavior: deterministic callback candidates from the dataset; no provider calls",
        "- Scope note: curated evaluation, not a general accuracy or semantic-equivalence claim",
        "",
        "## Results summary",
        "",
        f"- Expected outcomes: **{expected_outcomes['accept_safe_optimization']}** safe optimizations, **{expected_unchanged}** unchanged, **{expected_outcomes['reject_unsafe_candidate']}** unsafe candidates to reject",
        f"- Safe optimizations accepted: **{safe_accepted}/{expected_accepts}** expected opportunities",
        f"- Prompts correctly left unchanged: **{correctly_unchanged}/{expected_unchanged}** expected unchanged cases",
        f"- Unsafe LLM candidates rejected with fallback: **{unsafe_rejected}/{expected_unsafe}**",
        f"- False removals: **{false_removals}**",
        f"- Unexpected accepted optimizations on unchanged/rejection cases: **{unexpected}**",
        f"- Missed optimization opportunities: **{missed}**",
        f"- Exact-original fallbacks: **{exact_original_fallbacks}**",
        f"- Unexpected exceptions: **{len(exceptions)}**",
        f"- Aggregate estimated tokens: **{total_original_tokens}** original → **{total_final_tokens}** final",
        f"- Total estimated tokens saved: **{total_saved}**",
        f"- Aggregate estimated reduction: **{aggregate_reduction}%**",
        f"- Cases matching expected behavior: **{len(results) - len(failures)}/{len(results)}**",
        "",
        "False removals count accepted optimizations that omit one or more case-specific required phrases. "
        "Unexpected optimizations are reported separately because a changed output can retain all listed "
        "phrases and still violate a case designated unchanged. Missed opportunities count expected-safe "
        "cases that did not produce a valid, positive-saving optimization.",
        "",
        "### Cases by category",
        "",
        "| Category | Cases |",
        "|---|---:|",
    ]

    lines.extend(f"| {category} | {count} |" for category, count in sorted(categories.items()))
    lines.extend(["", "### Coverage by expected outcome", "", "| Expected outcome | Cases |", "|---|---:|"])
    lines.extend(
        f"| {outcome} | {count} |"
        for outcome, count in sorted(expected_outcomes.items())
    )
    lines.extend(["", "### Scenario coverage", "", "| Scenario | Cases |", "|---|---:|"])
    lines.extend(
        f"| {scenario} | {count} |"
        for scenario, count in sorted(scenarios.items())
    )
    lines.extend(["", "## Case results", ""])

    for result in results:
        lines.extend(_render_case(result))

    if failures:
        lines.extend(["## Failures and causes", ""])
        for result in failures:
            cause = []
            if result["exception"]:
                cause.append(f"evaluation exception: {result['exception']}")
            if result["missing_required_phrases"]:
                cause.append(
                    "required phrase(s) missing: "
                    + ", ".join(result["missing_required_phrases"])
                )
            if result["missed_opportunity"]:
                if not result["candidate_changes"]:
                    cause.append(
                        "no removable candidate was generated; detected issue types: "
                        + (", ".join(result["detected_issue_types"]) or "none")
                    )
                elif not result["pipeline_validation"]["is_valid"]:
                    cause.append(
                        "candidate rejected by validation: "
                        + "; ".join(result["pipeline_validation"]["reasons"])
                    )
                elif result["tokens_saved"] <= 0:
                    cause.append("candidate did not produce positive token savings")
                else:
                    cause.append("expected safe optimization was not accepted")
            if result["unexpected_optimization"]:
                cause.append("optimization accepted for a case expected to remain unchanged")
            if not cause:
                cause.append("actual behavior did not match the case expectation")
            lines.append(f"- `{result['id']}`: {'; '.join(cause)}.")
        lines.append("")
    else:
        lines.extend(["## Failures and causes", "", "- None in this curated run.", ""])

    return "\n".join(lines)


def run_evaluation() -> tuple[list[dict[str, Any]], str]:
    """Evaluate all cases using the default lexical path and write the report."""
    dataset = load_dataset()
    results = []

    # The dataset is designed to measure the deterministic default path.
    # Isolate it from a developer's optional model environment configuration.
    with patch("nlp_engine.redundancy.semantic_similarity_matrix", return_value=None):
        for case in dataset:
            try:
                results.append(evaluate_case(case))
            except Exception as exc:
                results.append(_evaluation_exception(case, exc))

    report = build_report(results)
    RESULT_PATH.write_text(report, encoding="utf-8")
    return results, report


def main() -> None:
    results, _ = run_evaluation()
    passed = sum(result["behavior_correct"] for result in results)
    print(f"Evaluated {len(results)} realistic prompts: {passed}/{len(results)} matched expectations")
    print(f"Results: {RESULT_PATH}")
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
