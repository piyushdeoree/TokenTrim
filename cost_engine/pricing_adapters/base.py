"""Shared strict parsing helpers; all monetary outputs are Decimal."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re

PRICE_RE=re.compile(r"^\s*\$\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]*\.[0-9]+)\s*(?:USD\s*)?(?:/\s*(?:MTok|1M tokens?))?\s*$",re.I)

def price(value: str, *, optional=False):
    value=re.sub(r"<sup>.*?</sup>","",str(value),flags=re.I)
    value=re.sub(r"<[^>]*>","",value).strip()
    if value in {"-","—","–",""}:
        if optional:return None
        raise ValueError("required price is missing")
    match=PRICE_RE.match(value)
    if not match: raise ValueError(f"unsupported price format: {value!r}")
    try: result=Decimal(match.group(1).replace(",",""))
    except InvalidOperation: raise ValueError(f"invalid decimal price: {value!r}") from None
    if not result.is_finite() or result<0: raise ValueError("price must be finite and non-negative")
    return result

def finish(provider, source_url, model, display_name, inputs, outputs, *, cached=None, cache_write=None,
           batch_input=None,batch_output=None,tier="standard",conditions=None,tiers=None,effective_date=None,notes="",context_window=None):
    if not isinstance(model,str) or not model.strip(): raise ValueError("model identifier is missing")
    now=datetime.now(timezone.utc).isoformat()
    return {"model":model,"display_name":display_name or model,"provider":provider,
        "input_price_per_million":inputs,"output_price_per_million":outputs,
        "cached_input_price_per_million":cached,"cache_write_price_per_million":cache_write,
        "batch_input_price_per_million":batch_input,"batch_output_price_per_million":batch_output,
        "currency":"USD","pricing_tier":tier,"pricing_conditions":conditions or {},
        "pricing_tiers":tiers or [],"effective_date":effective_date,"context_window":context_window,
        "source_url":source_url,"retrieved_at":now,"last_verified":now,
        "pricing_status":"official_verified","notes":notes}

def table_rows(markdown):
    for line in markdown.splitlines():
        line=line.strip()
        if not line.startswith("|"): continue
        cells=[x.strip() for x in line.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?",c.replace(" ","")) for c in cells): continue
        yield cells

def model_key(label):
    """Normalize displayed Anthropic name to its documented public ID convention."""
    clean=re.sub(r"\s*\([^)]*\)","",label).strip()
    match=re.match(r"(?:Claude\s+)?(Fable|Mythos|Opus|Sonnet|Haiku)\s+([0-9]+(?:\.[0-9]+)*)",clean,re.I)
    if match: return "claude-"+match.group(1).lower()+"-"+match.group(2).replace(".","-")
    return re.sub(r"[^a-z0-9]+","-",clean.lower()).strip("-")
