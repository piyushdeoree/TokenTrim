"""
benchmark_runner.py - semantic and redundancy evaluation for TokenTrim.

Run from the project root:

    python -m nlp_engine.tests.benchmark_runner

Reads:
    nlp_engine/tests/evaluation_dataset.json

Writes:
    nlp_engine/tests/semantic_benchmark_results.md

This is a focused redundancy-engine benchmark. It constructs instruction
segments from the dataset sentences and evaluates find_pairs() and
select_removals(). It does not run the complete analyzer pipeline.
"""

from __future__ import annotations

import copy
import json
import re
import time
from pathlib import Path
from typing import Any

from nlp_engine.redundancy import (
    Segment,
    build_clauses,
    find_pairs,
    select_removals,
)
from nlp_engine.semantic_similarity import semantic_model_enabled


TEST_DIR = Path(__file__).resolve().parent
DATASET_PATH = TEST_DIR / "evaluation_dataset.json"
RESULT_PATH = TEST_DIR / "semantic_benchmark_results.md"

REMOVAL_RELATIONS = {"equal", "i_in_j", "j_in_i"}

CONSTRAINT_PATTERN = re.compile(
    r"\b(?:exactly|at least|at most|below|above|under|"
    r"over|less than|more than|no more than|no less than|"
    r"only|all|every|each|except|minimum|maximum)\b",
    re.IGNORECASE,
)


def split_sentences(text: str) -> list[str]:
    """Split a dataset prompt into sentence-like segments."""
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", text.strip())
        if part.strip()
    ]


def classify_segment(text: str) -> str:
    """
    Assign a basic segment role for this focused benchmark.

    Numeric and scope-limiting language is classified as a constraint.
    Other dataset sentences are treated as instructions.

    This is deliberately not a replacement for the production analyzer's
    segment classification.
    """
    if CONSTRAINT_PATTERN.search(text):
        return "constraint"

    return "instruction"


def create_clauses(prompt: str):
    """Convert dataset sentences into comparable engine clauses."""
    segments = []

    for sentence in split_sentences(prompt):
        segments.append(
            Segment(
                text=sentence,
                kind=classify_segment(sentence),
            )
        )

    return build_clauses(segments)


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one dataset case."""
    started = time.perf_counter()

    clauses = create_clauses(case["text"])

    # Detect relationships before removal.
    pairs = find_pairs(clauses)

    # Use a separate copy because select_removals mutates Clause objects.
    removal_clauses = copy.deepcopy(clauses)
    removals = select_removals(removal_clauses)

    elapsed_ms = (time.perf_counter() - started) * 1000

    removal_pairs = [
        pair for pair in pairs
        if pair.relation in REMOVAL_RELATIONS
    ]

    similar_pairs = [
        pair for pair in pairs
        if pair.relation == "similar"
    ]

    expected = case["expected"]

    if expected == "duplicate_detected":
        passed = len(removals) > 0
        actual = "duplicate_detected" if passed else "not_detected"

    elif expected == "similarity_detected":
        passed = len(similar_pairs) > 0
        actual = "similarity_detected" if passed else "not_detected"

    elif expected == "preserve_both":
        passed = len(removals) == 0
        actual = "preserved" if passed else "incorrect_removal"

    else:
        raise ValueError(
            f"Unknown expected result {expected!r} "
            f"for case {case.get('id')!r}"
        )

    pair_details = []

    for pair in pairs:
        pair_details.append(
            f"{pair.i}-{pair.j}: {pair.relation} "
            f"(score={pair.sim:.3f})"
        )

    return {
        "id": case["id"],
        "category": case["category"],
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "clause_count": len(clauses),
        "pair_count": len(pairs),
        "removal_count": len(removals),
        "similarity_count": len(similar_pairs),
        "removal_pairs": len(removal_pairs),
        "elapsed_ms": elapsed_ms,
        "pair_details": pair_details,
    }


def build_report(results: list[dict[str, Any]]) -> str:
    """Build a Markdown benchmark report."""
    total = len(results)
    passed = sum(result["passed"] for result in results)
    failed = total - passed

    accuracy = (passed / total * 100) if total else 0.0

    lines = [
        "# TokenTrim Semantic Benchmark",
        "",
        f"- Dataset: `{DATASET_PATH.name}`",
        f"- Total cases: {total}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Pass rate: {accuracy:.1f}%",
        (
            "- Pretrained semantic model enabled: "
            f"`{semantic_model_enabled()}`"
        ),
        "",
        "## Case results",
        "",
        "| ID | Category | Expected | Actual | Result | Clauses | Pairs | Removals | Time (ms) |",
        "|---|---|---|---|:---:|---:|---:|---:|---:|",
    ]

    for result in results:
        lines.append(
            f"| {result['id']} "
            f"| {result['category']} "
            f"| {result['expected']} "
            f"| {result['actual']} "
            f"| {'PASS' if result['passed'] else 'FAIL'} "
            f"| {result['clause_count']} "
            f"| {result['pair_count']} "
            f"| {result['removal_count']} "
            f"| {result['elapsed_ms']:.2f} |"
        )

    lines.extend([
        "",
        "## Detected relationships",
        "",
    ])

    for result in results:
        lines.append(f"### {result['id']}")

        if result["pair_details"]:
            for detail in result["pair_details"]:
                lines.append(f"- {detail}")
        else:
            lines.append("- No pairs detected.")

        lines.append(
            f"- Expected: `{result['expected']}`; "
            f"actual: `{result['actual']}`."
        )
        lines.append("")

    # Category-level summary.
    categories = sorted({result["category"] for result in results})

    lines.extend([
        "## Category summary",
        "",
        "| Category | Passed | Total | Pass rate |",
        "|---|---:|---:|---:|",
    ])

    for category in categories:
        group = [
            result for result in results
            if result["category"] == category
        ]

        group_passed = sum(result["passed"] for result in group)
        group_total = len(group)
        group_rate = (
            group_passed / group_total * 100
            if group_total else 0.0
        )

        lines.append(
            f"| {category} | {group_passed} | "
            f"{group_total} | {group_rate:.1f}% |"
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
        "- `duplicate_detected`: at least one strict removal was selected.",
        "- `similarity_detected`: at least one pair was classified as similar.",
        "- `preserve_both`: no clause was selected for removal.",
        "- Similarity relationships alone must never cause removal.",
        "",
        "This is a small, manually authored evaluation dataset. Its pass "
        "rate is not a general measure of NLP accuracy.",
        "",
        "The benchmark constructs basic instruction/constraint segments "
        "itself. It does not measure the complete production segmentation "
        "pipeline or token savings.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    with DATASET_PATH.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list):
        raise ValueError("The evaluation dataset must be a JSON list.")

    results = []

    print("=" * 65)
    print("TOKENTRIM SEMANTIC BENCHMARK")
    print("=" * 65)
    print(f"Dataset cases: {len(dataset)}")
    print(
        "Pretrained semantic model enabled:",
        semantic_model_enabled(),
    )
    print()

    for index, case in enumerate(dataset, start=1):
        result = evaluate_case(case)
        results.append(result)

        status = "PASS" if result["passed"] else "FAIL"

        print(
            f"[{index:02d}/{len(dataset):02d}] "
            f"{case['id']:<25} {status}"
        )

    report = build_report(results)
    RESULT_PATH.write_text(report, encoding="utf-8")

    passed = sum(result["passed"] for result in results)
    failed = len(results) - passed

    print()
    print("=" * 65)
    print(f"TOTAL: {passed} passed, {failed} failed")
    print(f"RESULTS: {RESULT_PATH}")
    print("=" * 65)


if __name__ == "__main__":
    main()
