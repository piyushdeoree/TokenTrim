"""
analyzer.py - orchestration and the remaining detectors.

Main entry points (for Person 3):

    analyze_prompt(prompt, model)           -> dict   (the agreed backend contract)
    analyze_prompt_detailed(prompt, model)  -> DetailedAnalysis (explainable, richer)

Detectors defined here: verbosity, excessive context, formatting overload,
conflicting instructions. Repetition detectors live in redundancy.py and the
complexity features in complexity.py.

Pipeline:  tokens -> segmentation/classification -> detectors -> complexity
           -> optimize (candidate) -> validate -> accept or fall back to original
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Sequence

from . import config
from .complexity import complexity_label, complexity_score, compute_features, format_directive_hits
from .models import (
    AnalysisResponse, DetailedAnalysis, DetailedIssue, Finding, OptimizationResult,
    PromptAnalysis, TokenStats,
)
from .optimizer import optimize_prompt, optimize_with_llm
from .redundancy import (
    Clause, build_clauses, detect_duplicate_constraints, detect_repeated_instructions,
    detect_repeated_phrases,
)
from .textutils import (
    Segment, content_stems, prepare_prompt, rewrite_segments, words,
)
from .tokenizer import count_tokens, count_tokens_only, tokenizer_info
from .validator import validate_optimization

_SUGGESTIONS = {
    "redundancy": "Remove repeated instructions",
    "repeated_phrase": "Consolidate phrases that are repeated",
    "verbosity": "Replace verbose phrasing with direct instructions",
    "duplicate_constraint": "State each constraint only once",
    "excessive_context": "Review the context size: include only what the task needs (e.g. summarize or retrieve the relevant parts)",
    "formatting": "Keep only the formatting instructions you actually need",
    "conflict": "Resolve conflicting instructions manually (they are never auto-resolved)",
    "complexity": "Consider splitting this prompt into smaller steps",
}


def _short(text: str, n: int = 70) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1] + "\u2026"


# ---------------------------------------------------------------------------
# Verbosity
# ---------------------------------------------------------------------------
def detect_verbosity(segments: Sequence[Segment]) -> List[Finding]:
    _, events = rewrite_segments(list(segments))
    findings: List[Finding] = []
    persona = [e for _, e in events if e.kind == "persona"]
    rewrites = [e for _, e in events if e.kind != "persona"]
    if rewrites:
        n = len(rewrites)
        sev = "low" if n <= 2 else "medium" if n <= 5 else "high"
        ev = []
        for e in rewrites:
            ev.append(f"'{e.before}' -> '{e.after}'" if e.after else f"'{e.before}' (can be removed)")
        findings.append(Finding("verbosity", sev,
                                f"Verbose wording detected ({n} simplification{'s' if n != 1 else ''} possible)",
                                ev[:6]))
    for e in persona:
        findings.append(Finding("verbosity", "low",
                                "Generic persona statement adds tokens without task-specific information",
                                [_short(e.before)]))
    long_sents = [s for s in segments if not s.locked and not s.removed
                  and s.kind != "context" and len(words(s.text)) > config.LONG_SENTENCE_WORDS]
    if long_sents:
        findings.append(Finding("verbosity", "low",
                                f"{len(long_sents)} very long instruction sentence(s) (> {config.LONG_SENTENCE_WORDS} words)",
                                [_short(s.text) for s in long_sents[:2]]))
    return findings


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------
def context_and_instruction_tokens(prepared, model: str):
    ctx, ins = [], []
    for s in prepared.segments:
        text = prepared.unmask(s.text)
        (ctx if s.kind == "context" else ins).append(text)
    c = count_tokens_only("\n".join(ctx), model) if ctx else 0
    i = count_tokens_only("\n".join(ins), model) if ins else 0
    return c, i


def detect_excessive_context(prepared, context_tokens: int, instruction_tokens: int) -> List[Finding]:
    findings: List[Finding] = []
    ratio = context_tokens / max(instruction_tokens, 1)
    if context_tokens >= config.CONTEXT_MIN_TOKENS and ratio >= config.CONTEXT_RATIO_THRESHOLD:
        sev = "high" if context_tokens >= 2 * config.CONTEXT_HIGH_TOKENS else \
              "medium" if (context_tokens >= config.CONTEXT_HIGH_TOKENS or ratio >= 20) else "low"
        findings.append(Finding(
            "excessive_context", sev,
            f"Context is large relative to the task ({context_tokens} context tokens vs "
            f"{instruction_tokens} instruction tokens, ratio {ratio:.1f}:1). "
            "It is NOT removed automatically because it may be important",
            [f"context_tokens={context_tokens}", f"instruction_tokens={instruction_tokens}"]))
    seen: Dict[str, int] = {}
    for s in prepared.segments:
        if s.kind == "context" and len(words(s.text)) >= 6:
            key = " ".join(words(s.text))
            seen[key] = seen.get(key, 0) + 1
    dups = [k for k, v in seen.items() if v > 1]
    if dups:
        findings.append(Finding("excessive_context", "low",
                                f"{len(dups)} sentence(s) in the context appear more than once",
                                [_short(d) for d in dups[:2]]))
    return findings


# ---------------------------------------------------------------------------
# Formatting overload
# ---------------------------------------------------------------------------
def detect_formatting_overload(segments: Sequence[Segment]) -> List[Finding]:
    hits = format_directive_hits(segments)
    if len(hits) < config.FORMAT_DIRECTIVE_THRESHOLD:
        return []
    sev = "medium" if len(hits) >= config.FORMAT_DIRECTIVE_HIGH else "low"
    return [Finding("formatting", sev,
                    f"{len(hits)} different formatting requirements; check that all are really needed",
                    hits)]


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------
_LIMIT_RE = re.compile(
    r"(?P<op>at most|no more than|up to|under|fewer than|less than|maximum of|max(?:imum)?|within|"
    r"at least|no fewer than|minimum of|min(?:imum)?|more than|exactly)?\s*"
    r"(?P<n>\d+)\s*(?P<unit>words?|sentences?|paragraphs?|bullet points?|bullets?|characters?|chars?|"
    r"lines?|items?|tokens?|steps?|examples?)\b", re.IGNORECASE)
_MAX_OPS = {"at most", "no more than", "up to", "under", "fewer than", "less than", "maximum of", "max", "maximum", "within"}
_MIN_OPS = {"at least", "no fewer than", "minimum of", "min", "minimum", "more than"}


def _limits(text: str):
    out = []
    for m in _LIMIT_RE.finditer(text):
        op = (m.group("op") or "").lower()
        kind = "max" if op in _MAX_OPS else "min" if op in _MIN_OPS else "exact"
        unit = config.LENGTH_UNITS.get(m.group("unit").lower(), m.group("unit").lower())
        out.append((unit, kind, int(m.group("n")), m.group(0).strip()))
    return out


def detect_conflicts(segments: Sequence[Segment], clauses: Sequence[Clause]) -> List[Finding]:
    findings: List[Finding] = []
    live = [s for s in segments if not s.removed and not s.locked
            and s.kind in ("instruction", "constraint", "question", "role")]
    text = " ".join(s.text for s in live).lower()

    # 1. direct polarity contradiction ("Include X." vs "Do not include X.")
    for i, a in enumerate(clauses):
        for b in clauses[i + 1:]:
            if a.negated != b.negated:
                sa, sb = a.stems - {"not"}, b.stems - {"not"}
                if sa and sa == sb:
                    findings.append(Finding("conflict", "high", "Contradictory instructions detected",
                                            [_short(a.text), _short(b.text)]))

    # 2. opposing style words
    for left, right in config.OPPOSING_TERMS:
        l = [w for w in left if re.search(r"\b" + re.escape(w) + r"\b", text)]
        r = [w for w in right if re.search(r"\b" + re.escape(w) + r"\b", text)]
        if l and r:
            findings.append(Finding(
                "conflict", "medium",
                f"Possibly conflicting requirements: '{l[0]}' and '{r[0]}' pull in opposite directions",
                [f"'{l[0]}' vs '{r[0]}'"]))

    # 3. length limits that cannot all hold
    by_unit: Dict[str, list] = {}
    for s in live:
        for unit, kind, n, raw in _limits(s.text):
            by_unit.setdefault(unit, []).append((kind, n, raw))
    for unit, items in by_unit.items():
        maxes = [x for x in items if x[0] == "max"]
        mins = [x for x in items if x[0] == "min"]
        exacts = [x for x in items if x[0] == "exact"]
        msg = None
        if maxes and mins and min(m[1] for m in mins) > min(m[1] for m in maxes):
            msg = f"minimum {unit} limit is larger than the maximum"
        elif len({e[1] for e in exacts}) > 1:
            msg = f"different exact {unit} counts requested"
        if msg:
            findings.append(Finding("conflict", "medium", f"Possibly conflicting length requirements: {msg}",
                                    [x[2] for x in items[:4]]))

    # 4. mutually exclusive output formats in different directives
    formats = set()
    for s in live:
        m = config.OUTPUT_DIRECTIVE_RE.search(s.text)
        if m:
            formats.add(m.group(1).lower())
    if len(formats) > 1:
        findings.append(Finding("conflict", "medium",
                                "Possibly conflicting output formats requested: " + ", ".join(sorted(formats)),
                                sorted(formats)))
    return findings


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def build_analysis(prompt: str, model: str = config.DEFAULT_MODEL) -> PromptAnalysis:
    """Run all detectors and compute complexity features (no optimization yet)."""
    prepared = prepare_prompt(prompt)
    info = tokenizer_info(model)
    stats = count_tokens(prepared.original, model)
    token_stats = TokenStats(**stats, method=info.method, exact=info.exact, note=info.note)

    rewritten, _ = rewrite_segments(prepared.segments)
    clauses = build_clauses(rewritten)
    ctx_tokens, ins_tokens = context_and_instruction_tokens(prepared, model)

    findings: List[Finding] = []
    findings += detect_repeated_instructions(clauses)
    findings += detect_duplicate_constraints(clauses)
    phrase_findings, phrase_ratio = detect_repeated_phrases(prepared.segments)
    findings += phrase_findings
    findings += detect_verbosity(prepared.segments)
    findings += detect_excessive_context(prepared, ctx_tokens, ins_tokens)
    findings += detect_formatting_overload(prepared.segments)
    findings += detect_conflicts(rewritten, clauses)

    features = compute_features(prepared.original, stats["input_tokens"], prepared.segments, clauses,
                                phrase_ratio, ctx_tokens, ins_tokens)
    score = complexity_score(features)
    if score >= 66:
        findings.append(Finding("complexity", "low" if score < 80 else "medium",
                                f"High prompt complexity (score {score}/100)",
                                [f"instructions={features.instruction_count}",
                                 f"constraints={features.constraint_count}"]))
    return PromptAnalysis(prompt=prepared.original, model=model, prepared=prepared,
                          token_stats=token_stats, findings=findings,
                          features=features, complexity_score=score)


def _dedupe_findings(findings: List[Finding]) -> List[Finding]:
    seen, out = set(), []
    for f in findings:
        key = (f.type, f.description, tuple(f.evidence))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def analyze_prompt_detailed(prompt: str, model: str = config.DEFAULT_MODEL,
                            llm_rewriter: Optional[Callable[[str], str]] = None) -> DetailedAnalysis:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    analysis = build_analysis(prompt, model)
    original = analysis.prompt
    orig_tokens = analysis.token_stats.input_tokens

    candidates: List[OptimizationResult] = [optimize_prompt(original, analysis)]
    if llm_rewriter is not None:
        llm = optimize_with_llm(original, llm_rewriter, model)
        if llm is not None:
            candidates.append(llm)

    # pick the valid candidate with the largest saving
    best, best_validation, first_validation = None, None, None
    for cand in candidates:
        v = validate_optimization(original, cand.optimized_prompt)
        if first_validation is None:
            first_validation = v
        if v.is_valid and cand.tokens_saved > 0 and (best is None or cand.tokens_saved > best.tokens_saved):
            best, best_validation = cand, v

    findings = _dedupe_findings(analysis.findings)
    suggestions: List[str] = []
    for f in findings:
        s = _SUGGESTIONS.get(f.type)
        if s and s not in suggestions:
            suggestions.append(s)

    if best is not None:
        final, validation, accepted = best, best_validation, True
    else:
        validation = first_validation
        rejected = not validation.is_valid
        final = OptimizationResult(
            optimized_prompt=original, original_tokens=orig_tokens, optimized_tokens=orig_tokens,
            tokens_saved=0, reduction_percentage=0.0,
            changes=(["Optimization rejected by the safety check; original prompt returned"] if rejected
                     else ["No safe optimization found; original prompt returned"]),
            method="none")
        accepted = False
        if rejected:
            suggestions.append("Automatic optimization was rejected by the safety check; apply the suggestions manually")

    return DetailedAnalysis(
        token_stats=analysis.token_stats,
        features=analysis.features,
        complexity_score=analysis.complexity_score,
        complexity_label=complexity_label(analysis.complexity_score),
        issues=[DetailedIssue(type=f.type, severity=f.severity, description=f.description, evidence=f.evidence)
                for f in findings],
        suggestions=suggestions,
        candidate=candidates[0],
        validation=validation,
        final=final,
        optimization_accepted=accepted,
    )


def analyze_prompt(prompt: str, model: str = config.DEFAULT_MODEL,
                   llm_rewriter: Optional[Callable[[str], str]] = None) -> dict:
    """MAIN ENTRY POINT. Returns exactly the agreed backend structure (a dict).

    Raises ValueError for an empty prompt.
    """
    d = analyze_prompt_detailed(prompt, model, llm_rewriter)
    resp = AnalysisResponse(
        original_tokens=d.final.original_tokens,
        optimized_tokens=d.final.optimized_tokens,
        tokens_saved=d.final.tokens_saved,
        reduction_percentage=d.final.reduction_percentage,
        word_count=d.token_stats.word_count,
        complexity_score=d.complexity_score,
        issues=[{"type": i.type, "severity": i.severity, "description": i.description} for i in d.issues],
        suggestions=d.suggestions,
        optimized_prompt=d.final.optimized_prompt,
    )
    return resp.model_dump()
