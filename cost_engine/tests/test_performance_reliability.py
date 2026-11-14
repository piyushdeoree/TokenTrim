from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json

import pytest

from cost_engine import config, prediction
from cost_engine.analytics import analyze_savings
from cost_engine.calculator import calculate_cost, calculate_cost_batch
from cost_engine.comparison import compare_models
from cost_engine.forecasting import aggregate_usage_costs, forecast_usage_costs
from cost_engine.models import ModelPricing
from cost_engine.pricing import get_pricing, get_pricing_decimal, list_models, pricing_cache_info, upsert_pricing


def test_pricing_cache_is_detached_indexed_and_thread_safe(monkeypatch):
    import cost_engine.pricing as pricing

    monkeypatch.setattr(pricing, "_registry", None)
    monkeypatch.setattr(pricing, "_provider_index", None)
    monkeypatch.setattr(pricing, "_history", {})
    entry = ModelPricing("cache-test-model", "test-provider", 1, 2,
                         pricing_conditions={"nested": {"label": "original"}})
    upsert_pricing(entry, persist=False)
    snapshot = get_pricing_decimal(entry.model)
    snapshot.input_price_per_million = Decimal("999")
    snapshot.pricing_conditions["nested"]["label"] = "mutated"
    assert get_pricing_decimal(entry.model).input_price_per_million == Decimal("1")
    assert get_pricing_decimal(entry.model).pricing_conditions["nested"]["label"] == "original"
    assert list_models("TEST-PROVIDER") == [entry.model]
    assert pricing_cache_info()["providers"]["test-provider"] == 1

    def read_prices(_):
        return get_pricing("gpt-4o").input_price_per_million, list_models("openai")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(read_prices, range(100)))
    assert all(rate > 0 and "gpt-4o" in models for rate, models in results)


def test_explicit_pricing_reload_replaces_cached_catalogue(tmp_path, monkeypatch):
    import cost_engine.pricing as pricing

    catalog = tmp_path / "pricing.json"
    history = tmp_path / "history.json"
    monkeypatch.setattr(pricing.config, "PRICING_FILE", catalog)
    monkeypatch.setattr(pricing.config, "PRICING_HISTORY_FILE", history)
    monkeypatch.setattr(pricing, "_registry", None)
    monkeypatch.setattr(pricing, "_provider_index", None)
    monkeypatch.setattr(pricing, "_history", {})
    first = ModelPricing("reload-model", "provider", 1, 2)
    catalog.write_text(json.dumps({"models": [first.to_dict()]}), encoding="utf-8")
    pricing.reload_pricing()
    assert get_pricing_decimal(first.model).input_price_per_million == Decimal("1")
    second = ModelPricing("reload-model", "provider", 3, 2)
    catalog.write_text(json.dumps({"models": [second.to_dict()]}), encoding="utf-8")
    pricing.reload_pricing()
    assert get_pricing_decimal(second.model).input_price_per_million == Decimal("3")
    assert pricing_cache_info()["model_count"] == 1


def test_nested_tier_decimal_round_trip_does_not_create_fake_version(tmp_path, monkeypatch):
    import cost_engine.pricing as pricing

    catalog, history = tmp_path / "pricing.json", tmp_path / "history.json"
    monkeypatch.setattr(pricing.config, "PRICING_FILE", catalog)
    monkeypatch.setattr(pricing.config, "PRICING_HISTORY_FILE", history)
    monkeypatch.setattr(pricing, "_registry", None)
    monkeypatch.setattr(pricing, "_provider_index", None)
    monkeypatch.setattr(pricing, "_history", {})
    catalog.write_text(json.dumps({"_meta": {}, "models": []}), encoding="utf-8")
    first = ModelPricing("tier-roundtrip-model", "provider", 1, 2,
                         pricing_tiers=[{"tier": "batch", "input": Decimal("0.5"),
                                         "output": Decimal("1"), "conditions": {}}])
    upsert_pricing(first, persist=True)
    pricing.reload_pricing()
    same = ModelPricing("tier-roundtrip-model", "provider", 1, 2,
                        pricing_tiers=[{"tier": "batch", "input": Decimal("0.5"),
                                        "output": Decimal("1"), "conditions": {}}])
    upsert_pricing(same, persist=True)
    assert get_pricing_decimal(same.model).pricing_version == 1
    assert get_pricing_decimal(same.model).pricing_tiers[0]["input"] == Decimal("0.5")
    assert pricing.get_pricing_history(same.model) == []


