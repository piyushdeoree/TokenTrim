"""Adapter around Person 2's `cost_engine`."""

import importlib
import logging

from app.core.config import settings
from app.core.exceptions import MLServiceError

log = logging.getLogger(__name__)


def _engine():
    if settings.USE_STUB_ENGINES:
        from app.services import stubs
        return stubs.cost_engine

    try:
        return importlib.import_module("cost_engine")
    except ImportError:
        log.exception("cost_engine could not be imported")
        raise MLServiceError(
            "Cost estimation service is currently unavailable."
        )


def _call(name: str, **kwargs):
    engine = _engine()

    try:
        return getattr(engine, name)(**kwargs)
    except Exception:
        log.exception("cost_engine.%s failed", name)
        raise MLServiceError(
            "Cost estimation failed. Please try again later."
        )


def predict_output_tokens(
    prompt: str,
    model: str,
    input_tokens: int,
) -> int:
    result = _call(
        "predict_output_tokens",
        input_tokens=input_tokens,
        model=model,
        prompt_text=prompt,
    )

    if isinstance(result, dict):
        value = result.get("predicted_output_tokens")
    else:
        value = result

    if value is None:
        raise MLServiceError(
            "Cost engine returned no predicted output token count."
        )

    return max(0, int(value))


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_1k: float,
    output_price_per_1k: float,
    model: str,
) -> float:
    result = _call(
        "estimate_cost",
        model=model,
        input_tokens=input_tokens,
        predicted_output_tokens=output_tokens,
    )

    if isinstance(result, dict):
        value = result.get("estimated_cost")
    else:
        value = result

    if value is None:
        raise MLServiceError(
            "Cost engine returned no estimated cost."
        )

    return float(value)


def forecast_cost(
    daily_costs: list[float],
    horizon_days: int,
) -> list[float]:
    result = _call(
        "forecast_cost",
        historical_cost=daily_costs,
        forecast_period=f"{horizon_days}_days",
    )

    if isinstance(result, dict):
        # Person 2's engine returns a dictionary. Extract the forecast
        # sequence from the available result field.
        value = (
            result.get("forecast")
            or result.get("forecasted_costs")
            or result.get("predictions")
        )
    else:
        value = result

    if value is None:
        raise MLServiceError(
            "Cost engine returned no forecast values."
        )

    return [float(x) for x in value]