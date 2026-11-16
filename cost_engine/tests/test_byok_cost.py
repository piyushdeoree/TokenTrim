"""Comprehensive test suite for BYOK (Bring Your Own API Key) actual execution cost calculation."""
from decimal import Decimal
import math
import pytest

from cost_engine import (
    ActualCostResult,
    calculate_actual_cost,
    calculate_actual_cost_decimal,
    calculate_actual_cost_batch,
    calculate_execution_cost,
    calculate_execution_cost_decimal,
    estimate_cost,
    compare_models,
    calculate_savings,
    get_pricing,
    get_pricing_decimal,
    upsert_pricing,
    list_models,
    is_valid_currency,
    normalize_currency,
    is_supported_provider,
    normalize_provider,
    ModelPricing,
    UnknownModelError,
)


# ==============================================================================
# 1. Standard Input/Output Actual Cost Calculations
# ==============================================================================

def test_actual_cost_standard_openai():
    """Verify standard formula: (in * rate_in + out * rate_out) / 1,000,000 for OpenAI."""
    # gpt-4o: in=2.50, out=10.00
    res = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=1_000,
        actual_output_tokens=500,
    )
    assert res.pricing_status == "available"
    assert res.pricing_verification == "manual_unverified"
    assert res.provider == "openai"
    assert res.model == "gpt-4o"
    assert res.input_tokens == 1_000
    assert res.output_tokens == 500
    assert res.total_tokens == 1_500
    assert res.currency == "USD"
    assert res.estimate_type == "actual"

    # Expected exact Decimal: (1000 * 2.50 + 500 * 10.00) / 1_000_000 = (2500 + 5000) / 1e6 = 0.0075
    expected_cost = Decimal("0.0075")
    assert res.actual_cost_decimal == expected_cost
    assert math.isclose(res.actual_cost, 0.0075)
    assert res.input_cost_decimal == Decimal("0.0025")
    assert res.output_cost_decimal == Decimal("0.0050")
    assert math.isclose(res.input_cost, 0.0025)
    assert math.isclose(res.output_cost, 0.0050)


def test_actual_cost_gemini_provider():
    """Verify actual cost calculation for Google Gemini models using 'google' and 'gemini' provider names."""
    # gemini-flash: in=0.30, out=2.50
    res_google = calculate_actual_cost(
        provider="google",
        model="gemini-flash",
        actual_input_tokens=10_000,
        actual_output_tokens=2_000,
    )
    assert res_google.pricing_status == "available"
    assert res_google.provider == "google"
    # in: 10_000 * 0.30 / 1e6 = 0.003
    # out: 2_000 * 2.50 / 1e6 = 0.005
    # total: 0.008
    assert res_google.actual_cost_decimal == Decimal("0.008")
    assert math.isclose(res_google.actual_cost, 0.008)

    # Provider alias 'gemini' should also resolve cleanly
    res_gemini = calculate_actual_cost(
        provider="gemini",
        model="gemini-flash",
        actual_input_tokens=10_000,
        actual_output_tokens=2_000,
    )
    assert res_gemini.pricing_status == "available"
    assert res_gemini.actual_cost_decimal == Decimal("0.008")


def test_actual_cost_anthropic_provider():
    """Verify actual cost calculation for Anthropic Claude models using 'anthropic' and 'claude' provider names."""
    # claude-sonnet: in=3.00, out=15.00
    res_anthropic = calculate_actual_cost(
        provider="anthropic",
        model="claude-sonnet",
        actual_input_tokens=2_000,
        actual_output_tokens=1_000,
    )
    assert res_anthropic.pricing_status == "available"
    assert res_anthropic.provider == "anthropic"
    # in: 2000 * 3.00 / 1e6 = 0.006
    # out: 1000 * 15.00 / 1e6 = 0.015
    # total: 0.021
    assert res_anthropic.actual_cost_decimal == Decimal("0.021")
    assert math.isclose(res_anthropic.actual_cost, 0.021)

    # Provider alias 'claude' should also resolve cleanly
    res_claude = calculate_actual_cost(
        provider="claude",
        model="claude-sonnet",
        actual_input_tokens=2_000,
        actual_output_tokens=1_000,
    )
    assert res_claude.pricing_status == "available"
    assert res_claude.actual_cost_decimal == Decimal("0.021")


# ==============================================================================
# 2. Precision and Very Small Costs (Fractions of a Cent)
# ==============================================================================

