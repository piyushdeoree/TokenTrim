"""Tests for the cost engine. Run from the repo root:  pytest cost_engine/tests -v"""
import math

import pytest

from cost_engine import (
    calculate_cost, calculate_savings, compare_models, estimate_cost,
    estimate_cost_api, forecast_cost, get_pricing, list_models,
    predict_output_tokens, recommend_model, UnknownModelError,
)
from cost_engine import config, prediction


# ---- Cost calculation / estimation ------------------------------------------
def test_formula_matches_manual():
    p = get_pricing("gpt-4o")
    r = estimate_cost("gpt-4o", 1000, 500)
    exp_in = 1000 / 1e6 * p.input_price_per_million
    exp_out = 500 / 1e6 * p.output_price_per_million
    assert math.isclose(r["input_cost"], exp_in)
    assert math.isclose(r["output_cost"], exp_out)
    assert math.isclose(r["estimated_cost"], exp_in + exp_out)
    assert r["total_tokens"] == 1500


def test_short_and_long_prompt():
    short = estimate_cost("gpt-4o-mini", 10, 20)
    long_ = estimate_cost("gpt-4o-mini", 100_000, 4_000)
    assert 0 < short["estimated_cost"] < long_["estimated_cost"]


def test_different_models_differ():
    costs = {m: estimate_cost(m, 1000, 1000)["estimated_cost"] for m in list_models()}
    assert len(set(costs.values())) > 1


def test_different_output_predictions():
    assert estimate_cost("gpt-4o", 500, 100)["estimated_cost"] < estimate_cost("gpt-4o", 500, 2000)["estimated_cost"]


def test_zero_tokens():
    r = estimate_cost("gpt-4o", 0, 0)
    assert r["estimated_cost"] == 0 and r["total_tokens"] == 0


def test_tiny_tokens_nonnegative():
    assert estimate_cost("claude-haiku", 1, 1)["estimated_cost"] > 0


def test_large_tokens():
    r = estimate_cost("claude-sonnet", 50_000_000, 10_000_000)
    assert math.isfinite(r["estimated_cost"]) and r["estimated_cost"] > 0


@pytest.mark.parametrize("bad", [-1, 1.5, "10", None, True, float("nan")])
def test_invalid_tokens_rejected(bad):
    with pytest.raises((ValueError, TypeError)):
        estimate_cost("gpt-4o", bad, 10)


def test_unknown_model():
    with pytest.raises(UnknownModelError):
        estimate_cost("not-a-model", 10, 10)


def test_api_shape():
    r = estimate_cost_api("gpt-4o", 100, 50)
    assert {"estimated_input_cost", "estimated_output_cost", "estimated_total_cost"} <= set(r)


def test_actual_vs_estimated_distinct():
    assert "total_cost" in calculate_cost("gpt-4o", 10, 10).to_dict()
    assert "estimated_cost" in estimate_cost("gpt-4o", 10, 10)


# ---- Savings (Person 1 integration) -------------------------------------------
def test_savings():
    s = calculate_savings("gpt-4o", 1000, 800, tokens_saved=200, optimization_percentage=20.0)
    assert s["tokens_saved"] == 200
    assert math.isclose(s["input_cost_saved"], 200 / 1e6 * get_pricing("gpt-4o").input_price_per_million)


def test_savings_inconsistent_inputs():
    with pytest.raises(ValueError):
        calculate_savings("gpt-4o", 1000, 800, tokens_saved=50)
    with pytest.raises(ValueError):
        calculate_savings("gpt-4o", 100, 200)


def test_savings_zero_original():
    assert calculate_savings("gpt-4o", 0, 0)["optimization_percentage"] == 0.0


# ---- Prediction ---------------------------------------------------------------
def test_prediction_fallback(monkeypatch):
    monkeypatch.setattr(prediction, "_cached", None)
    monkeypatch.setattr(config, "PREDICTOR_FILE", config.ARTIFACT_DIR / "does_not_exist.joblib")
    r = predict_output_tokens(200)
    assert r["source"] == "fallback_ratio" and r["predicted_output_tokens"] == 200


def test_prediction_trained_if_available():
    prediction._cached = None
    if not config.PREDICTOR_FILE.exists():
        pytest.skip("run python -m cost_engine.prediction first")
    r = predict_output_tokens(300, task_type="coding", model="gpt-4o")
    assert r["predicted_output_tokens"] >= 1 and r["source"].startswith("trained:")


