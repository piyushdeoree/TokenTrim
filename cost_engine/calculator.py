"""Cost calculation.

Terminology (kept distinct on purpose):
  input_tokens / output_tokens / total_tokens
  input_cost / output_cost / total_cost   -> from KNOWN token counts
  estimated_cost                          -> output tokens were PREDICTED

None of these are actual provider invoices.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from . import config
from .models import CostBreakdown, CostEstimate, SavingsResult
from .pricing import get_pricing_decimal, get_pricing_version


def _check_tokens(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite")
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    if int(value) != value:
        raise ValueError(f"{name} must be a whole number, got {value}")
    return int(value)


def calculate_cost(model: str, input_tokens: int, output_tokens: int, *,
                   cached_input_tokens: int = 0, cache_write_tokens: int = 0,
                   batch: bool = False, pricing_tier: Optional[str] = None,
                   pricing_version: Optional[int] = None) -> CostBreakdown:
    """Cost from known (e.g. logged) token counts."""
    inp = _check_tokens(input_tokens, "input_tokens")
    out = _check_tokens(output_tokens, "output_tokens")
    cached = _check_tokens(cached_input_tokens, "cached_input_tokens")
    cache_write = _check_tokens(cache_write_tokens, "cache_write_tokens")
    if cached > inp:
        raise ValueError("cached_input_tokens cannot exceed input_tokens")
    p = get_pricing_version(model,pricing_version) if pricing_version is not None else get_pricing_decimal(model)
    if pricing_tier is not None and p.pricing_tier not in (None, pricing_tier):
        raise ValueError(f"Model {model!r} does not have pricing tier {pricing_tier!r}")
    ordinary_rate = p.batch_input_price_per_million if batch and p.batch_input_price_per_million is not None else p.input_price_per_million
    output_rate = p.batch_output_price_per_million if batch and p.batch_output_price_per_million is not None else p.output_price_per_million
    cache_rate = p.cached_input_price_per_million
    if cached and cache_rate is None:
        raise ValueError(f"Cached input pricing is unavailable for model {model!r}")
    if cache_write and p.cache_write_price_per_million is None:
        raise ValueError(f"Cache-write pricing is unavailable for model {model!r}")
    scale = Decimal(config.TOKENS_PER_MILLION)
    ordinary = Decimal(inp - cached)
    input_cost_d = ordinary / scale * Decimal(str(ordinary_rate))
    if cached:
        input_cost_d += Decimal(cached) / scale * Decimal(str(cache_rate))
    output_cost_d = Decimal(out) / scale * Decimal(str(output_rate))
    other_d = Decimal(cache_write) / scale * Decimal(str(p.cache_write_price_per_million or 0))
    # Keep Decimal through all arithmetic; floats are emitted only for backwards-compatible serialization.
    input_cost, output_cost, other = float(input_cost_d), float(output_cost_d), float(other_d)
    return CostBreakdown(
        model=model,
        input_tokens=inp,
        output_tokens=out,
        total_tokens=inp + out,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=float(input_cost_d + output_cost_d + other_d),
        provider=p.provider,
        pricing_version=p.pricing_version,
        cached_input_tokens=cached,
        applied_input_rate=float(ordinary_rate),
        applied_output_rate=float(output_rate),
        other_charges=other,
        currency=p.currency,
        calculation_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def estimate_cost(
    model: str,
    input_tokens: int,
    predicted_output_tokens: int,
    prediction_source: str = "caller_supplied",
) -> dict:
    """ESTIMATED cost using predicted output tokens.

    Returns the spec section 2 shape (plus ``prediction_source``).
    Use ``CostEstimate.to_api_dict()`` via ``estimate_cost_api`` for section 10.
    """
    b = calculate_cost(model, input_tokens, predicted_output_tokens)
    return CostEstimate(
        model=model,
        input_tokens=b.input_tokens,
        predicted_output_tokens=b.output_tokens,
        total_tokens=b.total_tokens,
        input_cost=b.input_cost,
        output_cost=b.output_cost,
        estimated_cost=b.total_cost,
        prediction_source=prediction_source,
    ).to_dict()


def estimate_cost_api(
    model: str,
    input_tokens: int,
    predicted_output_tokens: int,
    prediction_source: str = "caller_supplied",
) -> dict:
    """Same as estimate_cost but with the section 10 field names."""
    b = calculate_cost(model, input_tokens, predicted_output_tokens)
    return CostEstimate(
        model=model,
        input_tokens=b.input_tokens,
        predicted_output_tokens=b.output_tokens,
        total_tokens=b.total_tokens,
        input_cost=b.input_cost,
        output_cost=b.output_cost,
        estimated_cost=b.total_cost,
        prediction_source=prediction_source,
    ).to_api_dict()


def calculate_savings(
    model: str,
    original_tokens: int,
    optimized_tokens: int,
    tokens_saved: Optional[int] = None,
    optimization_percentage: Optional[float] = None,
) -> dict:
    """Input-cost savings from Person 1's prompt optimization output.

    Only INPUT cost is affected here: optimizing the prompt does not change
    the (predicted) output length in this module.
    """
    orig = _check_tokens(original_tokens, "original_tokens")
    opt = _check_tokens(optimized_tokens, "optimized_tokens")
    if opt > orig:
        raise ValueError("optimized_tokens cannot exceed original_tokens")
    saved = orig - opt
    if tokens_saved is not None and int(tokens_saved) != saved:
        raise ValueError(
            f"tokens_saved ({tokens_saved}) inconsistent with original-optimized ({saved})"
        )
    pct = (saved / orig * 100.0) if orig else 0.0
    if optimization_percentage is not None and abs(optimization_percentage - pct) > 0.5:
        raise ValueError(
            f"optimization_percentage ({optimization_percentage}) inconsistent with computed {pct:.2f}"
        )
    p = get_pricing_decimal(model)
    scale = Decimal(config.TOKENS_PER_MILLION)
    rate = p.input_price_per_million
    orig_cost_d = Decimal(orig) / scale * rate
    opt_cost_d = Decimal(opt) / scale * rate
    return SavingsResult(
        model=model,
        original_tokens=orig,
        optimized_tokens=opt,
        tokens_saved=saved,
        optimization_percentage=round(pct, 4),
        original_input_cost=float(orig_cost_d),
        optimized_input_cost=float(opt_cost_d),
        input_cost_saved=float(orig_cost_d - opt_cost_d),
    ).to_dict()
