"""
optimizer.py - meaning-preserving prompt optimization.

``optimize_prompt`` is HEURISTIC: it applies only transformations that are safe
by construction and never edits protected spans (code, URLs, quotes, JSON) or
user content blocks.

  1. drop generic persona sentences ("You are a helpful assistant.")
  2. rewrite verbose wording in instruction-like sentences
       (lead-ins such as "I would like you to", filler words, wordy phrases)
  3. remove clauses that are fully covered by another clause
       (repeated instructions / duplicate constraints; strict subsumption)

It does NOT: resolve conflicting instructions, remove context, remove
formatting requirements, or paraphrase freely. Its output is a *candidate*; the
caller must run validator.validate_optimization() before accepting it.

``optimize_with_llm`` is the OPTIONAL LLM-assisted path: the caller supplies a
rewrite function; the result is only a candidate and goes through the same
validator.
"""
from __future__ import annotations

import re
from dataclasses import replace
from typing import Callable, List, Optional

from . import config
from .models import OptimizationResult, PromptAnalysis
from .redundancy import build_clauses, select_removals
from .textutils import (
    PreparedPrompt, capitalize_first, prepare_prompt, render_segments, rewrite_segments,
)
from .tokenizer import count_tokens_only


def _reduction(original: int, optimized: int) -> tuple:
    saved = max(original - optimized, 0)
    pct = round(100.0 * saved / original, 2) if original else 0.0
    return saved, pct


def _event_text(ev) -> str:
    if ev.kind == "persona":
        return f"Removed generic persona statement: '{ev.before}'"
    if ev.kind == "leadin":
        return f"Removed verbose lead-in: '{ev.before}'"
    if ev.kind == "filler":
        return f"Removed filler word: '{ev.before}'"
    return f"Simplified wording: {ev.label}"


def optimize_prompt(prompt: str, analysis: Optional[PromptAnalysis] = None,
                    model: Optional[str] = None) -> OptimizationResult:
    """Heuristic optimization. Returns a CANDIDATE (not yet validated)."""
    model = (analysis.model if analysis else None) or model or config.DEFAULT_MODEL
    prepared: PreparedPrompt = analysis.prepared if analysis else prepare_prompt(prompt)

    segments, events = rewrite_segments(prepared.segments)
    changes: List[str] = []
    seen = set()
    for _, ev in events:
        msg = _event_text(ev)
        if msg not in seen:
            seen.add(msg)
            changes.append(msg)

    # Clause-level removal of fully covered content
    clauses = build_clauses(segments)
    for drop, keep in select_removals(clauses):
        changes.append(f"Removed repeated content: '{clauses[drop].text.strip()}' "
                       f"(already covered by '{clauses[keep].text.strip()}')")

    by_seg = {}
    for c in clauses:
        by_seg.setdefault(c.seg_index, []).append(c)
    for idx, cl in by_seg.items():
        kept = [c for c in cl if not c.removed]
        if len(kept) == len(cl):
            continue
        seg = segments[idx]
        if not kept:
            seg.removed = True
            continue
        terminal = re.search(r"[.!?:;]+$", seg.text)
        body = " and ".join(c.text.strip().rstrip(".!?;, ") for c in kept)
        seg.text = capitalize_first(body) + (terminal.group(0) if terminal else "")

    optimized = prepared.unmask(render_segments(segments))
    original_tokens = count_tokens_only(prepared.original, model)
    optimized_tokens = count_tokens_only(optimized, model)
    saved, pct = _reduction(original_tokens, optimized_tokens)
    return OptimizationResult(
        optimized_prompt=optimized, original_tokens=original_tokens,
        optimized_tokens=optimized_tokens, tokens_saved=saved,
        reduction_percentage=pct, changes=changes, method="heuristic",
    )


def optimize_with_llm(prompt: str, rewriter: Callable[[str], str],
                      model: Optional[str] = None) -> Optional[OptimizationResult]:
    """OPTIONAL: ask an LLM-backed ``rewriter(prompt) -> str`` for a rewrite.

    The returned result is only a candidate - the analyzer validates it with the
    same checks as the heuristic output and discards it when it loses
    information. Any exception raised by the rewriter yields ``None``.
    """
    model = model or config.DEFAULT_MODEL
    try:
        text = (rewriter(prompt) or "").strip()
    except Exception:
        return None
    if not text:
        return None
    original_tokens = count_tokens_only(prompt, model)
    optimized_tokens = count_tokens_only(text, model)
    saved, pct = _reduction(original_tokens, optimized_tokens)
    return OptimizationResult(
        optimized_prompt=text, original_tokens=original_tokens,
        optimized_tokens=optimized_tokens, tokens_saved=saved,
        reduction_percentage=pct, changes=["LLM-assisted rewrite (validated by the same safety check)"],
        method="llm",
    )
