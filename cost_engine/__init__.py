"""Cost Intelligence engine (Person 2).

Public API for FastAPI integration:
    estimate_cost, predict_output_tokens, forecast_cost,
    compare_models, recommend_model
"""
from .calculator import calculate_cost, calculate_savings, estimate_cost, estimate_cost_api
from .comparison import compare_models
from .forecasting import forecast_cost
from .prediction import predict_output_tokens
from .pricing import UnknownModelError, get_pricing, list_models, reload_pricing, upsert_pricing
from .recommendation import recommend_model

__all__ = [
    "estimate_cost", "estimate_cost_api", "calculate_cost", "calculate_savings",
    "predict_output_tokens", "forecast_cost", "compare_models", "recommend_model",
    "get_pricing", "list_models", "upsert_pricing", "reload_pricing", "UnknownModelError",
]
