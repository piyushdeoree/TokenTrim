"""
complexity.py - measurable prompt-complexity features and a 0-100 score.

score = 100 * sum_i  weight_i * min(feature_i / cap_i, 1)

Weights and caps live in config.py. They are heuristic design choices (not
learned from data); the score is a *relative indicator* for comparing prompts,
not a calibrated measurement.
"""
from __future__ import annotations

import re
from typing import Sequence

from . import config
from .models import ComplexityFeatures
from .redundancy import Clause
from .textutils import Segment, words


def structure_depth(prompt: str) -> int:
    """Max nesting of brackets or indented list items (fenced code excluded)."""
    text = re.sub(r"```.*?```", "", prompt, flags=re.S)
    depth = max_depth = 0
    for ch in text:
        if ch in "([{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch in ")]}":
            depth = max(0, depth - 1)
    list_depth = 0
    for line in text.splitlines():
        m = re.match(r"^(\s*)(?:[-*\u2022+]|\d+[.)])\s+", line)
        if m:
            indent = len(m.group(1).replace("\t", "    "))
            list_depth = max(list_depth, indent // 2 + 1)
    return max(max_depth, list_depth)


def format_directive_hits(segments: Sequence[Segment]) -> list:
    text = " ".join(s.text for s in segments if not s.locked and not s.removed and s.kind != "context")
    return [name for name, rx in config.FORMAT_DIRECTIVES.items() if rx.search(text)]


def compute_features(prompt: str, token_count: int, segments: Sequence[Segment],
                     clauses: Sequence[Clause], repeated_phrase_ratio: float,
                     context_tokens: int, instruction_tokens: int) -> ComplexityFeatures:
    live = [s for s in segments if not s.removed]
    lengths = [len(words(s.text)) for s in live] or [0]
    constraint_count = sum(1 for s in live if not s.locked and s.kind == "constraint")
    instruction_count = sum(1 for c in clauses if c.kind in ("instruction", "question"))
    ratio = context_tokens / max(instruction_tokens, 1)
    return ComplexityFeatures(
        token_count=token_count,
        instruction_count=instruction_count,
        constraint_count=constraint_count,
        avg_sentence_length=round(sum(lengths) / len(lengths), 2),
        max_sentence_length=max(lengths),
        structure_depth=structure_depth(prompt),
        code_block_count=prompt.count("```") // 2,
        repeated_phrase_ratio=round(repeated_phrase_ratio, 4),
        context_tokens=context_tokens,
        instruction_tokens=instruction_tokens,
        context_to_instruction_ratio=round(ratio, 2),
        format_directive_count=len(format_directive_hits(segments)),
    )


def complexity_score(f: ComplexityFeatures) -> float:
    total = 0.0
    for name, weight in config.COMPLEXITY_WEIGHTS.items():
        value = float(getattr(f, name))
        total += weight * min(value / config.COMPLEXITY_CAPS[name], 1.0)
    return round(100.0 * total, 1)


def complexity_label(score: float) -> str:
    for upper, label in config.COMPLEXITY_BANDS:
        if score < upper:
            return label
    return "high"
