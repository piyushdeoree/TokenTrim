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
from .currency import is_valid_currency, normalize_currency
from .models import ActualCostResult, CostBreakdown, CostEstimate, SavingsResult
from .pricing import (
    UnknownModelError, _get_pricing_cached, get_pricing_version,
    is_supported_provider, normalize_provider,
)


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


def _validate_actual_tokens(value, name: str) -> int:
    """Strictly validate provider-reported actual token counts."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, got bool")
    if not isinstance(value, (int, float, Decimal)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        if int(value) != value:
            raise ValueError(f"{name} must be a whole number, got {value}")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"{name} must be finite")
        if int(value) != value:
            raise ValueError(f"{name} must be a whole number, got {value}")
    val_int = int(value)
    if val_int < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return val_int


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


def calculate_cost_decimal(model: str, input_tokens: int, output_tokens: int, *,
                           cached_input_tokens: int = 0, cache_write_tokens: int = 0,
                           batch: bool = False, pricing_tier: Optional[str] = None,
                           pricing_version: Optional[int] = None) -> Decimal:
    """Return the exact Decimal total for internal integrations and persistence."""
    inp = _check_tokens(input_tokens, "input_tokens")
    out = _check_tokens(output_tokens, "output_tokens")
    cached = _check_tokens(cached_input_tokens, "cached_input_tokens")
    cache_write = _check_tokens(cache_write_tokens, "cache_write_tokens")
    if cached + cache_write > inp:
        raise ValueError("cached_input_tokens + cache_write_tokens cannot exceed input_tokens")
    if not isinstance(batch, bool):
        raise TypeError("batch must be a boolean")
    p = get_pricing_version(model, pricing_version) if pricing_version is not None else _get_pricing_cached(model)
    amounts = _calculate_decimal_amounts(model, p, inp, out, cached, cache_write,
                                         batch=batch, pricing_tier=pricing_tier)
    return amounts["total_cost"]


def _calculate_decimal_amounts(model, p, inp, out, cached, cache_write, *, batch=False, pricing_tier=None):
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
    return {
        "input_cost": input_cost_d,
        "output_cost": output_cost_d,
        "other_charges": other_d,
        "total_cost": input_cost_d + output_cost_d + other_d,
        "input_rate": ordinary_rate,
        "output_rate": output_rate,
        "requested_tier": requested_tier or "standard",
    }


def _calculate_cost_with_pricing(model, p, inp, out, cached, cache_write, *, batch=False, pricing_tier=None):
    amounts = _calculate_decimal_amounts(model, p, inp, out, cached, cache_write,
                                         batch=batch, pricing_tier=pricing_tier)
    # Keep Decimal through all arithmetic; floats are emitted only for backwards-compatible serialization.
    input_cost = _compat_float(amounts["input_cost"])
    output_cost = _compat_float(amounts["output_cost"])
    other = _compat_float(amounts["other_charges"])
    return CostBreakdown(
        model=model,
        input_tokens=inp,
        output_tokens=out,
        total_tokens=inp + out,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=_compat_float(amounts["total_cost"]),
        provider=p.provider,
        pricing_version=p.pricing_version,
        cached_input_tokens=cached,
        cache_write_tokens=cache_write,
        batch=batch,
        pricing_tier=amounts["requested_tier"],
        applied_input_rate=_compat_float(amounts["input_rate"]),
        applied_output_rate=_compat_float(amounts["output_rate"]),
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
        optimization_percentage=pct,
        original_input_cost=_compat_float(orig_cost_d),
        optimized_input_cost=_compat_float(opt_cost_d),
        input_cost_saved=_compat_float(orig_cost_d - opt_cost_d),
    ).to_dict()


def calculate_actual_cost(
    provider: str,
    model: str,
    actual_input_tokens: Optional[int] = None,
    actual_output_tokens: Optional[int] = None,
    *,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cached_input_tokens: int = 0,
    cache_write_tokens: int = 0,
    currency: Optional[str] = None,
    pricing_tier: Optional[str] = None,
    pricing_version: Optional[int] = None,
    additional_usage: Optional[dict] = None,
    raise_on_error: bool = False,
    **kwargs,
) -> ActualCostResult:
    """Calculate actual execution cost for BYOK requests using real provider-reported usage.

    Parameters:
        provider: Provider identifier ('openai', 'google', 'gemini', 'anthropic', 'claude').
        model: Exact model identifier (e.g. 'gpt-4o', 'claude-sonnet', 'gemini-pro').
        actual_input_tokens: Actual input token count reported by provider (or via input_tokens).
        actual_output_tokens: Actual output token count reported by provider (or via output_tokens).
        cached_input_tokens: Optional cached prompt input tokens reported by provider.
        cache_write_tokens: Optional cache write prompt tokens reported by provider.
        currency: Optional ISO 4217 currency code (e.g. 'USD').
        pricing_tier: Optional provider pricing tier (e.g. 'standard', 'batch').
        pricing_version: Optional historical pricing catalog version.
        additional_usage: Optional dict of extra provider-reported usage categories.
        raise_on_error: If True, raise exceptions on errors instead of returning an error result.
        **kwargs: Extra usage parameters (e.g. reasoning_tokens, batch=True).

    Returns:
        ActualCostResult: Standardized result structure.
    """
    # 1. Resolve and validate token counts
    raw_inp = actual_input_tokens if actual_input_tokens is not None else input_tokens
    raw_out = actual_output_tokens if actual_output_tokens is not None else output_tokens

    if actual_input_tokens is not None and input_tokens is not None and actual_input_tokens != input_tokens:
        err = "actual_input_tokens and input_tokens conflict"
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=str(provider), model=str(model), input_tokens=None, output_tokens=None, total_tokens=None, actual_cost=None, currency=currency, pricing_status="invalid_usage_data", pricing_verification=None, error_details=err)

    if actual_output_tokens is not None and output_tokens is not None and actual_output_tokens != output_tokens:
        err = "actual_output_tokens and output_tokens conflict"
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=str(provider), model=str(model), input_tokens=None, output_tokens=None, total_tokens=None, actual_cost=None, currency=currency, pricing_status="invalid_usage_data", pricing_verification=None, error_details=err)

    if raw_inp is None or raw_out is None:
        err = "Both input and output token counts are required"
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=str(provider), model=str(model), input_tokens=None, output_tokens=None, total_tokens=None, actual_cost=None, currency=currency, pricing_status="invalid_usage_data", pricing_verification=None, error_details=err)

    try:
        inp = _validate_actual_tokens(raw_inp, "input_tokens")
        out = _validate_actual_tokens(raw_out, "output_tokens")
        cached = _validate_actual_tokens(cached_input_tokens, "cached_input_tokens")
        cache_write = _validate_actual_tokens(cache_write_tokens, "cache_write_tokens")
        if cached + cache_write > inp:
            raise ValueError("cached_input_tokens + cache_write_tokens cannot exceed input_tokens")
    except (ValueError, TypeError) as exc:
        if raise_on_error: raise
        return ActualCostResult(provider=str(provider), model=str(model), input_tokens=None, output_tokens=None, total_tokens=None, actual_cost=None, currency=currency, pricing_status="invalid_usage_data", pricing_verification=None, error_details=str(exc))

    # 2. Validate Provider
    if not isinstance(provider, str) or not provider.strip():
        err = "Provider identifier must be a non-empty string"
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=str(provider), model=str(model), input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=currency, pricing_status="invalid_provider", pricing_verification=None, error_details=err)

    if not is_supported_provider(provider):
        err = f"Provider {provider!r} is not supported. Supported providers: ['openai', 'google', 'anthropic']"
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=str(provider), model=str(model), input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=currency, pricing_status="unsupported_provider", pricing_verification=None, error_details=err)

    canonical_prov = normalize_provider(provider)

    # 3. Validate Model and Lookup Pricing
    if not isinstance(model, str) or not model.strip():
        err = "Model identifier must be a non-empty string"
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=canonical_prov, model=str(model), input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=currency, pricing_status="model_not_registered", pricing_verification="unavailable", error_details=err)

    model_clean = model.strip()
    try:
        if pricing_version is not None:
            p = get_pricing_version(model_clean, pricing_version)
        else:
            p = _get_pricing_cached(model_clean)
    except UnknownModelError:
        err = f"Model {model_clean!r} is not registered in the pricing catalogue."
        if raise_on_error: raise
        return ActualCostResult(provider=canonical_prov, model=model_clean, input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=currency, pricing_status="model_not_registered", pricing_verification="unavailable", error_details=err)

    # Check that model belongs to provider
    model_canonical_prov = normalize_provider(p.provider)
    if canonical_prov != model_canonical_prov:
        err = f"Model {model_clean!r} is registered under provider {p.provider!r}, not {provider!r}."
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=canonical_prov, model=model_clean, input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=p.currency, pricing_status="model_not_registered", pricing_verification="unavailable", error_details=err)

    # Check that basic rate info exists
    if p.input_price_per_million is None or p.output_price_per_million is None:
        err = f"Complete pricing information is unavailable for model {model_clean!r}."
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=canonical_prov, model=model_clean, input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=p.currency, pricing_status="pricing_unavailable", pricing_verification=p.pricing_status, error_details=err)

    # 4. Currency validation
    effective_currency = p.currency
    if currency is not None:
        if not is_valid_currency(currency):
            err = f"Invalid ISO 4217 currency code: {currency!r}"
            if raise_on_error: raise ValueError(err)
            return ActualCostResult(provider=canonical_prov, model=model_clean, input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=str(currency), pricing_status="invalid_currency", pricing_verification=p.pricing_status, error_details=err)
        norm_currency = currency.strip().upper()
        if norm_currency != p.currency.upper():
            err = f"Requested currency '{norm_currency}' does not match model pricing currency '{p.currency}'; automatic exchange rate conversion is not performed in BYOK cost calculation."
            if raise_on_error: raise ValueError(err)
            return ActualCostResult(provider=canonical_prov, model=model_clean, input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=norm_currency, pricing_status="currency_mismatch", pricing_verification=p.pricing_status, error_details=err)
        effective_currency = norm_currency

    # 5. Unsupported pricing structures & categories
    unsupported = []
    if additional_usage:
        if not isinstance(additional_usage, dict):
            err = "additional_usage must be a dictionary"
            if raise_on_error: raise TypeError(err)
            return ActualCostResult(provider=canonical_prov, model=model_clean, input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=effective_currency, pricing_status="invalid_usage_data", pricing_verification=p.pricing_status, error_details=err)
        for k, v in additional_usage.items():
            if v and (not isinstance(v, (int, float, Decimal)) or v > 0):
                unsupported.append(str(k))
    known_unsupported_keys = ("reasoning_tokens", "thinking_tokens", "audio_tokens", "search_tokens", "image_tokens")
    for k in known_unsupported_keys:
        if k in kwargs and kwargs[k]:
            unsupported.append(k)

    if unsupported:
        err = f"Provider reported unsupported usage categories: {sorted(unsupported)}. Standard token pricing does not cover these components."
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=canonical_prov, model=model_clean, input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=effective_currency, pricing_status="unsupported_pricing_structure", pricing_verification=p.pricing_status, unsupported_components=sorted(unsupported), error_details=err)

    if cached and p.cached_input_price_per_million is None:
        err = f"Cached input pricing is unavailable for model {model_clean!r}"
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=canonical_prov, model=model_clean, input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=effective_currency, pricing_status="unsupported_pricing_structure", pricing_verification=p.pricing_status, unsupported_components=["cached_input_tokens"], error_details=err)

    if cache_write and p.cache_write_price_per_million is None:
        err = f"Cache write pricing is unavailable for model {model_clean!r}"
        if raise_on_error: raise ValueError(err)
        return ActualCostResult(provider=canonical_prov, model=model_clean, input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=effective_currency, pricing_status="unsupported_pricing_structure", pricing_verification=p.pricing_status, unsupported_components=["cache_write_tokens"], error_details=err)

    is_batch = kwargs.get("batch", False) or (pricing_tier and pricing_tier.casefold() == "batch")
    if is_batch:
        if p.batch_input_price_per_million is None or p.batch_output_price_per_million is None:
            err = f"Batch pricing is unavailable for model {model_clean!r}"
            if raise_on_error: raise ValueError(err)
            return ActualCostResult(provider=canonical_prov, model=model_clean, input_tokens=inp, output_tokens=out, total_tokens=inp+out, actual_cost=None, currency=effective_currency, pricing_status="unsupported_pricing_structure", pricing_verification=p.pricing_status, unsupported_components=["batch_pricing"], error_details=err)
        input_rate = Decimal(str(p.batch_input_price_per_million))
        output_rate = Decimal(str(p.batch_output_price_per_million))
        cached_rate = Decimal(0)
        cache_write_rate = Decimal(0)
    else:
        input_rate = Decimal(str(p.input_price_per_million))
        output_rate = Decimal(str(p.output_price_per_million))
        cached_rate = Decimal(str(p.cached_input_price_per_million)) if p.cached_input_price_per_million is not None else Decimal(0)
        cache_write_rate = Decimal(str(p.cache_write_price_per_million)) if p.cache_write_price_per_million is not None else Decimal(0)

    # 6. Decimal arithmetic without intermediate rounding
    scale = Decimal(config.TOKENS_PER_MILLION)
    ordinary = Decimal(inp - cached - cache_write)
    input_cost_d = ordinary / scale * input_rate
    if cached:
        input_cost_d += Decimal(cached) / scale * cached_rate
    output_cost_d = Decimal(out) / scale * output_rate
    other_d = Decimal(cache_write) / scale * cache_write_rate
    actual_cost_d = input_cost_d + output_cost_d + other_d

    warnings = [
        "Calculation covers standard input/output tokens (and cached input if specified). "
        "Provider-specific billing categories such as reasoning tokens, audio, web search tools, "
        "or regional surcharges are not included in this calculation."
    ]

    return ActualCostResult(
        provider=canonical_prov,
        model=model_clean,
        input_tokens=inp,
        output_tokens=out,
        total_tokens=inp + out,
        actual_cost=_compat_float(actual_cost_d),
        currency=effective_currency,
        pricing_status="available",
        pricing_verification=p.pricing_status,
        actual_cost_decimal=actual_cost_d,
        input_cost=_compat_float(input_cost_d),
        output_cost=_compat_float(output_cost_d),
        input_cost_decimal=input_cost_d,
        output_cost_decimal=output_cost_d,
        cached_input_tokens=cached,
        cache_write_tokens=cache_write,
        pricing_unit=getattr(p, "pricing_unit", "per 1,000,000 tokens"),
        pricing_source=p.source_url,
        last_verified=p.last_verified,
        pricing_version=p.pricing_version,
        estimate_type="actual",
        calculation_timestamp=datetime.now(timezone.utc).isoformat(),
        applied_input_rate=_compat_float(input_rate),
        applied_output_rate=_compat_float(output_rate),
        unsupported_components=[],
        error_details=None,
        warnings=warnings,
    )


def calculate_actual_cost_decimal(
    provider: str,
    model: str,
    actual_input_tokens: Optional[int] = None,
    actual_output_tokens: Optional[int] = None,
    *,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cached_input_tokens: int = 0,
    cache_write_tokens: int = 0,
    currency: Optional[str] = None,
    pricing_tier: Optional[str] = None,
    pricing_version: Optional[int] = None,
    additional_usage: Optional[dict] = None,
    raise_on_error: bool = True,
    **kwargs,
) -> Optional[Decimal]:
    """Calculate exact Decimal actual cost for persistence and financial precision."""
    res = calculate_actual_cost(
        provider=provider,
        model=model,
        actual_input_tokens=actual_input_tokens,
        actual_output_tokens=actual_output_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_write_tokens=cache_write_tokens,
        currency=currency,
        pricing_tier=pricing_tier,
        pricing_version=pricing_version,
        additional_usage=additional_usage,
        raise_on_error=raise_on_error,
        **kwargs,
    )
    if res.pricing_status != "available":
        if raise_on_error:
            raise ValueError(res.error_details or f"Cost calculation unavailable: {res.pricing_status}")
        return None
    return res.actual_cost_decimal


def calculate_actual_cost_batch(
    execution_records: Iterable[dict],
    *,
    raise_on_error: bool = False,
) -> list[dict]:
    """Calculate actual costs for a batch of execution usage records."""
    results = []
    for index, record in enumerate(execution_records):
        record_id = record.get("id") if isinstance(record, dict) else None
        try:
            if not isinstance(record, dict):
                raise TypeError("execution record must be a mapping")
            provider = record.get("provider")
            model = record.get("model")
            inp = record.get("actual_input_tokens", record.get("input_tokens"))
            out = record.get("actual_output_tokens", record.get("output_tokens"))
            cached = record.get("cached_input_tokens", 0)
            write = record.get("cache_write_tokens", 0)
            curr = record.get("currency")
            tier = record.get("pricing_tier")
            version = record.get("pricing_version")
            add_usage = record.get("additional_usage")
            res = calculate_actual_cost(
                provider=provider,
                model=model,
                actual_input_tokens=inp,
                actual_output_tokens=out,
                cached_input_tokens=cached,
                cache_write_tokens=write,
                currency=curr,
                pricing_tier=tier,
                pricing_version=version,
                additional_usage=add_usage,
                raise_on_error=raise_on_error,
            )
            results.append({"index": index, "id": record_id, **res.to_dict()})
        except Exception as exc:
            if raise_on_error:
                raise
            results.append({
                "index": index,
                "id": record_id,
                "provider": record.get("provider") if isinstance(record, dict) else None,
                "model": record.get("model") if isinstance(record, dict) else None,
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "actual_cost": None,
                "currency": None,
                "pricing_status": "invalid_usage_data",
                "pricing_verification": None,
                "error_details": str(exc),
            })
    return results


calculate_execution_cost = calculate_actual_cost
calculate_execution_cost_decimal = calculate_actual_cost_decimal

