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
import math
from typing import Iterable, Optional

from . import config
from .models import CostBreakdown, CostEstimate, SavingsResult
from .pricing import UnknownModelError, _get_pricing_cached, get_pricing_version


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


def _compat_float(value: Decimal) -> float:
    """Convert a finite Decimal to the legacy float response without Infinity."""
    if not value.is_finite():
        raise ValueError("financial calculation produced a non-finite amount")
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise ValueError("financial amount exceeds the legacy numeric response range") from None
    if not math.isfinite(result):
        raise ValueError("financial amount exceeds the legacy numeric response range")
    return result


def calculate_cost(model: str, input_tokens: int, output_tokens: int, *,
                   cached_input_tokens: int = 0, cache_write_tokens: int = 0,
                   batch: bool = False, pricing_tier: Optional[str] = None,
                   pricing_version: Optional[int] = None) -> CostBreakdown:
    """Cost from known (e.g. logged) token counts."""
    inp = _check_tokens(input_tokens, "input_tokens")
    out = _check_tokens(output_tokens, "output_tokens")
    cached = _check_tokens(cached_input_tokens, "cached_input_tokens")
    cache_write = _check_tokens(cache_write_tokens, "cache_write_tokens")
    if cached + cache_write > inp:
        raise ValueError("cached_input_tokens + cache_write_tokens cannot exceed input_tokens")
    if not isinstance(batch, bool):
        raise TypeError("batch must be a boolean")
    p = get_pricing_version(model, pricing_version) if pricing_version is not None else _get_pricing_cached(model)
    return _calculate_cost_with_pricing(model, p, inp, out, cached, cache_write,
                                        batch=batch, pricing_tier=pricing_tier)


