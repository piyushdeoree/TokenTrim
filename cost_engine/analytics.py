"""Explainable spend analysis over caller-provided usage records."""
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

def analyze_savings(records: list[dict], *, expensive_threshold: Decimal | str = "0.10",
                    unusual_increase_ratio: Decimal | str = "2") -> dict:
    """Summarize caller-provided historical cost records without inventing savings."""
    try:
        threshold = Decimal(str(expensive_threshold))
        increase_ratio = Decimal(str(unusual_increase_ratio))
    except Exception:
        raise ValueError("threshold and increase ratio must be decimal values") from None
    if not threshold.is_finite() or threshold < 0:
        raise ValueError("expensive_threshold must be finite and non-negative")
    if not increase_ratio.is_finite() or increase_ratio <= 1:
        raise ValueError("unusual_increase_ratio must be finite and greater than 1")
    model_cost=defaultdict(Decimal); provider_cost=defaultdict(Decimal); daily_cost=defaultdict(Decimal)
    tokens_in=tokens_out=cached=0
    for index, r in enumerate(records):
        if not isinstance(r, dict): raise TypeError(f"record {index} must be a mapping")
        try:
            model, provider = r["model"], r["provider"]
            if not isinstance(model, str) or not model.strip() or not isinstance(provider, str) or not provider.strip():
                raise ValueError
            cost=Decimal(str(r["cost"]))
        except (KeyError, ValueError, TypeError, InvalidOperation):
            raise ValueError(f"record {index} needs model, provider, and cost") from None
        if not cost.is_finite() or cost<0: raise ValueError(f"record {index} cost must be finite and non-negative")
        model_cost[model]+=cost; provider_cost[provider]+=cost
        for field in ("input_tokens", "output_tokens", "cached_input_tokens"):
            value = r.get(field, 0)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"record {index} {field} must be a non-negative integer")
        if r.get("cached_input_tokens", 0) > r.get("input_tokens", 0):
            raise ValueError(f"record {index} cached_input_tokens cannot exceed input_tokens")
        tokens_in+=r.get("input_tokens",0); tokens_out+=r.get("output_tokens",0); cached+=r.get("cached_input_tokens",0)
        stamp = r.get("date") or r.get("created_at")
        if stamp:
            try:
                day = date.fromisoformat(stamp[:10]) if isinstance(stamp, str) else (stamp.date() if isinstance(stamp, datetime) else stamp)
                if not isinstance(day, date): raise TypeError
            except (ValueError, TypeError, AttributeError): raise ValueError(f"record {index} has an invalid date") from None
            daily_cost[day] += cost
    findings=[]
    for model,cost in sorted(model_cost.items(), key=lambda x:x[1], reverse=True):
        if cost>=threshold: findings.append({"type":"high_model_spend","model":model,"spend":str(cost),"reason":f"Model spend meets or exceeds configured threshold {threshold}.","potential_saving":None})
    daily = sorted(daily_cost.items())
    for previous, current in zip(daily, daily[1:]):
        old, new = previous[1], current[1]
        if old > 0 and new >= old * increase_ratio:
            findings.append({"type":"unusual_cost_increase", "date":current[0].isoformat(),
                "previous_date":previous[0].isoformat(), "previous_cost":str(old), "cost":str(new),
                "increase_ratio":str(new/old), "potential_saving":None})
    return {"record_count":len(records),"actual_historical_cost":str(sum(model_cost.values(),Decimal(0))),"model_spend":{k:str(v) for k,v in model_cost.items()},"provider_spend":{k:str(v) for k,v in provider_cost.items()},"daily_spend":[{"date":d.isoformat(),"cost":str(v)} for d,v in daily],"input_tokens":tokens_in,"output_tokens":tokens_out,"cached_input_tokens":cached,"input_output_ratio":(tokens_in/tokens_out if tokens_out else None),"findings":findings,"limitations":"Potential savings require model pricing and scenario estimates; historical cost alone is not a recommendation. An unusual increase is a threshold signal, not causal attribution."}
