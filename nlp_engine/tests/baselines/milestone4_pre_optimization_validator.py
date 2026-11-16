
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
  - Explicit sequence and ordinal workflow preservation

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


def _sequence_relations(text: str) -> List[tuple]:
    """
    Extract explicit ordering relationships from text.

    Each result contains:
        (left_action_stems, right_action_stems, relation)

    relation:
        "left_before_right"
        "right_before_left"

    Only explicit markers are considered. This avoids guessing the order
    of unrelated instructions.
    """

    marker_pattern = re.compile(
        r"\b(prior\s+to|before|after|followed\s+by)\b",
        re.IGNORECASE,
    )

    relations = []

    for match in marker_pattern.finditer(text):
        left_boundary = max(
            text.rfind(".", 0, match.start()),
            text.rfind(";", 0, match.start()),
            text.rfind("\n", 0, match.start()),
        )

        right_candidates = [
            pos
            for pos in (
                text.find(".", match.end()),
                text.find(";", match.end()),
                text.find("\n", match.end()),
            )
            if pos != -1
        ]

        right_boundary = (
            min(right_candidates)
            if right_candidates
            else len(text)
        )

        left_text = text[left_boundary + 1:match.start()]
        right_text = text[match.end():right_boundary]

        left_stems = content_stems(left_text)
        right_stems = content_stems(right_text)

        if len(left_stems) < 2 or len(right_stems) < 2:
            continue

        marker = match.group(1).lower()

        if marker == "after":
            relation = "right_before_left"
        else:
            relation = "left_before_right"

        relations.append(
            (left_stems, right_stems, relation)
        )

    return relations


def _phrase_match_score(first: Set[str], second: Set[str]) -> float:
    """
    Measure how much two action phrases overlap.

    Dividing by the smaller set allows a phrase to gain harmless extra
    descriptive words without losing its identity.
    """
    if not first or not second:
        return 0.0

    denominator = min(len(first), len(second))

    if denominator == 0:
        return 0.0

    return len(first & second) / denominator


def _ordinal_actions(text: str) -> List[str]:
    """
    Extract action-head stems from explicitly ordered workflow steps.

    Recognized markers include:
        First, Firstly, Second, Secondly, Third, Thirdly,
        Then, Next, Finally, Lastly.

    This is a surface-level detector, not a general natural-language
    workflow parser.
    """

    marker_pattern = re.compile(
        r"^\s*(?:"
        r"first(?:ly)?|"
        r"second(?:ly)?|"
        r"third(?:ly)?|"
        r"fourth(?:ly)?|"
        r"fifth(?:ly)?|"
        r"then|next|finally|lastly"
        r")\b[\s,:-]*",
        re.IGNORECASE,
    )

    # Split at sentence and clause boundaries.
    chunks = re.split(r"(?<=[.!?;])\s+|\n+", text)

    actions: List[str] = []

    for chunk in chunks:
        match = marker_pattern.match(chunk)

        if not match:
            continue

        action_text = chunk[match.end():].strip()

        if not action_text:
            continue

        # Identify the first meaningful word in the action phrase.
        # content_stems handles the project's existing normalization.
        words = re.findall(
            r"[A-Za-z][A-Za-z0-9_]*",
            action_text,
        )

        action_head = None

        for word in words:
            stems = content_stems(word)

            if stems:
                action_head = next(iter(stems))
                break

        if action_head:
            actions.append(action_head)

    return actions


def _ordinal_order_preserved(
    original: str,
    optimized: str,
) -> bool:
    """
    Check whether recognizable explicitly ordered actions remain in order.

    The comparison uses action-head stems from marked workflow steps.
    It rejects a candidate when at least two recognizable actions have
    exchanged their relative positions.

    This does not detect every possible workflow rewrite. In particular,
    it cannot reliably understand unmarked or heavily paraphrased steps.
    """

    original_actions = _ordinal_actions(original)

    if len(original_actions) < 2:
        return True

    optimized_actions = _ordinal_actions(optimized)

    if len(optimized_actions) < 2:
        return True

    # Match original action heads to distinct optimized positions.
    # Missing actions are left to the other validation checks.
    matched_positions: List[int] = []
    used_positions: Set[int] = set()

    for original_action in original_actions:
        for position, optimized_action in enumerate(optimized_actions):
            if position in used_positions:
                continue

            if original_action == optimized_action:
                matched_positions.append(position)
                used_positions.add(position)
                break

    # At least two matched actions are needed to establish an ordering.
    if len(matched_positions) < 2:
        return True

    return matched_positions == sorted(matched_positions)


def _sequence_order_preserved(
    original: str,
    optimized: str,
) -> bool:
    """
    Check whether recognizable explicit ordering relationships survive.

    Reject:
    - Reversing the two recognizable actions.
    - Changing an action from before another action to after it.
    - Reordering recognizable ordinal workflow steps.

    This is deliberately conservative and does not claim to understand
    arbitrary natural-language workflows.
    """

    # Check ordinal workflow markers independently.
    if not _ordinal_order_preserved(original, optimized):
        return False

    original_relations = _sequence_relations(original)

    if not original_relations:
        return True

    optimized_relations = _sequence_relations(optimized)

    if not optimized_relations:
        return True

    minimum_match = 0.5

    for orig_left, orig_right, orig_relation in original_relations:
        for opt_left, opt_right, opt_relation in optimized_relations:
            direct_left = _phrase_match_score(
                orig_left,
                opt_left,
            )
            direct_right = _phrase_match_score(
                orig_right,
                opt_right,
            )

            reversed_left = _phrase_match_score(
                orig_left,
                opt_right,
            )
            reversed_right = _phrase_match_score(
                orig_right,
                opt_left,
            )

            direct_match = (
                direct_left >= minimum_match
                and direct_right >= minimum_match
            )

            reversed_match = (
                reversed_left >= minimum_match
                and reversed_right >= minimum_match
            )

            if direct_match and orig_relation != opt_relation:
                return False

            if reversed_match:
                return False

    return True


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

    # 6. Explicit sequence preservation ---------------------------------------

    if not _sequence_order_preserved(
        core_original,
        optimized,
    ):
        reasons.append(
            "Explicit instruction sequence or ordering changed"
        )

    # 7. Keyword coverage (soft) -----------------------------------------------

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

    # 8. Lexical similarity (soft) ---------------------------------------------

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
