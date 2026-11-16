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
from .calculator import _calculate_cost_with_pricing, _check_tokens
from .pricing import _get_pricing_cached, list_models, pricing_freshness

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
    input_tokens = _check_tokens(input_tokens, "input_tokens")
    predicted_output_tokens = _check_tokens(predicted_output_tokens, "predicted_output_tokens")
    if context_size is not None:
        context_size = _check_tokens(context_size, "context_size")
    min_tier = config.QUALITY_LEVELS[required_quality]
    floor_applied = False
    if task_type in _COMPLEX_TASKS and min_tier < config.QUALITY_LEVELS["medium"]:
        min_tier = config.QUALITY_LEVELS["medium"]
        floor_applied = True
    needed_context = max(context_size or 0, input_tokens + predicted_output_tokens)

    eligible = []
    for m in list_models():
        p = _get_pricing_cached(m)
        if p.quality_tier < min_tier:
            continue
        if p.context_window is not None and p.context_window < needed_context:
            continue
        cost = _calculate_cost_with_pricing(m, p, input_tokens, predicted_output_tokens, 0, 0).total_cost
        eligible.append((cost, m, p))
    eligible.sort(key=lambda row: (row[0], row[1]))

    base = {"is_recommendation_only": True,
            "disclaimer": "Recommendation based on price, quality tier and context fit; not a guaranteed optimal choice."}
    if not eligible:
        return {**base, "recommended_model": None, "estimated_saving": 0.0,
                "reason": "No supported model meets the quality and context requirements."}

    cost, best, best_pricing = eligible[0]
    saving, saving_pct = 0.0, 0.0
    if current_model:
        current_pricing = _get_pricing_cached(current_model)
        cur_cost = _calculate_cost_with_pricing(current_model, current_pricing,
                                               input_tokens, predicted_output_tokens, 0, 0).total_cost
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
            "pricing_status": best_pricing.pricing_status,
            "pricing_freshness": pricing_freshness(best_pricing),
            "verified_for_live_use": best_pricing.pricing_status == "official_verified" and not pricing_freshness(best_pricing)["stale"],
            "quality_tier_basis": "editable subjective metadata; not a measured model evaluation",
            "reason": reason}