def test_tiny_token_counts_and_sub_cent_precision():
    """Very small token counts must maintain full Decimal precision without premature rounding."""
    # gpt-4o-mini: in=0.15, out=0.60 per 1M
    # 1 input token = $0.00000015
    # 1 output token = $0.00000060
    # Total = $0.00000075 (0.000075 cents!)
    res = calculate_actual_cost(
        provider="openai",
        model="gpt-4o-mini",
        actual_input_tokens=1,
        actual_output_tokens=1,
    )
    assert res.pricing_status == "available"
    assert res.actual_cost_decimal == Decimal("0.00000075")
    assert res.input_cost_decimal == Decimal("0.00000015")
    assert res.output_cost_decimal == Decimal("0.00000060")
    assert res.actual_cost == 0.00000075


def test_zero_token_execution():
    """Zero tokens billed yields exact 0.0 cost while keeping available status."""
    res = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=0,
        actual_output_tokens=0,
    )
    assert res.pricing_status == "available"
    assert res.actual_cost == 0.0
    assert res.actual_cost_decimal == Decimal("0")
    assert res.total_tokens == 0


def test_large_token_execution_precision():
    """Calculations with large prompt and completion volumes avoid intermediate rounding drift."""
    # gpt-4o: in=2.50, out=10.00
    # in: 123,456 tokens -> 123456 / 1e6 * 2.50 = 0.30864
    # out: 65,432 tokens -> 65432 / 1e6 * 10.00 = 0.65432
    # total: 0.96296
    res = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=123_456,
        actual_output_tokens=65_432,
    )
    assert res.actual_cost_decimal == Decimal("0.96296")
    assert math.isclose(res.actual_cost, 0.96296)


# ==============================================================================
# 3. Cached Input Token Pricing Support
# ==============================================================================

def test_actual_cost_with_cached_input_tokens(monkeypatch):
    """Support models with cached prompt pricing when cached input tokens are present."""
    # Register a model with cached input pricing
    custom_model = ModelPricing(
        model="test-cache-model",
        provider="openai",
        input_price_per_million=Decimal("2.00"),
        output_price_per_million=Decimal("8.00"),
        cached_input_price_per_million=Decimal("0.50"),
        cache_write_price_per_million=Decimal("1.00"),
    )
    upsert_pricing(custom_model, persist=False)

    # 100k input total: 40k cached, 10k cache write, 50k regular; 20k output
    res = calculate_actual_cost(
        provider="openai",
        model="test-cache-model",
        actual_input_tokens=100_000,
        actual_output_tokens=20_000,
        cached_input_tokens=40_000,
        cache_write_tokens=10_000,
    )
    assert res.pricing_status == "available"
    # ordinary in: 50,000 * 2.00 / 1e6 = 0.10
    # cached in: 40,000 * 0.50 / 1e6 = 0.02
    # input cost: 0.12
    # out: 20,000 * 8.00 / 1e6 = 0.16
    # write: 10,000 * 1.00 / 1e6 = 0.01
    # total: 0.29
    assert res.input_cost_decimal == Decimal("0.12")
    assert res.output_cost_decimal == Decimal("0.16")
    assert res.actual_cost_decimal == Decimal("0.29")


# ==============================================================================
# 4. Error Handling and Status Distinction (Section 6 Contract)
# ==============================================================================

def test_model_not_registered():
    """Unregistered model returns 'model_not_registered' status with actual_cost=None (never zero)."""
    res = calculate_actual_cost(
        provider="openai",
        model="non-existent-model-xyz",
        actual_input_tokens=100,
        actual_output_tokens=100,
    )
    assert res.pricing_status == "model_not_registered"
    assert res.actual_cost is None
    assert res.actual_cost_decimal is None
    assert res.pricing_verification == "unavailable"
    assert "not registered" in res.error_details


def test_provider_model_mismatch():
    """If provider does not match model owner, returns model_not_registered."""
    # claude-sonnet belongs to anthropic, not openai
    res = calculate_actual_cost(
        provider="openai",
        model="claude-sonnet",
        actual_input_tokens=100,
        actual_output_tokens=100,
    )
    assert res.pricing_status == "model_not_registered"
    assert res.actual_cost is None
    assert "registered under provider 'anthropic'" in res.error_details