def test_prediction_zero_input_min_one():
    assert predict_output_tokens(0)["predicted_output_tokens"] >= 1


def test_prediction_from_text():
    r = predict_output_tokens(40, prompt_text="Summarize this article. It is long.")
    assert r["predicted_output_tokens"] >= 1


def test_prediction_invalid():
    with pytest.raises(ValueError):
        predict_output_tokens(-5)


def test_task_classifier():
    assert prediction.classify_task("Translate this to French") == "translation"
    assert prediction.classify_task("fix this python bug") == "coding"
    assert prediction.classify_task("hello there") == "question_answering"


# ---- Forecasting --------------------------------------------------------------
def test_forecast_horizons():
    hist = [10 + i * 0.5 for i in range(60)]
    for period, n in config.FORECAST_HORIZONS.items():
        r = forecast_cost(hist, period)
        assert len(r["forecast"]) == n
        assert math.isclose(r["estimated_future_cost"], sum(r["forecast"]))
        assert r["historical_cost"] == hist


def test_forecast_picks_trend_for_linear_growth():
    hist = [float(i) for i in range(1, 100)]
    assert forecast_cost(hist, "7_days")["method"] == "linear_regression"


def test_forecast_flat_series_prefers_simple():
    r = forecast_cost([5.0] * 50, "30_days")
    assert r["method"] == "moving_average"
    assert math.isclose(r["estimated_future_cost"], 150.0)


def test_forecast_non_negative():
    hist = [100 - 3 * i for i in range(30)]  # declining trend would go below 0
    assert min(forecast_cost(hist, "90_days", method="linear_regression")["forecast"]) >= 0


def test_forecast_accepts_dicts_and_tuples():
    d = [{"date": f"d{i}", "cost": 2.0} for i in range(10)]
    t = [(f"d{i}", 2.0) for i in range(10)]
    assert forecast_cost(d)["forecast"] == forecast_cost(t)["forecast"]


def test_forecast_short_history():
    r = forecast_cost([1.0, 2.0, 3.0], "7_days")
    assert r["method"] == "moving_average" and r["backtest"] is None
    with pytest.raises(ValueError):
        forecast_cost([1.0, 2.0])


def test_forecast_bad_inputs():
    with pytest.raises(ValueError):
        forecast_cost([1, 2, 3, 4], "365_days")
    with pytest.raises(ValueError):
        forecast_cost([1, -2, 3, 4])
    with pytest.raises(ValueError):
        forecast_cost([1, 2, 3, 4], method="magic")


# ---- Comparison / recommendation -------------------------------------------------
def test_compare_models():
    r = compare_models(1000, 500)
    costs = [m["estimated_cost"] for m in r["models"]]
    assert costs == sorted(costs)
    assert r["cheapest_model"] == r["models"][0]["model"]
    assert r["models"][0]["relative_cost"] == 1.0
    assert len(r["comparisons"]) == len(list_models())


def test_compare_zero_tokens():
    r = compare_models(0, 0)
    assert all(m["relative_cost"] == 1.0 for m in r["models"])


def test_compare_subset_and_empty():
    assert len(compare_models(10, 10, models=["gpt-4o", "gpt-4o-mini"])["models"]) == 2
    with pytest.raises(ValueError):
        compare_models(10, 10, models=[])


def test_recommend_quality_and_saving():
    r = recommend_model(1000, 500, task_type="coding", required_quality="high", current_model="claude-sonnet")
    assert r["is_recommendation_only"]
    assert get_pricing(r["recommended_model"]).quality_tier == 3
    assert r["estimated_saving"] >= 0


def test_recommend_complex_task_floor():
    r = recommend_model(100, 100, task_type="coding", required_quality="low")
    assert get_pricing(r["recommended_model"]).quality_tier >= 2


def test_recommend_context_filter():
    r = recommend_model(500_000, 1000)
    assert get_pricing(r["recommended_model"]).context_window >= 501_000


def test_recommend_no_eligible():
    r = recommend_model(5_000_000, 1000)
    assert r["recommended_model"] is None


def test_recommend_invalid_quality():
    with pytest.raises(ValueError):
        recommend_model(10, 10, required_quality="ultra")