def test_late_official_snapshot_cannot_replace_newer_verified_pricing(monkeypatch):
    import cost_engine.pricing as pricing
    monkeypatch.setattr(pricing, "_registry", None)
    monkeypatch.setattr(pricing, "_provider_index", None)
    monkeypatch.setattr(pricing, "_history", {})
    newer_time = "2026-11-14T10:00:00+00:00"
    older_time = "2026-11-14T09:00:00+00:00"
    newer = ModelPricing("verified-order-model", "openai", 2, 4,
        source_url="https://developers.openai.com/api/docs/pricing", last_verified=newer_time,
        retrieved_at=newer_time, pricing_status="official_verified")
    older = ModelPricing("verified-order-model", "openai", 1, 3,
        source_url="https://developers.openai.com/api/docs/pricing", last_verified=older_time,
        retrieved_at=older_time, pricing_status="official_verified")
    provenance = pricing._OFFICIAL_ADAPTER_PROVENANCE
    pricing.upsert_pricing(newer, persist=False, _provenance=provenance)
    with pytest.raises(ValueError, match="older snapshot"):
        pricing.upsert_pricing(older, persist=False, _provenance=provenance)
    assert get_pricing_decimal(newer.model).input_price_per_million == Decimal("2")


def test_batch_calculation_reuses_price_and_isolates_row_failures():
    rows = calculate_cost_batch([
        {"id": "ok", "model": "gpt-4o", "input_tokens": 1_000_000, "output_tokens": 0},
        {"id": "bad", "model": "gpt-4o", "input_tokens": -1, "output_tokens": 0},
        {"id": "unknown", "model": "missing-model", "input_tokens": 10, "output_tokens": 1},
    ])
    assert [row["ok"] for row in rows] == [True, False, False]
    assert rows[0]["id"] == "ok"
    assert rows[0]["total_cost"] == pytest.approx(2.5)
    assert rows[1]["error"]["type"] == "ValueError"
    assert rows[2]["error"]["type"] == "UnknownModelError"


def test_published_batch_tier_applies_tier_cache_prices():
    from pathlib import Path
    from cost_engine.pricing_adapters.openai import parse_openai_pricing

    fixture = Path(__file__).parent / "fixtures" / "openai_pricing.md"
    parsed = next(row for row in parse_openai_pricing(fixture.read_text(encoding="utf-8"))
                  if row["model"] == "gpt-4o")
    parsed["pricing_status"] = "manual_unverified"
    parsed["last_verified"] = None
    model = ModelPricing(**parsed)
    upsert_pricing(model, persist=False)
    standard = calculate_cost(model.model, 1_000_000, 1_000_000)
    batch = calculate_cost(model.model, 1_000_000, 1_000_000, batch=True)
    batch_cached = calculate_cost(model.model, 1_000_000, 1_000_000,
                                  cached_input_tokens=400_000, cache_write_tokens=100_000, batch=True)
    assert batch.total_cost < standard.total_cost
    assert batch_cached.total_cost == pytest.approx(6.03125)
    assert batch_cached.batch and batch_cached.pricing_tier == "batch"


def test_cache_write_tokens_are_not_double_billed_and_large_costs_stay_finite():
    model = ModelPricing("cache-write-model", "test-provider", 2, 4,
                         cached_input_price_per_million=Decimal("0.5"),
                         cache_write_price_per_million=Decimal("3"))
    upsert_pricing(model, persist=False)
    result = calculate_cost(model.model, 1_000_000, 500_000,
                             cached_input_tokens=400_000, cache_write_tokens=100_000)
    assert result.input_cost == pytest.approx(1.2)
    assert result.other_charges == pytest.approx(0.3)
    assert result.total_cost == pytest.approx(3.5)
    with pytest.raises(ValueError, match="cannot exceed"):
        calculate_cost(model.model, 1, 0, cached_input_tokens=1, cache_write_tokens=1)
    with pytest.raises(ValueError, match="numeric response range"):
        calculate_cost(model.model, 10**400, 0)


def test_comparison_reports_missing_and_incompatible_models():
    result = compare_models(10, 5, models=["gpt-4o", "not-supported", "gemini-pro"],
                            provider="openai")
    assert [row["model"] for row in result["models"]] == ["gpt-4o"]
    assert {row["reason"] for row in result["unavailable_models"]} == {"pricing_unavailable", "provider_filter"}
    none = compare_models(10, 5, models=["not-supported"])
    assert none["cheapest_model"] is None and none["unavailable_models"]


def test_training_rejects_insufficient_and_invalid_usage_rows():
    import pandas as pd

    small = pd.DataFrame({column: [1] * 5 for column in prediction.FEATURES + ["output_tokens"]})
    with pytest.raises(ValueError, match="at least"):
        prediction.train(small, data_source="REAL")
    enough = pd.DataFrame({column: [1] * prediction.MIN_TRAINING_ROWS for column in prediction.FEATURES + ["output_tokens"]})
    enough.loc[0, "output_tokens"] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        prediction.train(enough, data_source="REAL")


