"""Optional adapter to the existing public NLP Engine interface."""
from __future__ import annotations

from .calculator import _calculate_cost_with_pricing, _check_tokens
from .pricing import _get_pricing_cached, pricing_freshness


def compare_prompt_cost(prompt: str, model: str, *, expected_output_tokens: int) -> dict:
    from nlp_engine import analyze_prompt
    result=analyze_prompt(prompt, model)
    if not isinstance(result, dict): raise ValueError("NLP Engine returned an invalid analysis result")
    original=_check_tokens(result.get("original_tokens"), "original_tokens")
    optimized=_check_tokens(result.get("optimized_tokens"), "optimized_tokens")
    if optimized > original: raise ValueError("NLP Engine returned optimized token count above original")
    output_tokens=_check_tokens(expected_output_tokens, "expected_output_tokens")
    pricing=_get_pricing_cached(model)
    before=_calculate_cost_with_pricing(model, pricing, original, output_tokens, 0, 0)
    after=_calculate_cost_with_pricing(model, pricing, optimized, output_tokens, 0, 0)
    saved=before.total_cost-after.total_cost
    return {"model":model,"provider":before.provider,"pricing_version":before.pricing_version,
        "original_prompt":prompt,"optimized_prompt":result["optimized_prompt"],
        "original_input_tokens":original,"optimized_input_tokens":optimized,
        "output_tokens_assumption":expected_output_tokens,
        "original_estimated_cost":before.total_cost,"optimized_estimated_cost":after.total_cost,
        "estimated_savings":saved,"percentage_cost_reduction":(saved/before.total_cost*100 if before.total_cost else 0.0),
        "currency":before.currency,"pricing_status":pricing.pricing_status,
        "pricing_freshness":pricing_freshness(pricing),
        "estimate_type":"estimate_not_actual_billing","nlp_analysis":result}