def _calculate_cost_with_pricing(model, p, inp, out, cached, cache_write, *, batch=False, pricing_tier=None):
    if pricing_tier is not None and not isinstance(pricing_tier, str):
        raise TypeError("pricing_tier must be a string")
    if not isinstance(batch, bool):
        raise TypeError("batch must be a boolean")
    selected = None
    requested_tier = pricing_tier or ("batch" if batch else None)
    if requested_tier:
        for tier in p.pricing_tiers or []:
            conditions = tier.get("conditions") or {}
            label = tier.get("tier") or conditions.get("service_tier")
            if isinstance(label, str) and label.casefold() == requested_tier.casefold():
                selected = tier
                break
    if batch and pricing_tier and pricing_tier.casefold() != "batch":
        raise ValueError("batch=True cannot be combined with a non-batch pricing_tier")
    if selected is not None:
        ordinary_rate = selected.get("input")
        output_rate = selected.get("output")
        cache_rate = selected.get("cached_input")
        cache_write_rate = selected.get("cache_write")
        if cache_write_rate is None:
            cache_write_rate = selected.get("cache_write_5m")
        if cache_write_rate is None:
            cache_write_rate = selected.get("cache_write_30m")
    elif requested_tier:
        if requested_tier.casefold() == "batch":
            ordinary_rate = p.batch_input_price_per_million
            output_rate = p.batch_output_price_per_million
            cache_rate = None
            cache_write_rate = None
        elif requested_tier.casefold() == "standard" and p.pricing_tier in (None, "standard"):
            ordinary_rate, output_rate = p.input_price_per_million, p.output_price_per_million
            cache_rate, cache_write_rate = p.cached_input_price_per_million, p.cache_write_price_per_million
        else:
            raise ValueError(f"Pricing tier {requested_tier!r} is unavailable for model {model!r}")
    else:
        ordinary_rate, output_rate = p.input_price_per_million, p.output_price_per_million
        cache_rate, cache_write_rate = p.cached_input_price_per_million, p.cache_write_price_per_million
    if ordinary_rate is None or output_rate is None:
        raise ValueError(f"Complete {requested_tier or 'standard'} pricing is unavailable for model {model!r}")
    if cached and cache_rate is None:
        raise ValueError(f"Cached input pricing is unavailable for model {model!r} in {requested_tier or 'standard'} tier")
    if cache_write and cache_write_rate is None:
        raise ValueError(f"Cache-write pricing is unavailable for model {model!r} in {requested_tier or 'standard'} tier")
    if batch and not (p.batch_input_price_per_million is not None and p.batch_output_price_per_million is not None):
        raise ValueError(f"Batch pricing is unavailable for model {model!r}")
    ordinary_rate = Decimal(str(ordinary_rate))
    output_rate = Decimal(str(output_rate))
    cache_rate = Decimal(str(cache_rate)) if cache_rate is not None else None
    cache_write_rate = Decimal(str(cache_write_rate)) if cache_write_rate is not None else None
    scale = Decimal(config.TOKENS_PER_MILLION)
    ordinary = Decimal(inp - cached - cache_write)
    input_cost_d = ordinary / scale * ordinary_rate
    if cached:
        input_cost_d += Decimal(cached) / scale * cache_rate
    output_cost_d = Decimal(out) / scale * output_rate
    other_d = Decimal(cache_write) / scale * (cache_write_rate or Decimal(0))
    # Keep Decimal through all arithmetic; floats are emitted only for backwards-compatible serialization.
    input_cost, output_cost, other = _compat_float(input_cost_d), _compat_float(output_cost_d), _compat_float(other_d)
    return CostBreakdown(
        model=model,
        input_tokens=inp,
        output_tokens=out,
        total_tokens=inp + out,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=_compat_float(input_cost_d + output_cost_d + other_d),
        provider=p.provider,
        pricing_version=p.pricing_version,
        cached_input_tokens=cached,
        cache_write_tokens=cache_write,
        batch=batch,
        pricing_tier=requested_tier or "standard",
        applied_input_rate=_compat_float(ordinary_rate),
        applied_output_rate=_compat_float(output_rate),
        other_charges=other,
        currency=p.currency,
        calculation_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def calculate_cost_batch(usage_records: Iterable[dict]) -> list[dict]:
    """Calculate a batch independently, reusing one pricing snapshot per key.

    Each output includes its input index and optional caller ``id``. Invalid
    records return an error entry while valid records continue processing.
    """
    results = []
    pricing_cache = {}
    for index, record in enumerate(usage_records):
        record_id = record.get("id") if isinstance(record, dict) else None
        try:
            if not isinstance(record, dict):
                raise TypeError("usage record must be a mapping")
            model = record.get("model")
            if not isinstance(model, str) or not model:
                raise ValueError("model is required")
            version = record.get("pricing_version")
            key = (model, version)
            if key not in pricing_cache:
                pricing_cache[key] = (get_pricing_version(model, version) if version is not None
                                      else _get_pricing_cached(model))
            inp = _check_tokens(record.get("input_tokens"), "input_tokens")
            out = _check_tokens(record.get("output_tokens"), "output_tokens")
            cached = _check_tokens(record.get("cached_input_tokens", 0), "cached_input_tokens")
            write = _check_tokens(record.get("cache_write_tokens", 0), "cache_write_tokens")
            if cached + write > inp:
                raise ValueError("cached_input_tokens + cache_write_tokens cannot exceed input_tokens")
            batch = record.get("batch", False)
            if not isinstance(batch, bool):
                raise TypeError("batch must be a boolean")
            breakdown = _calculate_cost_with_pricing(
                model, pricing_cache[key], inp, out, cached, write,
                batch=batch, pricing_tier=record.get("pricing_tier"),
            )
            # CostBreakdown contains scalar/immutable fields, so a shallow dict
            # copy is sufficient and avoids dataclasses.asdict's recursive copy.
            results.append({"index": index, "id": record_id, "ok": True,
                            **breakdown.__dict__})
        except (ValueError, TypeError, KeyError) as exc:
            results.append({"index": index, "id": record_id, "ok": False,
                            "error": {"type": type(exc).__name__, "message": str(exc)}})
    return results


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
    if tokens_saved is not None:
        provided_saved = _check_tokens(tokens_saved, "tokens_saved")
        if provided_saved != saved:
            raise ValueError(f"tokens_saved ({provided_saved}) inconsistent with original-optimized ({saved})")
    pct_d = (Decimal(saved) / Decimal(orig) * Decimal(100)) if orig else Decimal(0)
    if optimization_percentage is not None:
        try:
            provided_pct = Decimal(str(optimization_percentage))
        except Exception:
            raise ValueError("optimization_percentage must be a finite non-negative number") from None
        if not provided_pct.is_finite() or provided_pct < 0:
            raise ValueError("optimization_percentage must be a finite non-negative number")
        if abs(provided_pct - pct_d) > Decimal("0.5"):
            raise ValueError(f"optimization_percentage ({optimization_percentage}) inconsistent with computed {pct_d:.2f}")
    pct = _compat_float(pct_d)
    p = _get_pricing_cached(model)
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
        original_input_cost=_compat_float(orig_cost_d),
        optimized_input_cost=_compat_float(opt_cost_d),
        input_cost_saved=_compat_float(orig_cost_d - opt_cost_d),
    ).to_dict()