def test_predictor_has_runtime_version_metadata_and_reuses_loaded_model(monkeypatch):
    import sklearn

    if not config.PREDICTOR_METADATA_FILE.exists() or not config.PREDICTOR_FILE.exists():
        pytest.skip("trained predictor artifact is not present")
    metadata = json.loads(config.PREDICTOR_METADATA_FILE.read_text(encoding="utf-8"))
    assert metadata["sklearn_version"]
    assert metadata["artifact_sha256"]
    calls = 0
    original_load = prediction.joblib.load

    def counted_load(path):
        nonlocal calls
        calls += 1
        return original_load(path)

    monkeypatch.setattr(prediction.joblib, "load", counted_load)
    prediction.reload_prediction_model()
    first = prediction.predict_output_tokens(300)
    second = prediction.predict_output_tokens(301)
    if metadata["sklearn_version"] == sklearn.__version__:
        assert calls == 1
        assert first["source"].startswith("trained:")
        assert first["uncertainty_method"] == "held_out_MAE"
    else:
        assert calls == 0
        assert first["source"] == "fallback_ratio"
        assert "scikit-learn" in first["warning"]
    assert second["predicted_output_tokens"] >= 1


def test_prediction_version_mismatch_falls_back_before_unpickle(tmp_path, monkeypatch):
    import sklearn

    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"not a pickle; version check must stop before loading")
    metadata_path = tmp_path / "model.metadata.json"
    metadata_path.write_text(json.dumps({
        "artifact_schema_version": prediction.ARTIFACT_SCHEMA_VERSION,
        "sklearn_version": "0.0-incompatible",
        "artifact_sha256": prediction._sha256_file(artifact),
    }), encoding="utf-8")
    monkeypatch.setattr(config, "PREDICTOR_FILE", artifact)
    monkeypatch.setattr(config, "PREDICTOR_METADATA_FILE", metadata_path)
    monkeypatch.setattr(prediction.joblib, "load", lambda *_: pytest.fail("must not unpickle incompatible artifact"))
    prediction.reload_prediction_model()
    response = prediction.predict_output_tokens(200)
    assert response["source"] == "fallback_ratio"
    assert sklearn.__version__ not in response["warning"] or "runtime" in response["warning"]
    prediction.reload_prediction_model()


def test_forecast_aggregation_fills_missing_periods_and_projects_weekly_monthly():
    rows = [
        {"date": "2026-01-01", "cost": "1.25", "model": "m1"},
        {"date": "2026-01-03", "cost": "2.00", "model": "m1"},
        {"date": "2026-02-01", "cost": "3", "model": "m1"},
        {"date": "2026-03-01", "cost": "4", "model": "m1"},
    ]
    daily = aggregate_usage_costs(rows)
    assert [row["cost"] for row in daily[:3]] == [1.25, 0.0, 2.0]
    assert len(aggregate_usage_costs(rows, "monthly")) == 3
    weekly = forecast_usage_costs(rows, frequency="weekly", periods=2)
    monthly = forecast_usage_costs(rows, frequency="monthly", periods=1)
    assert weekly["frequency"] == "weekly" and len(weekly["forecast"]) == 2
    assert monthly["frequency"] == "monthly" and len(monthly["forecast"]) == 1
    by_model = aggregate_usage_costs(rows, group_by="model")
    assert all(row["model"] == "m1" for row in by_model)


def test_analytics_flags_observed_cost_increase_without_claiming_savings():
    result = analyze_savings([
        {"model": "m", "provider": "p", "date": "2026-01-01", "cost": "1", "input_tokens": 10, "output_tokens": 5},
        {"model": "m", "provider": "p", "date": "2026-01-02", "cost": "3", "input_tokens": 10, "output_tokens": 5},
    ])
    finding = next(item for item in result["findings"] if item["type"] == "unusual_cost_increase")
    assert finding["increase_ratio"] == "3"
    assert finding["potential_saving"] is None


def test_analytics_rejects_invalid_tokens_and_currency_amounts(monkeypatch):
    with pytest.raises(ValueError, match="input_tokens"):
        analyze_savings([{"model": "m", "provider": "p", "cost": "1", "input_tokens": -1}])
    from cost_engine import currency

    monkeypatch.setattr(currency, "get_usd_inr_rate", lambda **kwargs: {"rate": "80", "rate_date": "2026-01-01", "stale": False})
    with pytest.raises(ValueError, match="finite non-negative"):
        currency.convert_usd_to_inr("NaN")
    with pytest.raises(ValueError, match="finite non-negative"):
        currency.convert_usd_to_inr("-1")
