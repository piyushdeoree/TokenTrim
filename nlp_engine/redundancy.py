
"""
redundancy.py - detection of repeated / duplicated content.

Hybrid techniques:
  * clause extraction (sentence -> clauses split before instruction verbs)
  * original stem-set representation for conservative removal
  * similarity-only stem-set representation for paraphrase detection
  * TF-IDF-style binary-vector cosine similarity (scikit-learn)
  * optional pretrained sentence-embedding similarity
  * strict subsumption test for removal
  * word n-gram counting for repeated phrases

Important safety rule:
  Similarity is used for reporting only.
  Removal requires the existing strict subsumption test:
    - same clause kind
    - same polarity
    - compatible numbers
    - complete original-stem coverage
    - matching head verb for instructions/questions

Similarity-only canonicalization and synonyms are NEVER used for removal.

The pretrained semantic model is optional and disabled by default.
If it is unavailable, the existing lexical system continues working.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, replace
from typing import FrozenSet, List, Optional, Sequence, Tuple

from . import config
from .models import Finding
from .semantic_similarity import semantic_similarity_matrix
from .textutils import (
    Segment,
    content_stems,
    similarity_content_stems,
    extract_numbers,
    head_word,
    is_negated,
    words,
)


COMPARABLE_KINDS = {"instruction", "constraint", "question"}

# Initial conservative thresholds for sentence-embedding similarity.
# These are separate from the existing TF-IDF thresholds in config.py.
SEMANTIC_SIMILARITY_THRESHOLD_INSTRUCTION = 0.82
SEMANTIC_SIMILARITY_THRESHOLD_CONSTRAINT = 0.86


_SPLIT_RE = re.compile(
    r"\s*(?:,\s*(?:and\s+)?(?:then\s+)?|;\s*|:\s*|"
    r"\s+and\s+(?:also\s+)?(?:then\s+)?)"
    r"(?=(?:please\s+)?(?:" + "|".join(sorted(config.SPLIT_VERBS)) + r")\b)",
    re.IGNORECASE,
)


@dataclass
class Clause:
    text: str
    kind: str
    seg_index: int
    stems: FrozenSet[str]
    head: Optional[str]
    negated: bool
    numbers: FrozenSet[str]
    removed: bool = False
    covered_by: Optional[int] = None


def split_clauses(sentence: str) -> List[str]:
    parts = [p.strip() for p in _SPLIT_RE.split(sentence) if p and p.strip()]
    return parts or [sentence]


def build_clauses(segments: Sequence[Segment]) -> List[Clause]:
    """Build clauses for comparable instruction/constraint/question segments."""
    clauses: List[Clause] = []

    for i, seg in enumerate(segments):
        if seg.removed or seg.locked or seg.kind not in COMPARABLE_KINDS:
            continue

        parts = split_clauses(seg.text) if seg.kind != "question" else [seg.text]

        for part in parts:
            clauses.append(Clause(
                text=part,
                kind=seg.kind,
                seg_index=i,
                # IMPORTANT:
                # Keep original stems for strict subsumption/removal.
                # Similarity-only mappings must never enter this field.
                stems=content_stems(part),
                head=head_word(part),
                negated=is_negated(part),
                numbers=extract_numbers(part),
            ))

    return clauses


# ---------------------------------------------------------------------------
# Lexical similarity (scikit-learn)
# ---------------------------------------------------------------------------

def similarity_matrix(clauses: Sequence[Clause]):
    """
    Calculate cosine similarity between similarity-only stem vectors.

    Expanded canonicalization and synonym mappings are used exclusively
    for similarity detection. Clause.stems remains unchanged and continues
    to be used by the conservative subsumption/removal logic.

    Returns None when the matrix cannot be computed.
    """
    if len(clauses) < 2 or len(clauses) > config.MAX_CLAUSES_FOR_PAIRWISE:
        return None

    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    docs = [
        " ".join(sorted(similarity_content_stems(c.text)))
        for c in clauses
    ]

    if not any(docs):
        return None

    try:
        X = CountVectorizer(
            binary=True,
            token_pattern=r"\S+",
            lowercase=False,
        ).fit_transform(docs)
    except ValueError:
        return None

    return cosine_similarity(X)


# ---------------------------------------------------------------------------
# Shared safety checks
# ---------------------------------------------------------------------------

def _same_class(a: Clause, b: Clause) -> bool:
    """Only compare clauses with the same semantic role."""
    return a.kind == b.kind


def _subsumed(small: Clause, big: Clause) -> bool:
    """
    True only if ``small`` adds nothing that ``big`` does not already say.

    This remains the sole authority for removing clauses.

    It deliberately uses Clause.stems, which contain the original
    conservative content stems, not similarity-only expanded stems.
    """
    if not small.stems or not _same_class(small, big):
        return False

    if small.negated != big.negated:
        return False

    if not small.numbers <= big.numbers:
        return False

    if not small.stems <= big.stems:
        return False

    if small.kind == "constraint":
        return len(small.stems) >= 2 or small.stems == big.stems

    # Instruction / question: same head verb required.
    return small.head is not None and small.head == big.head


# ---------------------------------------------------------------------------
# Hybrid similarity
# ---------------------------------------------------------------------------

def _valid_similarity_matrix(matrix, size: int) -> bool:
    """Check that a supplied similarity matrix has the expected dimensions."""
    if matrix is None:
        return False

    try:
        if len(matrix) != size:
            return False

        for row in matrix:
            if len(row) != size:
                return False

            for value in row:
                if not math.isfinite(float(value)):
                    return False

        return True

    except (TypeError, ValueError, IndexError):
        return False


def _semantic_threshold(kind: str) -> float:
    if kind == "constraint":
        return SEMANTIC_SIMILARITY_THRESHOLD_CONSTRAINT

    return SEMANTIC_SIMILARITY_THRESHOLD_INSTRUCTION


@dataclass
class Pair:
    i: int
    j: int
    sim: float
    relation: str       # "equal" | "i_in_j" | "j_in_i" | "similar"


def find_pairs(
    clauses: Sequence[Clause],
    semantic_sims=None,
) -> List[Pair]:
    """
    Find duplicate or similar clause pairs.

    Args:
        clauses: Clauses to compare.
        semantic_sims: Optional precomputed semantic similarity matrix.
            Primarily useful for testing. When omitted, the optional
            pretrained model is consulted if enabled.

    Returns:
        Pairs classified as equal, subsumed, or merely similar.

    Semantic and similarity-only lexical matching can create a "similar"
    finding, but cannot create an "equal", "i_in_j", or "j_in_i"
    removal relationship.
    """
    size = len(clauses)

    if size < 2 or size > config.MAX_CLAUSES_FOR_PAIRWISE:
        return []

    lexical_sims = similarity_matrix(clauses)

    if semantic_sims is None:
        semantic_sims = semantic_similarity_matrix(
            [clause.text for clause in clauses]
        )

    use_lexical = _valid_similarity_matrix(lexical_sims, size)
    use_semantic = _valid_similarity_matrix(semantic_sims, size)

    if not use_lexical and not use_semantic:
        return []

    pairs: List[Pair] = []

    for i in range(size):
        for j in range(i + 1, size):
            a, b = clauses[i], clauses[j]

            # Never compare different clause roles.
            if not _same_class(a, b):
                continue

            lexical_score = (
                float(lexical_sims[i][j]) if use_lexical else 0.0
            )
            semantic_score = (
                float(semantic_sims[i][j]) if use_semantic else 0.0
            )

            # Keep the strongest available score for reporting.
            combined_score = max(lexical_score, semantic_score)

            # Strict subsumption is evaluated independently of semantic
            # and similarity-only lexical similarity.
            # It remains the only route to a removal relationship.
            if a.stems == b.stems and _subsumed(a, b):
                pairs.append(Pair(i, j, combined_score, "equal"))

            elif _subsumed(a, b):
                pairs.append(Pair(i, j, combined_score, "i_in_j"))

            elif _subsumed(b, a):
                pairs.append(Pair(i, j, combined_score, "j_in_i"))

            else:
                # Similarity findings must not combine opposite polarity
                # or clauses with different numerical requirements.
                if a.negated != b.negated or a.numbers != b.numbers:
                    continue

                lexical_threshold = (
                    config.SIMILARITY_THRESHOLD_CONSTRAINT
                    if a.kind == "constraint"
                    else config.SIMILARITY_THRESHOLD_INSTRUCTION
                )

                semantic_threshold = _semantic_threshold(a.kind)

                lexical_match = (
                    use_lexical and lexical_score >= lexical_threshold
                )
                semantic_match = (
                    use_semantic and semantic_score >= semantic_threshold
                )

                if lexical_match or semantic_match:
                    pairs.append(Pair(
                        i,
                        j,
                        combined_score,
                        "similar",
                    ))

    return pairs


# ---------------------------------------------------------------------------
# Removal
# ---------------------------------------------------------------------------

def select_removals(
    clauses: List[Clause],
    semantic_sims=None,
) -> List[Tuple[int, int]]:
    """
    Mark fully-covered clauses as removed.

    Returns:
        [(removed_index, kept_index), ...]

    The semantic matrix is accepted for API consistency and testing.
    It can help find_pairs() report similarity, but only strict
    original-stem subsumption relationships can cause removal.
    """
    removed: List[Tuple[int, int]] = []

    for pair in find_pairs(clauses, semantic_sims=semantic_sims):
        if pair.relation == "similar":
            continue

        if clauses[pair.i].removed or clauses[pair.j].removed:
            continue

        drop, keep = {
            "equal": (pair.j, pair.i),
            "i_in_j": (pair.i, pair.j),
            "j_in_i": (pair.j, pair.i),
        }[pair.relation]

        clauses[drop].removed = True
        clauses[drop].covered_by = keep
        removed.append((drop, keep))

    return removed


def _short(text: str, n: int = 70) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1] + "\u2026"


# ---------------------------------------------------------------------------
# Detectors -> Findings
# ---------------------------------------------------------------------------

def _redundancy_findings(
    clauses: Sequence[Clause],
    constraint: bool,
) -> List[Finding]:
    """One finding per redundant clause (not per pair), using a throw-away copy."""
    work = [replace(c) for c in clauses]
    removals = select_removals(work)
    dropped = {d for d, _ in removals}

    findings: List[Finding] = []

    for drop, keep in removals:
        if (work[drop].kind == "constraint") != constraint:
            continue

        what = (
            "Duplicate constraint detected (same requirement stated again)"
            if constraint else "Repeated instruction detected"
        )

        findings.append(Finding(
            "duplicate_constraint" if constraint else "redundancy",
            "medium",
            what,
            [
                f"'{_short(work[drop].text)}' is already covered by "
                f"'{_short(work[keep].text)}'"
            ],
        ))

    for pair in find_pairs(clauses):
        if pair.relation != "similar" or pair.i in dropped or pair.j in dropped:
            continue

        a, b = clauses[pair.i], clauses[pair.j]

        if (a.kind == "constraint") != constraint:
            continue

        what = (
            "Similar constraints detected; the same requirement may be stated more than once"
            if constraint else
            "Similar instructions detected; they may be stating the same request twice"
        )

        findings.append(Finding(
            "duplicate_constraint" if constraint else "redundancy",
            "low",
            what,
            [_short(a.text), _short(b.text)],
        ))

    return findings


def detect_repeated_instructions(
    clauses: Sequence[Clause],
) -> List[Finding]:
    return _redundancy_findings(clauses, constraint=False)


def detect_duplicate_constraints(
    clauses: Sequence[Clause],
) -> List[Finding]:
    return _redundancy_findings(clauses, constraint=True)


# ---------------------------------------------------------------------------
# Repeated phrase detection
# ---------------------------------------------------------------------------

def repeated_phrases(
    segments: Sequence[Segment],
) -> Tuple[List[Tuple[str, int]], float]:
    """
    Return ([(phrase, count)], repeated_phrase_ratio).

    Looks for word n-grams (3..8 words) that occur at least twice in the prose
    (non-locked segments), keeps only maximal phrases, and ignores phrases
    made only of stop-words, placeholders or numbers.
    """
    sentences = [
        words(s.text)
        for s in segments
        if not s.locked and not s.removed
    ]

    total_words = sum(len(s) for s in sentences)

    if total_words < 8:
        return [], 0.0

    accepted: List[Tuple[Tuple[str, ...], int]] = []

    for n in range(
        config.REPEATED_PHRASE_MAX_WORDS,
        config.REPEATED_PHRASE_MIN_WORDS - 1,
        -1,
    ):
        counts: Counter = Counter()

        for toks in sentences:
            for k in range(len(toks) - n + 1):
                gram = tuple(toks[k:k + n])

                if any(t.startswith("qzph") for t in gram):
                    continue

                if all(t in config.STOPWORDS or t.isdigit() for t in gram):
                    continue

                counts[gram] += 1

        for gram, count in counts.items():
            if count < config.REPEATED_PHRASE_MIN_COUNT:
                continue

            joined = " ".join(gram)

            if any(
                joined in " ".join(existing)
                and count <= existing_count
                for existing, existing_count in accepted
            ):
                continue

            accepted.append((gram, count))

    accepted.sort(
        key=lambda item: (
            len(item[0]) * (item[1] - 1),
            len(item[0]),
        ),
        reverse=True,
    )

    extra_words = sum(
        len(gram) * (count - 1)
        for gram, count in accepted
    )

    ratio = min(1.0, extra_words / total_words)

    shown = [
        (" ".join(gram), count)
        for gram, count in accepted[:config.REPEATED_PHRASE_MAX_REPORTED]
    ]

    return shown, round(ratio, 4)


def detect_repeated_phrases(
    segments: Sequence[Segment],
) -> Tuple[List[Finding], float]:
    phrases, ratio = repeated_phrases(segments)

    if not phrases:
        return [], ratio

    severity = (
        "high" if ratio >= 0.30
        else "medium" if ratio >= 0.12
        else "low"
    )

    evidence = [f"'{phrase}' x{count}" for phrase, count in phrases]

    return [
        Finding(
            "repeated_phrase",
            severity,
            "Phrases repeated unnecessarily (%.0f%% of the wording is repeated)"
            % (ratio * 100),
            evidence,
        )
    ], ratio
