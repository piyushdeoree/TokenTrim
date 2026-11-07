
"""
validator.py - safety check for an optimized prompt.

Compares ORIGINAL vs OPTIMIZED and rejects the optimization when important
information appears to be lost.

Hard checks:
  - Numbers
  - Protected spans
  - Output format
  - Named items
  - Constraint coverage and negation preservation

Soft checks:
  - Keyword coverage
  - TF-IDF lexical similarity

These are surface-level checks. A passing result means "no detectable loss",
NOT proven semantic equivalence.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from . import config
from .models import ValidationResult
from .textutils import (
    apply_rewrites,
    content_stems,
    extract_numbers,
    is_negated,
    prepare_prompt,
    render_segments,
)


def _entities(text: str) -> Set[str]:
    """Find names, acronyms, camelCase and snake_case identifiers."""
    found: Set[str] = set()

    for seg in prepare_prompt(text).segments:
        toks = re.findall(r"[A-Za-z][A-Za-z0-9_]*", seg.text)

        for k, tok in enumerate(toks):
            if tok.upper().startswith("QZPH") or len(tok) < 2:
                continue

            special = (
                tok.isupper()
                or "_" in tok
                or re.search(r"[a-z][A-Z]", tok) is not None
            )

            if special or (k > 0 and tok[0].isupper()):
                found.add(tok)

    return found


def _format_keywords(text: str) -> Set[str]:
    """Extract required output-format keywords."""
    low = text.lower()

    return {
        k.replace("-", " ")
        for k in config.FORMAT_KEYWORDS
        if re.search(r"\b" + re.escape(k) + r"\b", low)
    }


def _lexical_similarity(a: str, b: str) -> float:
    """Calculate TF-IDF cosine similarity."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    docs = [
        " ".join(sorted(content_stems(a))),
        " ".join(sorted(content_stems(b))),
    ]

    if not docs[0] or not docs[1]:
        return 0.0

    try:
        vectorizer = TfidfVectorizer(
            token_pattern=r"\S+",
            lowercase=False,
        )
        X = vectorizer.fit_transform(docs)
    except ValueError:
        return 0.0

    return float(cosine_similarity(X[0], X[1])[0][0])


def _best_constraint_coverage(
    original_constraint: str,
    optimized_segments: List[str],
) -> float:
    """
    Find the best local match for one original constraint.

    Important:
    - A constraint must match an individual optimized segment.
    - Its negation status must also match that segment.
    - Negation elsewhere in the optimized prompt cannot satisfy it.

    Returns the highest coverage score between 0.0 and 1.0.
    """

    original_stems = {
        stem
        for stem in content_stems(original_constraint)
        if not stem.startswith("qzph")
    }

    if not original_stems:
        return 1.0

    original_negated = is_negated(original_constraint)
    best_coverage = 0.0

    for candidate in optimized_segments:
        candidate_negated = is_negated(candidate)

        # Do not allow a positive instruction to become negative,
        # or a negative instruction to become positive.
        if original_negated != candidate_negated:
            continue

        candidate_stems = {
            stem
            for stem in content_stems(candidate)
            if not stem.startswith("qzph")
        }

        if not candidate_stems:
            continue

        overlap = len(original_stems & candidate_stems)
        coverage = overlap / len(original_stems)

        best_coverage = max(best_coverage, coverage)

    return best_coverage