def test_invalid_provider():
    """Unsupported provider returns 'unsupported_provider' status with actual_cost=None."""
    res = calculate_actual_cost(
        provider="unknown-provider-999",
        model="gpt-4o",
        actual_input_tokens=100,
        actual_output_tokens=100,
    )
    assert res.pricing_status == "unsupported_provider"
    assert res.actual_cost is None
    assert "not supported" in res.error_details


def test_negative_tokens_rejected():
    """Negative token counts return 'invalid_usage_data' with actual_cost=None."""
    res_in = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=-10,
        actual_output_tokens=100,
    )
    assert res_in.pricing_status == "invalid_usage_data"
    assert res_in.actual_cost is None
    assert ">= 0" in res_in.error_details

    res_out = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=100,
        actual_output_tokens=-5,
    )
    assert res_out.pricing_status == "invalid_usage_data"
    assert res_out.actual_cost is None


def test_non_integer_tokens_rejected():
    """Non-integer tokens (float, bool, str) return 'invalid_usage_data' with actual_cost=None."""
    res_float = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=10.5,
        actual_output_tokens=100,
    )
    assert res_float.pricing_status == "invalid_usage_data"
    assert res_float.actual_cost is None

    res_bool = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=True,
        actual_output_tokens=100,
    )
    assert res_bool.pricing_status == "invalid_usage_data"
    assert res_bool.actual_cost is None

    res_str = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens="100",
        actual_output_tokens=100,
    )
    assert res_str.pricing_status == "invalid_usage_data"
    assert res_str.actual_cost is None


def test_cached_tokens_exceeding_input_rejected():
    """Cached tokens greater than total input tokens must return invalid_usage_data."""
    res = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=100,
        actual_output_tokens=50,
        cached_input_tokens=150,
    )
    assert res.pricing_status == "invalid_usage_data"
    assert res.actual_cost is None
    assert "cannot exceed input_tokens" in res.error_details


def test_missing_pricing_rates(monkeypatch):
    """If a registered model has incomplete pricing rates, return pricing_unavailable."""
    import cost_engine.pricing as pricing
    incomplete_model = ModelPricing(
        model="incomplete-model",
        provider="openai",
        input_price_per_million=Decimal("1.00"),
        output_price_per_million=Decimal("2.00"),
    )
    object.__setattr__(incomplete_model, "output_price_per_million", None)
    # Inject directly into registry cache
    reg = pricing._get_registry()
    monkeypatch.setitem(reg, "incomplete-model", incomplete_model)

    res = calculate_actual_cost(
        provider="openai",
        model="incomplete-model",
        actual_input_tokens=100,
        actual_output_tokens=100,
    )
    assert res.pricing_status == "pricing_unavailable"
    assert res.actual_cost is None


def test_unsupported_pricing_components_reported():
    """When provider returns additional usage categories (e.g. reasoning_tokens, audio_tokens), report limitation clearly."""
    # Passing reasoning_tokens in additional_usage
    res = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=500,
        actual_output_tokens=200,
        additional_usage={"reasoning_tokens": 100},
    )
    assert res.pricing_status == "unsupported_pricing_structure"
    assert res.actual_cost is None
    assert "reasoning_tokens" in res.unsupported_components
    assert "unsupported usage categories" in res.error_details

    # Passing audio_tokens in kwargs
    res_audio = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=500,
        actual_output_tokens=200,
        audio_tokens=50,
    )
    assert res_audio.pricing_status == "unsupported_pricing_structure"
    assert "audio_tokens" in res_audio.unsupported_components


def test_cached_pricing_requested_on_unsupported_model():
    """If cached input tokens are reported for a model without cached rates, report unsupported_pricing_structure."""
    model_without_cache = ModelPricing(
        model="no-cache-model",
        provider="openai",
        input_price_per_million=Decimal("1.00"),
        output_price_per_million=Decimal("2.00"),
    )
    upsert_pricing(model_without_cache, persist=False)

    res = calculate_actual_cost(
        provider="openai",
        model="no-cache-model",
        actual_input_tokens=1000,
        actual_output_tokens=500,
        cached_input_tokens=200,
    )
    assert res.pricing_status == "unsupported_pricing_structure"
    assert res.actual_cost is None
    assert "cached_input_tokens" in res.unsupported_components


# ==============================================================================
# 5. Multi-Currency Support (ISO 4217)
# ==============================================================================

def test_iso_4217_validation():
    """Validate ISO 4217 currency helpers."""
    assert is_valid_currency("USD")
    assert is_valid_currency("EUR")
    assert is_valid_currency("gbp")
    assert is_valid_currency("JPY")
    assert is_valid_currency("INR")
    assert not is_valid_currency("INVALID_CURRENCY")
    assert not is_valid_currency("US")
    assert not is_valid_currency(123)
    assert normalize_currency("eur") == "EUR"


