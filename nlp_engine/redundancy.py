"""
redundancy.py - detection of repeated / duplicated content.

Techniques (all deterministic):
  * clause extraction (sentence -> clauses split before instruction verbs)
  * stem-set representation of each clause (Porter stemming + synonym folding)
  * cosine similarity on binary stem vectors (scikit-learn)  -> REPORTING
  * strict subsumption test (A's stems are a subset of B's, same polarity,
    same numbers, same head verb)                            -> REMOVAL
  * word n-gram counting for repeated phrases

Reporting is deliberately more liberal than removal: two clauses that are merely
*similar* are reported as an issue, but only a clause whose content is fully
covered by another clause is ever removed by the optimizer.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, replace
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from . import config
from .models import Finding
from .textutils import (
    Segment, content_stems, extract_numbers, head_word, is_negated, words,
)

COMPARABLE_KINDS = {"instruction", "constraint", "question"}

_SPLIT_RE = re.compile(
    r"\s*(?:,\s*(?:and\s+)?(?:then\s+)?|;\s*|\s+and\s+(?:also\s+)?(?:then\s+)?)"
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
    """Clauses for every comparable (instruction/constraint/question) segment."""
    clauses: List[Clause] = []
    for i, seg in enumerate(segments):
        if seg.removed or seg.locked or seg.kind not in COMPARABLE_KINDS:
            continue
        parts = split_clauses(seg.text) if seg.kind != "question" else [seg.text]
        for part in parts:
            clauses.append(Clause(
                text=part, kind=seg.kind, seg_index=i,
                stems=content_stems(part), head=head_word(part),
                negated=is_negated(part), numbers=extract_numbers(part),
            ))
    return clauses


# ---------------------------------------------------------------------------
# Similarity (scikit-learn)
# ---------------------------------------------------------------------------
def similarity_matrix(clauses: Sequence[Clause]):
    """Cosine similarity between binary stem vectors; None if not computable."""
    if len(clauses) < 2 or len(clauses) > config.MAX_CLAUSES_FOR_PAIRWISE:
        return None
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    docs = [" ".join(sorted(c.stems)) for c in clauses]
    if not any(docs):
        return None
    try:
        X = CountVectorizer(binary=True, token_pattern=r"\S+", lowercase=False).fit_transform(docs)
    except ValueError:
        return None
    return cosine_similarity(X)


def _same_class(a: Clause, b: Clause) -> bool:
    return (a.kind == "constraint") == (b.kind == "constraint")


def _subsumed(small: Clause, big: Clause) -> bool:
    """True if ``small`` adds nothing that ``big`` does not already say."""
    if not small.stems or not _same_class(small, big):
        return False
    if small.negated != big.negated or not small.numbers <= big.numbers:
        return False
    if not small.stems <= big.stems:
        return False
    if small.kind == "constraint":
        return len(small.stems) >= 2 or small.stems == big.stems
    # instruction / question: same head verb required
    return small.head is not None and small.head == big.head


@dataclass
class Pair:
    i: int
    j: int
    sim: float
    relation: str       # "equal" | "i_in_j" | "j_in_i" | "similar"


def find_pairs(clauses: Sequence[Clause]) -> List[Pair]:
    sims = similarity_matrix(clauses)
    pairs: List[Pair] = []
    if sims is None:
        return pairs
    for i in range(len(clauses)):
        for j in range(i + 1, len(clauses)):
            a, b = clauses[i], clauses[j]
            if not _same_class(a, b):
                continue
            sim = float(sims[i][j])
            if sim == 0.0:
                continue
            if a.stems == b.stems and _subsumed(a, b):
                pairs.append(Pair(i, j, sim, "equal"))
            elif _subsumed(a, b):
                pairs.append(Pair(i, j, sim, "i_in_j"))
            elif _subsumed(b, a):
                pairs.append(Pair(i, j, sim, "j_in_i"))
            else:
                thr = (config.SIMILARITY_THRESHOLD_CONSTRAINT if a.kind == "constraint"
                       else config.SIMILARITY_THRESHOLD_INSTRUCTION)
                if sim >= thr and a.negated == b.negated and a.numbers == b.numbers:
                    pairs.append(Pair(i, j, sim, "similar"))
    return pairs


def select_removals(clauses: List[Clause]) -> List[Tuple[int, int]]:
    """Mark fully-covered clauses as removed. Returns [(removed, kept_by)]."""
    removed: List[Tuple[int, int]] = []
    for p in find_pairs(clauses):
        if p.relation == "similar":
            continue
        if clauses[p.i].removed or clauses[p.j].removed:
            continue
        drop, keep = {"equal": (p.j, p.i), "i_in_j": (p.i, p.j), "j_in_i": (p.j, p.i)}[p.relation]
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
def _redundancy_findings(clauses: Sequence[Clause], constraint: bool) -> List[Finding]:
    """One finding per redundant clause (not per pair), using a throw-away copy."""
    work = [replace(c) for c in clauses]
    removals = select_removals(work)
    dropped = {d for d, _ in removals}
    findings: List[Finding] = []
    for drop, keep in removals:
        if (work[drop].kind == "constraint") != constraint:
            continue
        what = "Duplicate constraint detected (same requirement stated again)" if constraint \
            else "Repeated instruction detected"
        findings.append(Finding(
            "duplicate_constraint" if constraint else "redundancy", "medium", what,
            [f"'{_short(work[drop].text)}' is already covered by '{_short(work[keep].text)}'"]))
    for p in find_pairs(clauses):
        if p.relation != "similar" or p.i in dropped or p.j in dropped:
            continue
        a, b = clauses[p.i], clauses[p.j]
        if (a.kind == "constraint") != constraint:
            continue
        what = ("Similar constraints detected; the same requirement may be stated more than once"
                if constraint else "Similar instructions detected; they may be stating the same request twice")
        findings.append(Finding("duplicate_constraint" if constraint else "redundancy", "low",
                                what, [_short(a.text), _short(b.text)]))
    return findings


def detect_repeated_instructions(clauses: Sequence[Clause]) -> List[Finding]:
    return _redundancy_findings(clauses, constraint=False)


def detect_duplicate_constraints(clauses: Sequence[Clause]) -> List[Finding]:
    return _redundancy_findings(clauses, constraint=True)


def repeated_phrases(segments: Sequence[Segment]) -> Tuple[List[Tuple[str, int]], float]:
    """Return ([(phrase, count)], repeated_phrase_ratio).

    Looks for word n-grams (3..8 words) that occur at least twice in the prose
    (non-locked segments), keeps only maximal phrases, and ignores phrases made
    only of stop-words, placeholders or numbers.
    """
    sentences = [words(s.text) for s in segments if not s.locked and not s.removed]
    total_words = sum(len(s) for s in sentences)
    if total_words < 8:
        return [], 0.0

    accepted: List[Tuple[Tuple[str, ...], int]] = []
    for n in range(config.REPEATED_PHRASE_MAX_WORDS, config.REPEATED_PHRASE_MIN_WORDS - 1, -1):
        counts: Counter = Counter()
        for toks in sentences:
            for k in range(len(toks) - n + 1):
                gram = tuple(toks[k:k + n])
                if any(t.startswith("qzph") for t in gram):
                    continue
                if all(t in config.STOPWORDS or t.isdigit() for t in gram):
                    continue
                counts[gram] += 1
        for gram, c in counts.items():
            if c < config.REPEATED_PHRASE_MIN_COUNT:
                continue
            joined = " ".join(gram)
            if any(joined in " ".join(g) and c <= ac for g, ac in accepted):
                continue
            accepted.append((gram, c))

    accepted.sort(key=lambda x: (len(x[0]) * (x[1] - 1), len(x[0])), reverse=True)
    extra_words = sum(len(g) * (c - 1) for g, c in accepted)
    ratio = min(1.0, extra_words / total_words)
    shown = [(" ".join(g), c) for g, c in accepted[: config.REPEATED_PHRASE_MAX_REPORTED]]
    return shown, round(ratio, 4)


def detect_repeated_phrases(segments: Sequence[Segment]) -> Tuple[List[Finding], float]:
    phrases, ratio = repeated_phrases(segments)
    if not phrases:
        return [], ratio
    sev = "high" if ratio >= 0.30 else "medium" if ratio >= 0.12 else "low"
    evidence = [f"'{p}' x{c}" for p, c in phrases]
    return [Finding("repeated_phrase", sev,
                    "Phrases repeated unnecessarily (%.0f%% of the wording is repeated)" % (ratio * 100),
                    evidence)], ratio
