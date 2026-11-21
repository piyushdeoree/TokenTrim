"""Cost Intelligence engine (Person 2).

Public API for FastAPI integration:
    estimate_cost, predict_output_tokens, forecast_cost,
    compare_models, recommend_model
"""
from .calculator import (calculate_cost, calculate_cost_batch, calculate_cost_decimal,
                         calculate_savings, estimate_cost, estimate_cost_api,
                         calculate_actual_cost, calculate_actual_cost_decimal,
                         calculate_actual_cost_batch, calculate_execution_cost,
                         calculate_execution_cost_decimal)
from .comparison import compare_models
from .forecasting import forecast_cost
from .prediction import predict_output_tokens
from .prediction import reload_prediction_model
from .pricing import (UnknownModelError, get_pricing, get_pricing_decimal, list_models, reload_pricing,
                      upsert_pricing, pricing_freshness, get_pricing_history,
                      get_pricing_version, pricing_cache_info,
                      is_supported_provider, normalize_provider)
from .recommendation import recommend_model
from .nlp_adapter import compare_prompt_cost
from .pricing_engine import (refresh_pricing, refresh_provider, refresh_openai_pricing,
                             refresh_anthropic_pricing, refresh_google_pricing,
                             manual_pricing_update)
from .currency import convert_usd_to_inr, is_valid_currency, normalize_currency
from .analytics import analyze_savings
from .forecasting import aggregate_usage_costs, forecast_usage_costs
from .models import ActualCostResult, ModelPricing, CostBreakdown, CostEstimate, SavingsResult

__all__ = [
    "estimate_cost", "estimate_cost_api", "calculate_cost", "calculate_cost_decimal",
    "calculate_cost_batch", "calculate_savings",
    "calculate_actual_cost", "calculate_actual_cost_decimal", "calculate_actual_cost_batch",
    "calculate_execution_cost", "calculate_execution_cost_decimal",
    "ActualCostResult", "ModelPricing", "CostBreakdown", "CostEstimate", "SavingsResult",
    "predict_output_tokens", "reload_prediction_model", "forecast_cost", "compare_models", "recommend_model",
    "get_pricing", "get_pricing_decimal", "list_models", "upsert_pricing", "reload_pricing", "UnknownModelError",
    "compare_prompt_cost", "refresh_pricing", "manual_pricing_update",
    "convert_usd_to_inr", "is_valid_currency", "normalize_currency", "analyze_savings",
    "pricing_freshness", "is_supported_provider", "normalize_provider",
    "get_pricing_history", "get_pricing_version", "refresh_provider",
    "refresh_openai_pricing", "refresh_anthropic_pricing", "refresh_google_pricing",
    "pricing_cache_info", "aggregate_usage_costs", "forecast_usage_costs",
]