def test_invalid_currency_code_rejected():
    """Invalid currency returns 'invalid_currency' status with actual_cost=None."""
    res = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=100,
        actual_output_tokens=100,
        currency="FAKE_CURR",
    )
    assert res.pricing_status == "invalid_currency"
    assert res.actual_cost is None


def test_currency_mismatch_without_auto_conversion():
    """When caller requests a currency different from model pricing currency, reject auto-conversion."""
    # gpt-4o is priced in USD. Requesting EUR must not perform silent exchange conversion.
    res = calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        actual_input_tokens=100,
        actual_output_tokens=100,
        currency="EUR",
    )
    assert res.pricing_status == "currency_mismatch"
    assert res.actual_cost is None
    assert "automatic exchange rate conversion is not performed" in res.error_details


def test_multi_currency_model_pricing():
    """Support models registered in non-USD currencies (e.g. EUR, GBP, JPY)."""
    eur_model = ModelPricing(
        model="euro-llm-1",
        provider="openai",
        input_price_per_million=Decimal("3.00"),
        output_price_per_million=Decimal("12.00"),
        currency="EUR",
    )
    upsert_pricing(eur_model, persist=False)

    res = calculate_actual_cost(
        provider="openai",
        model="euro-llm-1",
        actual_input_tokens=10_000,
        actual_output_tokens=5_000,
        currency="EUR",
    )
    assert res.pricing_status == "available"
    assert res.currency == "EUR"
    # in: 10_000 * 3.00 / 1e6 = 0.03 EUR
    # out: 5_000 * 12.00 / 1e6 = 0.06 EUR
    # total: 0.09 EUR
    assert res.actual_cost_decimal == Decimal("0.09")
    assert math.isclose(res.actual_cost, 0.09)


def test_cross_currency_comparison_rejected_without_conversion():
    """compare_models must not compare raw monetary values across differing currencies."""
    jpy_model = ModelPricing(
        model="tokyo-llm-1",
        provider="openai",
        input_price_per_million=Decimal("500.00"),  # 500 JPY
        output_price_per_million=Decimal("1500.00"), # 1500 JPY
        currency="JPY",
    )
    upsert_pricing(jpy_model, persist=False)

    # Comparing USD models and JPY model without currency filter
    result = compare_models(1000, 500, models=["gpt-4o", "tokyo-llm-1"])
    # The JPY model must not be directly sorted against the USD model
    unavailable_reasons = {m["model"]: m["reason"] for m in result["unavailable_models"]}
    assert "tokyo-llm-1" in unavailable_reasons
    assert "currency_mismatch" in unavailable_reasons["tokyo-llm-1"]

    # When explicit target currency is requested, only models of that currency are evaluated
    res_jpy = compare_models(1000, 500, models=["gpt-4o", "tokyo-llm-1"], currency="JPY")
    assert len(res_jpy["models"]) == 1
    assert res_jpy["models"][0]["model"] == "tokyo-llm-1"


# ==============================================================================
# 6. Pricing Verification Status Transparency
# ==============================================================================

def test_unverified_pricing_status():
    """Manual unverified models transparently report manual_unverified verification."""
    res = calculate_actual_cost("openai", "gpt-4o", 100, 100)
    assert res.pricing_status == "available"
    assert res.pricing_verification == "manual_unverified"


def test_official_verified_pricing_status():
    """Models verified by official provider adapter report official_verified."""
    from cost_engine.pricing import _OFFICIAL_ADAPTER_PROVENANCE

    verified_model = ModelPricing(
        model="verified-claude-3",
        provider="anthropic",
        input_price_per_million=Decimal("3.00"),
        output_price_per_million=Decimal("15.00"),
        source_url="https://platform.claude.com/docs/en/about-claude/pricing",
        last_verified="2026-11-15T00:00:00+00:00",
        retrieved_at="2026-11-15T00:00:00+00:00",
        pricing_status="official_verified",
    )
    upsert_pricing(verified_model, persist=False, _provenance=_OFFICIAL_ADAPTER_PROVENANCE)

    res = calculate_actual_cost("anthropic", "verified-claude-3", 1000, 500)
    assert res.pricing_status == "available"
    assert res.pricing_verification == "official_verified"


