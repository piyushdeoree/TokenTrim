"""Cost calculation.

Terminology (kept distinct on purpose):
  input_tokens / output_tokens / total_tokens
  input_cost / output_cost / total_cost   -> from KNOWN token counts
  estimated_cost                          -> output tokens were PREDICTED

None of these are actual provider invoices.
"""
from __future__ import annotations

from typing import Optional

from . import config
from .models import CostBreakdown, CostEstimate, SavingsResult
from .pricing import get_pricing


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


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> CostBreakdown:
    """Cost from known (e.g. logged) token counts."""
    inp = _check_tokens(input_tokens, "input_tokens")
    out = _check_tokens(output_tokens, "output_tokens")
    p = get_pricing(model)
    input_cost = (inp / config.TOKENS_PER_MILLION) * p.input_price_per_million
    output_cost = (out / config.TOKENS_PER_MILLION) * p.output_price_per_million
    return CostBreakdown(
        model=model,
        input_tokens=inp,
        output_tokens=out,
        total_tokens=inp + out,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=input_cost + output_cost,
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
    p = get_pricing(model)
    orig_cost = orig / config.TOKENS_PER_MILLION * p.input_price_per_million
    opt_cost = opt / config.TOKENS_PER_MILLION * p.input_price_per_million
    return SavingsResult(
        model=model,
        original_tokens=orig,
        optimized_tokens=opt,
        tokens_saved=saved,
        optimization_percentage=round(pct, 4),
        original_input_cost=orig_cost,
        optimized_input_cost=opt_cost,
        input_cost_saved=orig_cost - opt_cost,
    ).to_dict()
