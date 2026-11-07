"""
validator.py - safety check for an optimized prompt.

Compares ORIGINAL vs OPTIMIZED and rejects the optimization when important
information appears to be lost. It checks (hard = reject immediately):

  hard  numbers            every number / percentage / amount is still present
  hard  protected spans    code, URLs, e-mails, quoted strings, JSON blocks
  hard  output format      json / xml / csv / markdown / table / bullet ... keywords
  hard  named items        capitalised names, acronyms, camelCase / snake_case
  hard  constraints        each constraint sentence is >= 85 % covered (and
                           negations such as "do not" still present)
  soft  keyword coverage   >= 90 % of the original content stems remain
  soft  lexical similarity TF-IDF cosine(original, optimized) >= 0.35

These are surface-level checks. A passing result means "no *detectable* loss",
NOT proven semantic equivalence.
"""
from __future__ import annotations

import re
from typing import Dict, FrozenSet, List, Set

from . import config
from .models import ValidationResult
from .textutils import (
    apply_rewrites, content_stems, extract_numbers, is_negated, prepare_prompt,
    protect_spans, render_segments,
)


def _entities(text: str) -> Set[str]:
    """Names, acronyms, camelCase/snake_case identifiers (case-sensitive)."""
    found: Set[str] = set()
    for seg in prepare_prompt(text).segments:       # one entry per sentence / list item
        toks = re.findall(r"[A-Za-z][A-Za-z0-9_]*", seg.text)
        for k, tok in enumerate(toks):
            if tok.upper().startswith("QZPH") or len(tok) < 2:
                continue
            special = (tok.isupper() or "_" in tok
                       or (re.search(r"[a-z][A-Z]", tok) is not None))
            if special or (k > 0 and tok[0].isupper()):
                found.add(tok)
    return found


def _format_keywords(text: str) -> Set[str]:
    low = text.lower()
    return {k.replace("-", " ") for k in config.FORMAT_KEYWORDS
            if re.search(r"\b" + re.escape(k) + r"\b", low)}


def _lexical_similarity(a: str, b: str) -> float:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    docs = [" ".join(sorted(content_stems(a))), " ".join(sorted(content_stems(b)))]
    if not docs[0] or not docs[1]:
        return 0.0
    try:
        X = TfidfVectorizer(token_pattern=r"\S+", lowercase=False).fit_transform(docs)
    except ValueError:
        return 0.0
    return float(cosine_similarity(X[0], X[1])[0][0])


def validate_optimization(original: str, optimized: str) -> ValidationResult:
    reasons: List[str] = []
    metrics: Dict[str, float] = {}
    original, optimized = original.strip(), optimized.strip()

    if not optimized:
        return ValidationResult(is_valid=False, reasons=["Optimized prompt is empty"], metrics={})

    prep = prepare_prompt(original)
    persona_idx = {i for i, s in enumerate(prep.segments) if s.kind == "persona" and not s.locked}
    # text of the original WITHOUT generic persona statements (they carry no task info),
    # rendered with its original line/list layout
    core_masked = render_segments([s for i, s in enumerate(prep.segments) if i not in persona_idx])
    core_original = prep.unmask(core_masked)

    # 1. numbers --------------------------------------------------------------
    orig_nums, opt_nums = extract_numbers(core_original), extract_numbers(optimized)
    missing = sorted(orig_nums - opt_nums)
    metrics["number_coverage"] = 1.0 if not orig_nums else 1 - len(missing) / len(orig_nums)
    if missing:
        reasons.append(f"Numbers lost: {', '.join(missing)}")

    # 2. protected spans --------------------------------------------------------
    lost_spans = [frag for frag in prep.mapping.values() if frag not in optimized]
    metrics["protected_span_coverage"] = (
        1.0 if not prep.mapping else 1 - len(lost_spans) / len(prep.mapping))
    if lost_spans:
        reasons.append("Code/URL/quoted/JSON content changed or lost: "
                       + "; ".join(f[:40] for f in lost_spans[:3]))

    # 3. output format ----------------------------------------------------------
    orig_fmt, opt_fmt = _format_keywords(core_original), _format_keywords(optimized)
    lost_fmt = sorted(orig_fmt - opt_fmt)
    metrics["format_keyword_coverage"] = 1.0 if not orig_fmt else 1 - len(lost_fmt) / len(orig_fmt)
    if lost_fmt:
        reasons.append(f"Output-format requirement lost: {', '.join(lost_fmt)}")

    # 4. named items ------------------------------------------------------------
    orig_ent, opt_ent = _entities(core_original), _entities(optimized) | {
        t for t in re.findall(r"[A-Za-z][A-Za-z0-9_]*", optimized)}
    lost_ent = sorted(orig_ent - opt_ent)
    metrics["entity_coverage"] = 1.0 if not orig_ent else 1 - len(lost_ent) / len(orig_ent)
    if lost_ent:
        reasons.append(f"Named items lost: {', '.join(lost_ent[:5])}")

    # 5. constraints ------------------------------------------------------------
    opt_stems = content_stems(optimized)
    opt_negated = is_negated(optimized)
    checked, bad = 0, []
    for i, seg in enumerate(prep.segments):
        if i in persona_idx or seg.locked or seg.kind not in ("constraint", "instruction", "question", "role"):
            continue
        if seg.kind != "constraint" and not (config.CONSTRAINT_RE.search(seg.text) or is_negated(seg.text)):
            continue
        stems = {s for s in content_stems(seg.text) if not s.startswith("qzph")}
        if not stems:
            continue
        checked += 1
        cov = len(stems & opt_stems) / len(stems)
        if cov < config.CONSTRAINT_COVERAGE_MIN or (is_negated(seg.text) and not opt_negated):
            bad.append(prep.unmask(seg.text)[:50])
    metrics["constraints_checked"] = float(checked)
    metrics["constraint_coverage"] = 1.0 if not checked else 1 - len(bad) / checked
    if bad:
        reasons.append("Constraint(s) possibly lost: " + "; ".join(bad[:3]))

    # 6. keyword coverage (soft) ------------------------------------------------
    ignorable: Set[str] = set()
    for seg in prep.segments:
        if seg.locked or seg.kind not in ("instruction", "constraint", "question"):
            continue
        _, events = apply_rewrites(seg.text)
        for ev in events:
            ignorable |= content_stems(ev.before) - content_stems(ev.after)
    orig_stems = {s for s in content_stems(core_masked) if not s.startswith("qzph")} - ignorable
    kw_cov = 1.0 if not orig_stems else len(orig_stems & opt_stems) / len(orig_stems)
    metrics["keyword_coverage"] = round(kw_cov, 4)
    if kw_cov < config.KEYWORD_COVERAGE_MIN:
        reasons.append(f"Keyword coverage {kw_cov:.0%} is below {config.KEYWORD_COVERAGE_MIN:.0%}")

    # 7. lexical similarity (soft) ------------------------------------------------
    sim = _lexical_similarity(core_original, optimized)
    metrics["lexical_similarity"] = round(sim, 4)
    if sim < config.MIN_LEXICAL_SIMILARITY:
        reasons.append(f"Lexical similarity {sim:.2f} is below {config.MIN_LEXICAL_SIMILARITY}")

    for k in list(metrics):
        metrics[k] = round(float(metrics[k]), 4)
    return ValidationResult(is_valid=not reasons, reasons=reasons, metrics=metrics)
