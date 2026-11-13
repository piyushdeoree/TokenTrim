"""Official provider refresh orchestration with fail-closed validation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import urllib.request

from . import config
from .models import ModelPricing
from .pricing import (list_pricing_decimal, upsert_pricing_batch,
                      _OFFICIAL_ADAPTER_PROVENANCE)
from .pricing_adapters import PARSERS
from .pricing_adapters.openai import FETCH_URL as OPENAI_FETCH_URL
from .pricing_adapters.anthropic import FETCH_URL as ANTHROPIC_FETCH_URL
from .pricing_adapters.google import FETCH_URL as GOOGLE_FETCH_URL

OFFICIAL_SOURCES={
    "openai":"https://developers.openai.com/api/docs/pricing",
    "anthropic":"https://platform.claude.com/docs/en/about-claude/pricing",
    "google":"https://ai.google.dev/gemini-api/docs/pricing",
}
FETCH_URLS={"openai":OPENAI_FETCH_URL,"anthropic":ANTHROPIC_FETCH_URL,"google":GOOGLE_FETCH_URL}
REFRESH_INTERVAL_HOURS=max(1,int(os.getenv("COST_ENGINE_REFRESH_INTERVAL_HOURS","24")))
REFRESH_STATE_FILE=config.DATA_DIR/"pricing_refresh_state.json"
_ADAPTER_PROVENANCE=_OFFICIAL_ADAPTER_PROVENANCE

def _now(): return datetime.now(timezone.utc).isoformat()

def fetch_provider_page(provider: str, *, timeout: float=20.0) -> str:
    """Fetch only the registered official source (Markdown where provider supports it)."""
    if provider not in FETCH_URLS: raise ValueError(f"unsupported provider {provider!r}")
    request=urllib.request.Request(FETCH_URLS[provider],headers={
        "User-Agent":"TokenTrim-CostEngine/1.0 (+official-pricing-refresh)",
        "Accept":"text/markdown,text/html;q=0.9,*/*;q=0.1"})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        final=response.geturl()
        # urllib.parse is the canonical parser; reject unexpected redirects.
        from urllib.parse import urlparse
        host=urlparse(final).hostname or ""
        allowed={"openai":{"developers.openai.com"},
                 "anthropic":{"platform.claude.com"},
                 "google":{"ai.google.dev","aistudio.google.com"}}[provider]
        if host not in allowed: raise ValueError(f"official source redirected to untrusted host {host!r}")
        data=response.read()
        charset="utf-8"
        headers=response.headers
        content_type=headers.get_content_charset() if hasattr(headers,"get_content_charset") else None
        if content_type: charset=content_type
        return data.decode(charset,"replace")

def validate_official_rows(provider: str, rows: list[dict], source_url: str, *, _provenance=None) -> list[ModelPricing]:
    """Validate records emitted by a provider parser; arbitrary/manual data is rejected."""
    if _provenance is not _ADAPTER_PROVENANCE:
        raise ValueError("official verification requires a provider adapter parse of the fetched source")
    if provider not in OFFICIAL_SOURCES or source_url!=OFFICIAL_SOURCES[provider]:
        raise ValueError("pricing source must be the registered official provider URL")
    if not isinstance(rows,list) or not rows: raise ValueError("no pricing rows parsed; refusing empty verified snapshot")
    entries=[]; seen=set()
    for row in rows:
        if not isinstance(row,dict): raise ValueError("pricing row must be an object")
        if row.get("provider")!=provider or row.get("source_url")!=source_url:
            raise ValueError("provider parser returned mismatched source identity")
        required=("model","input_price_per_million","output_price_per_million","retrieved_at","last_verified")
        if any(row.get(k) in (None,"") for k in required): raise ValueError("pricing row is incomplete")
        if row["model"] in seen: raise ValueError(f"duplicate model row {row['model']!r}")
        seen.add(row["model"])
        try:
            for field in ("input_price_per_million","output_price_per_million","cached_input_price_per_million",
                          "cache_write_price_per_million","batch_input_price_per_million","batch_output_price_per_million"):
                value=row.get(field)
                if value is None: continue
                amount=value if isinstance(value,Decimal) else Decimal(str(value))
                if not amount.is_finite() or amount<0: raise ValueError(f"invalid {field}")
                row[field]=amount
        except (InvalidOperation,TypeError) as exc: raise ValueError(f"invalid decimal pricing: {exc}") from None
        row["pricing_status"]="official_verified"
        # Older sources may not state an effective date. Do not invent one.
        allowed=set(ModelPricing.__dataclass_fields__)
        entry=ModelPricing(**{k:v for k,v in row.items() if k in allowed})
        from .pricing import _validate
        _validate(entry)
        entries.append(entry)
    return entries

def refresh_provider(provider: str, *, timeout: float=20.0) -> dict:
    if provider not in OFFICIAL_SOURCES: raise ValueError(f"unsupported provider {provider!r}")
    started=_now()
    try:
        page=fetch_provider_page(provider,timeout=timeout)
        rows=PARSERS[provider](page)
        entries=validate_official_rows(provider,rows,OFFICIAL_SOURCES[provider],_provenance=_ADAPTER_PROVENANCE)
        # A provider update is all-or-nothing after every model row validates.
        before={p.model:p.pricing_version for p in list_pricing_decimal() if p.provider==provider}
        upsert_pricing_batch(entries,_provenance=_ADAPTER_PROVENANCE)
        changed=[e.model for e in entries if e.pricing_version!=before.get(e.model,0)]
        report={"provider":provider,"ok":True,"model_count":len(entries),"models":[e.model for e in entries],
                "pricing_changed_models":changed,"last_attempt":started,"last_successful_refresh":_now()}
    except Exception as exc:
        report={"provider":provider,"ok":False,"error":f"{type(exc).__name__}: {exc}","last_attempt":started}
    state=_read_state(); providers=state.setdefault("providers",{}); previous=providers.get(provider,{})
    if not report.get("ok"): report["last_successful_refresh"]=previous.get("last_successful_refresh")
    providers[provider]=report; state["last_attempt"]=_now()
    if report.get("ok"): state["last_successful_refresh"]=_now()
    state["refresh_interval_hours"]=REFRESH_INTERVAL_HOURS
    REFRESH_STATE_FILE.parent.mkdir(parents=True,exist_ok=True)
    tmp=REFRESH_STATE_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps(state,indent=2),encoding="utf-8"); os.replace(tmp,REFRESH_STATE_FILE)
    return report

def refresh_openai_pricing(*,timeout:float=20.0): return refresh_provider("openai",timeout=timeout)
def refresh_anthropic_pricing(*,timeout:float=20.0): return refresh_provider("anthropic",timeout=timeout)
def refresh_google_pricing(*,timeout:float=20.0): return refresh_provider("google",timeout=timeout)

def _read_state():
    try: return json.loads(REFRESH_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError,ValueError): return {"providers":{}}

def refresh_pricing(*,timeout:float=20.0,force:bool=False) -> dict:
    """Refresh providers due by interval; pass force=True for an immediate manual refresh."""
    prior=_read_state(); provider_state=prior.get("providers",{}); reports={}
    now_dt=datetime.now(timezone.utc)
    for provider in OFFICIAL_SOURCES:
        old=provider_state.get(provider,{})
        last=old.get("last_successful_refresh")
        if not force and last:
            try:
                last_dt=datetime.fromisoformat(last.replace("Z","+00:00"))
                if last_dt.tzinfo is None: last_dt=last_dt.replace(tzinfo=timezone.utc)
                if now_dt-last_dt < timedelta(hours=REFRESH_INTERVAL_HOURS):
                    reports[provider]={**old,"provider":provider,"ok":True,"skipped":True,
                        "reason":"refresh interval has not elapsed","last_successful_refresh":last}
                    continue
            except (ValueError,TypeError): pass
        report=refresh_provider(provider,timeout=timeout)
        if report["ok"]:
            report["last_successful_refresh"]=_now()
        else:
            report["last_successful_refresh"]=old.get("last_successful_refresh")
        reports[provider]=report
    now=_now()
    complete_cycle=any(r.get("ok") and not r.get("skipped") for r in reports.values()) and all(r.get("ok") for r in reports.values())
    state={"last_attempt":now,"last_successful_refresh":now if complete_cycle else prior.get("last_successful_refresh"),
           "refresh_interval_hours":REFRESH_INTERVAL_HOURS,"providers":reports}
    REFRESH_STATE_FILE.parent.mkdir(parents=True,exist_ok=True)
    tmp=REFRESH_STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state,indent=2),encoding="utf-8"); os.replace(tmp,REFRESH_STATE_FILE)
    return state

def manual_pricing_update(record: dict, *, verified: bool=False) -> ModelPricing:
    """Manual data is never verified by URL assertion; only fetched parser output can verify it."""
    if verified: raise ValueError("manual records cannot be marked official_verified; refresh the official provider adapter")
    values=dict(record); values["pricing_status"]="manual_unverified"; values["last_verified"]=None
    entry=ModelPricing(**values)
    from .pricing import upsert_pricing
    upsert_pricing(entry)
    return entry
