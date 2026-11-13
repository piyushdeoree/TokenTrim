"""Model cost comparison across supported models."""
from __future__ import annotations

from typing import Iterable, Optional

from .calculator import calculate_cost
from .pricing import get_pricing, list_models, pricing_freshness


def compare_models(
    input_tokens: int,
    predicted_output_tokens: int,
    models: Optional[Iterable[str]] = None,
    *, cached_input_tokens: int = 0, context_window_required: Optional[int] = None,
    provider: Optional[str] = None,
) -> dict:
    """Estimated cost per model, sorted cheapest first.

    ``cheapest_model`` is the lowest ESTIMATED price only. It says nothing
    about quality, latency or suitability; use ``recommend_model`` for a
    constraint-aware suggestion.
    """
    names = list(models) if models is not None else list_models()
    if not names:
        raise ValueError("No models to compare")
    rows = []
    for m in names:
        pricing=get_pricing(m)
        if provider and pricing.provider.lower()!=provider.lower(): continue
        needed=max(input_tokens+predicted_output_tokens,context_window_required or 0)
        if pricing.context_window is not None and pricing.context_window<needed: continue
        supports_cache=pricing.cached_input_price_per_million is not None
        freshness=pricing_freshness(pricing)
        b = calculate_cost(m, input_tokens, predicted_output_tokens,
                           cached_input_tokens=cached_input_tokens if supports_cache else 0)
        rows.append({
            "model": m,
            "provider": pricing.provider,
            "estimated_cost": b.total_cost,
            "pricing_version":pricing.pricing_version,"pricing_status":pricing.pricing_status,
            "source_url":pricing.source_url,"context_window":pricing.context_window,
            "currency":pricing.currency,"input_cost":b.input_cost,"output_cost":b.output_cost,
            "cached_input_supported":supports_cache,
            "pricing_freshness":freshness,
        })
    if not rows: raise ValueError("No models with applicable pricing and context compatibility")
    rows.sort(key=lambda r: (r["estimated_cost"], r["model"]))
    cheapest = rows[0]["estimated_cost"]
    for r in rows:
        if cheapest > 0:
            r["relative_cost"] = r["estimated_cost"] / cheapest
        else:
            r["relative_cost"] = 1.0 if r["estimated_cost"] == 0 else None
    return {
        "input_tokens": int(input_tokens),
        "predicted_output_tokens": int(predicted_output_tokens),
        "models": rows,
        "comparisons": [{"model": r["model"], "estimated_cost": r["estimated_cost"]} for r in rows],
        "cheapest_model": rows[0]["model"],
        "note": "Cheapest by estimated price only; not a quality-aware recommendation.",
    }