def validate_optimization(
    original: str,
    optimized: str,
) -> ValidationResult:
    """Validate an optimized prompt against its original version."""

    reasons: List[str] = []
    metrics: Dict[str, float] = {}

    original = original.strip()
    optimized = optimized.strip()

    if not optimized:
        return ValidationResult(
            is_valid=False,
            reasons=["Optimized prompt is empty"],
            metrics={},
        )

    prep = prepare_prompt(original)

    persona_idx = {
        i
        for i, seg in enumerate(prep.segments)
        if seg.kind == "persona" and not seg.locked
    }

    # Remove generic persona statements from content comparisons.
    core_masked = render_segments([
        seg
        for i, seg in enumerate(prep.segments)
        if i not in persona_idx
    ])

    core_original = prep.unmask(core_masked)

    # Prepare optimized segments for local constraint matching.
    optimized_prepared = prepare_prompt(optimized)

    optimized_segments = [
        optimized_prepared.unmask(seg.text)
        for seg in optimized_prepared.segments
        if seg.text.strip()
    ]

    # 1. Numbers ---------------------------------------------------------------

    orig_nums = extract_numbers(core_original)
    opt_nums = extract_numbers(optimized)

    missing = sorted(orig_nums - opt_nums)

    metrics["number_coverage"] = (
        1.0
        if not orig_nums
        else 1 - len(missing) / len(orig_nums)
    )

    if missing:
        reasons.append(
            f"Numbers lost: {', '.join(missing)}"
        )

    # 2. Protected spans -------------------------------------------------------

    lost_spans = [
        frag
        for frag in prep.mapping.values()
        if frag not in optimized
    ]

    metrics["protected_span_coverage"] = (
        1.0
        if not prep.mapping
        else 1 - len(lost_spans) / len(prep.mapping)
    )

    if lost_spans:
        reasons.append(
            "Code/URL/quoted/JSON content changed or lost: "
            + "; ".join(f[:40] for f in lost_spans[:3])
        )

    # 3. Output format ---------------------------------------------------------

    orig_fmt = _format_keywords(core_original)
    opt_fmt = _format_keywords(optimized)

    lost_fmt = sorted(orig_fmt - opt_fmt)

    metrics["format_keyword_coverage"] = (
        1.0
        if not orig_fmt
        else 1 - len(lost_fmt) / len(orig_fmt)
    )

    if lost_fmt:
        reasons.append(
            f"Output-format requirement lost: {', '.join(lost_fmt)}"
        )

    # 4. Named items -----------------------------------------------------------

    orig_ent = _entities(core_original)

    opt_ent = _entities(optimized) | {
        tok
        for tok in re.findall(
            r"[A-Za-z][A-Za-z0-9_]*",
            optimized,
        )
    }

    lost_ent = sorted(orig_ent - opt_ent)

    metrics["entity_coverage"] = (
        1.0
        if not orig_ent
        else 1 - len(lost_ent) / len(orig_ent)
    )

    if lost_ent:
        reasons.append(
            f"Named items lost: {', '.join(lost_ent[:5])}"
        )

    # 5. Constraints -----------------------------------------------------------

    checked = 0
    bad: List[str] = []
    constraint_coverages: List[float] = []

    for i, seg in enumerate(prep.segments):

        # Ignore removable generic persona statements.
        if i in persona_idx:
            continue

        if seg.locked:
            continue

        if seg.kind not in (
            "constraint",
            "instruction",
            "question",
            "role",
        ):
            continue

        # Check explicit constraints, negated instructions,
        # and other instructions classified as constraints.
        if (
            seg.kind != "constraint"
            and not (
                config.CONSTRAINT_RE.search(seg.text)
                or is_negated(seg.text)
            )
        ):
            continue

        original_constraint = prep.unmask(seg.text)

        stems = {
            stem
            for stem in content_stems(original_constraint)
            if not stem.startswith("qzph")
        }

        if not stems:
            continue

        checked += 1

        # Compare this constraint against individual optimized segments.
        coverage = _best_constraint_coverage(
            original_constraint,
            optimized_segments,
        )

        constraint_coverages.append(coverage)

        if coverage < config.CONSTRAINT_COVERAGE_MIN:
            bad.append(original_constraint[:50])

    metrics["constraints_checked"] = float(checked)

    metrics["constraint_coverage"] = (
        1.0
        if not checked
        else 1 - len(bad) / checked
    )

    if bad:
        reasons.append(
            "Constraint(s) possibly lost: "
            + "; ".join(bad[:3])
        )

    # 6. Keyword coverage (soft) -----------------------------------------------

    opt_stems = content_stems(optimized)

    ignorable: Set[str] = set()

    for seg in prep.segments:
        if seg.locked or seg.kind not in (
            "instruction",
            "constraint",
            "question",
        ):
            continue

        _, events = apply_rewrites(seg.text)

        for event in events:
            ignorable |= (
                content_stems(event.before)
                - content_stems(event.after)
            )

    orig_stems = {
        stem
        for stem in content_stems(core_masked)
        if not stem.startswith("qzph")
    } - ignorable

    kw_cov = (
        1.0
        if not orig_stems
        else len(orig_stems & opt_stems) / len(orig_stems)
    )

    metrics["keyword_coverage"] = round(kw_cov, 4)

    if kw_cov < config.KEYWORD_COVERAGE_MIN:
        reasons.append(
            f"Keyword coverage {kw_cov:.0%} is below "
            f"{config.KEYWORD_COVERAGE_MIN:.0%}"
        )

    # 7. Lexical similarity (soft) ---------------------------------------------

    sim = _lexical_similarity(
        core_original,
        optimized,
    )

    metrics["lexical_similarity"] = round(sim, 4)

    if sim < config.MIN_LEXICAL_SIMILARITY:
        reasons.append(
            f"Lexical similarity {sim:.2f} is below "
            f"{config.MIN_LEXICAL_SIMILARITY}"
        )

    # Normalize metrics for API compatibility.
    for key in list(metrics):
        metrics[key] = round(float(metrics[key]), 4)

    return ValidationResult(
        is_valid=not reasons,
        reasons=reasons,
        metrics=metrics,
    )