# ==============================================================================
# 7. Integration Contract, Dict/Dataclass Interface & Batch Execution
# ==============================================================================

def test_actual_cost_result_contract_and_dict_access():
    """ActualCostResult supports both attribute and dictionary access."""
    res = calculate_actual_cost("openai", "gpt-4o", 120, 250)
    assert res.provider == "openai"
    assert res.model == "gpt-4o"
    assert res["provider"] == "openai"
    assert res["model"] == "gpt-4o"
    assert res["input_tokens"] == 120
    assert res["output_tokens"] == 250
    assert res["total_tokens"] == 370
    assert res["currency"] == "USD"
    assert res["pricing_status"] == "available"
    assert res["pricing_verification"] == "manual_unverified"
    assert isinstance(res["actual_cost"], float)
    assert "actual_cost_decimal" in res
    assert res.get("non_existent", "default") == "default"

    as_dict = res.to_dict()
    assert isinstance(as_dict, dict)
    assert as_dict["provider"] == "openai"
    assert as_dict["actual_cost"] is not None


def test_calculate_actual_cost_decimal():
    """calculate_actual_cost_decimal returns exact Decimal or raises on error."""
    # gpt-4o: in=2.50, out=10.00
    cost_d = calculate_actual_cost_decimal("openai", "gpt-4o", 1000, 500)
    assert isinstance(cost_d, Decimal)
    assert cost_d == Decimal("0.0075")

    # When error occurs and raise_on_error=True (default)
    with pytest.raises(UnknownModelError):
        calculate_actual_cost_decimal("openai", "unknown-model", 1000, 500)

    # When raise_on_error=False
    assert calculate_actual_cost_decimal("openai", "unknown-model", 1000, 500, raise_on_error=False) is None


def test_calculate_actual_cost_batch():
    """calculate_actual_cost_batch processes multiple provider executions."""
    records = [
        {"id": "req-1", "provider": "openai", "model": "gpt-4o", "actual_input_tokens": 1000, "actual_output_tokens": 500},
        {"id": "req-2", "provider": "google", "model": "gemini-flash", "actual_input_tokens": 2000, "actual_output_tokens": 1000},
        {"id": "req-3", "provider": "anthropic", "model": "claude-sonnet", "actual_input_tokens": 1000, "actual_output_tokens": 500},
        {"id": "req-4", "provider": "openai", "model": "non-existent", "actual_input_tokens": 100, "actual_output_tokens": 100},
        {"id": "req-5", "provider": "openai", "model": "gpt-4o", "actual_input_tokens": -5, "actual_output_tokens": 100},
    ]
    batch_results = calculate_actual_cost_batch(records)
    assert len(batch_results) == 5

    assert batch_results[0]["id"] == "req-1"
    assert batch_results[0]["pricing_status"] == "available"
    assert batch_results[0]["actual_cost"] == 0.0075

    assert batch_results[1]["id"] == "req-2"
    assert batch_results[1]["pricing_status"] == "available"

    assert batch_results[2]["id"] == "req-3"
    assert batch_results[2]["pricing_status"] == "available"

    assert batch_results[3]["id"] == "req-4"
    assert batch_results[3]["pricing_status"] == "model_not_registered"
    assert batch_results[3]["actual_cost"] is None

    assert batch_results[4]["id"] == "req-5"
    assert batch_results[4]["pricing_status"] == "invalid_usage_data"
    assert batch_results[4]["actual_cost"] is None


# ==============================================================================
# 8. Preservation of Existing Estimated Cost Functionality
# ==============================================================================

def test_estimated_cost_remains_unchanged():
    """Existing prompt cost estimates, savings, and comparisons are completely preserved."""
    # Pre-execution estimate uses estimate_cost
    est = estimate_cost("gpt-4o", 1000, 500)
    assert est["input_tokens"] == 1000
    assert est["predicted_output_tokens"] == 500
    assert math.isclose(est["estimated_cost"], 0.0075)

    # Actual cost after execution uses calculate_actual_cost
    actual = calculate_actual_cost("openai", "gpt-4o", 1000, 500)
    assert actual.input_tokens == 1000
    assert actual.output_tokens == 500
    assert actual.actual_cost == 0.0075
    assert actual.estimate_type == "actual"

    # Savings calculation preserved
    savings = calculate_savings("gpt-4o", 1000, 700)
    assert savings["tokens_saved"] == 300
    assert savings["optimization_percentage"] == 30.0
