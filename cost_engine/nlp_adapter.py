"""Optional adapter to the existing public NLP Engine interface."""
from __future__ import annotations

from .calculator import calculate_cost


def compare_prompt_cost(prompt: str, model: str, *, expected_output_tokens: int) -> dict:
    from nlp_engine import analyze_prompt
    result=analyze_prompt(prompt, model)
    original=int(result["original_tokens"]); optimized=int(result["optimized_tokens"])
    if optimized > original: raise ValueError("NLP Engine returned optimized token count above original")
    before=calculate_cost(model, original, expected_output_tokens)
    after=calculate_cost(model, optimized, expected_output_tokens)
    saved=before.total_cost-after.total_cost
    return {"model":model,"provider":before.provider,"pricing_version":before.pricing_version,
        "original_prompt":prompt,"optimized_prompt":result["optimized_prompt"],
        "original_input_tokens":original,"optimized_input_tokens":optimized,
        "output_tokens_assumption":expected_output_tokens,
        "original_estimated_cost":before.total_cost,"optimized_estimated_cost":after.total_cost,
        "estimated_savings":saved,"percentage_cost_reduction":(saved/before.total_cost*100 if before.total_cost else 0.0),
        "currency":before.currency,"pricing_status":__import__("cost_engine.pricing",fromlist=["get_pricing"]).get_pricing(model).pricing_status,
        "estimate_type":"estimate_not_actual_billing","nlp_analysis":result}
