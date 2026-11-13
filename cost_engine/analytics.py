"""Explainable spend analysis over caller-provided usage records."""
from collections import defaultdict
from decimal import Decimal

def analyze_savings(records: list[dict], *, expensive_threshold: Decimal | str = "0.10") -> dict:
    """Records need model, provider, input_tokens, output_tokens, cost; no records are fabricated."""
    threshold=Decimal(str(expensive_threshold)); model_cost=defaultdict(Decimal); provider_cost=defaultdict(Decimal)
    tokens_in=tokens_out=cached=0
    for r in records:
        cost=Decimal(str(r["cost"]))
        if not cost.is_finite() or cost<0: raise ValueError("cost must be finite and non-negative")
        model_cost[r["model"]]+=cost; provider_cost[r["provider"]]+=cost
        tokens_in+=int(r.get("input_tokens",0)); tokens_out+=int(r.get("output_tokens",0)); cached+=int(r.get("cached_input_tokens",0))
    findings=[]
    for model,cost in sorted(model_cost.items(), key=lambda x:x[1], reverse=True):
        if cost>=threshold: findings.append({"type":"high_model_spend","model":model,"spend":str(cost),"reason":f"Model spend meets or exceeds configured threshold {threshold}.","potential_saving":None})
    return {"record_count":len(records),"actual_historical_cost":str(sum(model_cost.values(),Decimal(0))),"model_spend":{k:str(v) for k,v in model_cost.items()},"provider_spend":{k:str(v) for k,v in provider_cost.items()},"input_tokens":tokens_in,"output_tokens":tokens_out,"cached_input_tokens":cached,"input_output_ratio":(tokens_in/tokens_out if tokens_out else None),"findings":findings,"limitations":"Potential savings require model pricing and scenario estimates; historical cost alone is not a recommendation."}
