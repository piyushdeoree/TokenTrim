"""PLACEHOLDER engines so the backend runs before Person 1 / Person 2 deliver their modules.

These are NOT the real NLP or ML algorithms. They only mimic the assumed interface, using
trivial heuristics. Enable with USE_STUB_ENGINES=true. In production leave it false so the
real `nlp_engine` and `cost_engine` packages are imported.
"""
from types import SimpleNamespace


def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _analyze_prompt(prompt: str, model: str) -> dict:
    optimized = " ".join(prompt.split())
    issues = ["Extra whitespace"] if optimized != prompt else []
    return {
        "original_tokens": _count_tokens(prompt),
        "optimized_tokens": _count_tokens(optimized),
        "optimized_prompt": optimized,
        "issues": issues,
        "suggestions": ["Collapse repeated whitespace"] if issues else [],
    }


def _predict_output_tokens(input_tokens: int, model: str, prompt_text: str = "") -> int:
    return max(1, input_tokens)


def _estimate_cost(model: str, input_tokens: int, predicted_output_tokens: int,
                   input_price_per_1k: float = 0.0, output_price_per_1k: float = 0.0) -> float:
    return input_tokens / 1000 * input_price_per_1k + predicted_output_tokens / 1000 * output_price_per_1k


def _forecast_cost(historical_cost: list[float], forecast_period: str) -> list[float]:
    horizon_days = int(forecast_period.split("_")[0])
    avg = sum(historical_cost) / len(historical_cost) if historical_cost else 0.0
    return [avg] * horizon_days


nlp_engine = SimpleNamespace(analyze_prompt=_analyze_prompt)
cost_engine = SimpleNamespace(
    predict_output_tokens=_predict_output_tokens, estimate_cost=_estimate_cost, forecast_cost=_forecast_cost)
