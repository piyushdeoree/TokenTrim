"""Cost Intelligence engine (Person 2).

Public API for FastAPI integration:
    estimate_cost, predict_output_tokens, forecast_cost,
    compare_models, recommend_model
"""
from .calculator import calculate_cost, calculate_savings, estimate_cost, estimate_cost_api
from .comparison import compare_models
from .forecasting import forecast_cost
from .prediction import predict_output_tokens
from .pricing import (UnknownModelError, get_pricing, list_models, reload_pricing,
                      upsert_pricing, pricing_freshness, get_pricing_history,
                      get_pricing_version)
from .recommendation import recommend_model
from .nlp_adapter import compare_prompt_cost
from .pricing_engine import (refresh_pricing, refresh_provider, refresh_openai_pricing,
                             refresh_anthropic_pricing, refresh_google_pricing,
                             manual_pricing_update)
from .currency import convert_usd_to_inr
from .analytics import analyze_savings

__all__ = [
    "estimate_cost", "estimate_cost_api", "calculate_cost", "calculate_savings",
    "predict_output_tokens", "forecast_cost", "compare_models", "recommend_model",
    "get_pricing", "list_models", "upsert_pricing", "reload_pricing", "UnknownModelError",
    "compare_prompt_cost", "refresh_pricing", "manual_pricing_update",
    "convert_usd_to_inr", "analyze_savings",
    "pricing_freshness",
    "get_pricing_history", "get_pricing_version", "refresh_provider",
    "refresh_openai_pricing", "refresh_anthropic_pricing", "refresh_google_pricing",
]
