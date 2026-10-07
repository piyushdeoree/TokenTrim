"""Simple, rule-based model recommendation.

This is a RECOMMENDATION, not a guaranteed optimal choice. It uses only the
pricing registry's (editable, subjective) ``quality_tier`` and context window;
it has not been validated against real task quality.

Rules:
  1. Drop models whose context window cannot fit input + predicted output
     (or the caller-supplied ``context_size``).
  2. Drop models whose quality_tier is below the required level.
     Complex task types (coding, analysis) get a floor of "medium".
  3. Pick the cheapest remaining model by estimated cost.
"""
from __future__ import annotations

from typing import Optional

from . import config
from .calculator import calculate_cost
from .pricing import get_pricing, list_models

_COMPLEX_TASKS = {"coding", "analysis"}


def recommend_model(
    input_tokens: int,
    predicted_output_tokens: int,
    task_type: Optional[str] = None,
    required_quality: str = "medium",
    current_model: Optional[str] = None,
    context_size: Optional[int] = None,
) -> dict:
    if required_quality not in config.QUALITY_LEVELS:
        raise ValueError(f"required_quality must be one of {list(config.QUALITY_LEVELS)}")
    min_tier = config.QUALITY_LEVELS[required_quality]
    floor_applied = False
    if task_type in _COMPLEX_TASKS and min_tier < config.QUALITY_LEVELS["medium"]:
        min_tier = config.QUALITY_LEVELS["medium"]
        floor_applied = True
    needed_context = max(int(context_size or 0), int(input_tokens) + int(predicted_output_tokens))

    eligible = []
    for m in list_models():
        p = get_pricing(m)
        if p.quality_tier < min_tier:
            continue
        if p.context_window is not None and p.context_window < needed_context:
            continue
        eligible.append((calculate_cost(m, input_tokens, predicted_output_tokens).total_cost, m))
    eligible.sort()

    base = {"is_recommendation_only": True,
            "disclaimer": "Recommendation based on price, quality tier and context fit; not a guaranteed optimal choice."}
    if not eligible:
        return {**base, "recommended_model": None, "estimated_saving": 0.0,
                "reason": "No supported model meets the quality and context requirements."}

    cost, best = eligible[0]
    saving, saving_pct = 0.0, 0.0
    if current_model:
        cur_cost = calculate_cost(current_model, input_tokens, predicted_output_tokens).total_cost
        saving = max(0.0, cur_cost - cost)
        saving_pct = (saving / cur_cost * 100.0) if cur_cost > 0 else 0.0

    reason = (f"Cheapest of {len(eligible)} model(s) meeting quality tier >= {min_tier}"
              f" and a context window of at least {needed_context} tokens.")
    if floor_applied:
        reason += f" Task type '{task_type}' raised the minimum quality to medium."
    if current_model and best == current_model:
        reason += " This is already your current model."
    elif current_model:
        reason += f" Estimated saving vs {current_model}: {saving:.6f} ({saving_pct:.1f}%)."
    return {**base, "recommended_model": best, "estimated_cost": cost,
            "estimated_saving": saving, "estimated_saving_pct": saving_pct,
            "reason": reason}
