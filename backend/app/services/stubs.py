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


def _predict_output_tokens(prompt: str, model: str, input_tokens: int) -> int:
    return max(1, input_tokens)


def _estimate_cost(input_tokens: int, output_tokens: int, input_price_per_1k: float,
                   output_price_per_1k: float, model: str = "") -> float:
    return input_tokens / 1000 * input_price_per_1k + output_tokens / 1000 * output_price_per_1k


def _forecast_cost(daily_costs: list[float], horizon_days: int) -> list[float]:
    avg = sum(daily_costs) / len(daily_costs) if daily_costs else 0.0
    return [avg] * horizon_days


nlp_engine = SimpleNamespace(analyze_prompt=_analyze_prompt)
cost_engine = SimpleNamespace(
    predict_output_tokens=_predict_output_tokens, estimate_cost=_estimate_cost, forecast_cost=_forecast_cost)
