"""Model cost comparison across supported models."""
from __future__ import annotations

from typing import Iterable, Optional

from .calculator import calculate_cost
from .pricing import get_pricing, list_models


def compare_models(
    input_tokens: int,
    predicted_output_tokens: int,
    models: Optional[Iterable[str]] = None,
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
        b = calculate_cost(m, input_tokens, predicted_output_tokens)
        rows.append({
            "model": m,
            "provider": get_pricing(m).provider,
            "estimated_cost": b.total_cost,
        })
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
