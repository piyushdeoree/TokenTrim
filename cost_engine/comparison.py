"""Model cost comparison across supported models."""
from __future__ import annotations

from typing import Iterable, Optional

from .calculator import _calculate_cost_with_pricing, _check_tokens
from .pricing import UnknownModelError, _get_pricing_cached, list_models, pricing_freshness


def compare_models(
    input_tokens: int,
    predicted_output_tokens: int,
    models: Optional[Iterable[str]] = None,
    *, cached_input_tokens: int = 0, context_window_required: Optional[int] = None,
    provider: Optional[str] = None, batch: bool = False, pricing_tier: Optional[str] = None,
) -> dict:
    """Estimated cost per model, sorted cheapest first.

    ``cheapest_model`` is the lowest ESTIMATED price only. It says nothing
    about quality, latency or suitability; use ``recommend_model`` for a
    constraint-aware suggestion.
    """
    names = list(models) if models is not None else list_models()
    if not names:
        raise ValueError("No models to compare")
    input_tokens = _check_tokens(input_tokens, "input_tokens")
    predicted_output_tokens = _check_tokens(predicted_output_tokens, "predicted_output_tokens")
    cached_input_tokens = _check_tokens(cached_input_tokens, "cached_input_tokens")
    if cached_input_tokens > input_tokens:
        raise ValueError("cached_input_tokens cannot exceed input_tokens")
    if context_window_required is not None:
        context_window_required = _check_tokens(context_window_required, "context_window_required")
    if not isinstance(batch, bool):
        raise TypeError("batch must be a boolean")
    if pricing_tier is not None and not isinstance(pricing_tier, str):
        raise TypeError("pricing_tier must be a string")
    if provider is not None and not isinstance(provider, str):
        raise TypeError("provider must be a string")
    unavailable = []
    rows = []
    for m in names:
        try:
            pricing = _get_pricing_cached(m)
        except UnknownModelError:
            unavailable.append({"model": m, "available": False, "reason": "pricing_unavailable"})
            continue
        if provider and pricing.provider.casefold()!=provider.casefold():
            unavailable.append({"model": m, "available": False, "reason": "provider_filter"})
            continue
        needed=max(input_tokens+predicted_output_tokens,context_window_required or 0)
        if pricing.context_window is not None and pricing.context_window<needed:
            unavailable.append({"model": m, "available": False, "reason": "context_window_too_small",
                                "context_window": pricing.context_window})
            continue
        supports_cache=pricing.cached_input_price_per_million is not None
        if cached_input_tokens and not supports_cache:
            unavailable.append({"model": m, "available": False, "reason": "cached_input_pricing_unavailable"})
            continue
        freshness=pricing_freshness(pricing)
        try:
            b = _calculate_cost_with_pricing(
                m, pricing, input_tokens, predicted_output_tokens,
                cached_input_tokens, 0,
                batch=batch, pricing_tier=pricing_tier,
            )
        except ValueError as exc:
            unavailable.append({"model": m, "available": False, "reason": str(exc)})
            continue
        rows.append({
            "model": m,
            "provider": pricing.provider,
            "estimated_cost": b.total_cost,
            "pricing_version":pricing.pricing_version,"pricing_status":pricing.pricing_status,
            "source_url":pricing.source_url,"context_window":pricing.context_window,
            "currency":pricing.currency,"input_cost":b.input_cost,"output_cost":b.output_cost,
            "cached_input_supported":supports_cache,
            "pricing_freshness":freshness,
            "verified_for_live_use": pricing.pricing_status == "official_verified" and not freshness["stale"],
        })
    rows.sort(key=lambda r: (r["estimated_cost"], r["model"]))
    cheapest = rows[0]["estimated_cost"] if rows else None
    for r in rows:
        if cheapest and cheapest > 0:
            r["relative_cost"] = r["estimated_cost"] / cheapest
        else:
            r["relative_cost"] = 1.0 if r["estimated_cost"] == 0 else None
    return {
        "input_tokens": int(input_tokens),
        "predicted_output_tokens": int(predicted_output_tokens),
        "models": rows,
        "unavailable_models": unavailable,
        "comparisons": [{"model": r["model"], "estimated_cost": r["estimated_cost"]} for r in rows],
        "cheapest_model": rows[0]["model"] if rows else None,
        "note": "Cheapest by estimated price only; not a quality-aware recommendation.",
    }
