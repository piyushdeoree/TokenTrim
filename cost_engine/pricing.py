"""Centralized model-pricing registry.

Prices live in ``data/pricing.json`` (see config.PRICING_FILE) and nowhere
else. Update prices by editing the JSON or calling ``upsert_pricing``.
"""
from __future__ import annotations

import json
import os
import threading
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional
from urllib.parse import urlparse

from . import config
from .models import ModelPricing

_lock = threading.RLock()
_registry: Optional[Dict[str, ModelPricing]] = None
_history: Dict[str, List[dict]] = {}
_OFFICIAL_ADAPTER_PROVENANCE=object()


class UnknownModelError(KeyError):
    """Raised when a model is not present in the pricing registry."""


def _load_file(path=None) -> Dict[str, ModelPricing]:
    global _history
    path = path or config.PRICING_FILE
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f,parse_float=Decimal)
    entries = raw["models"] if isinstance(raw, dict) else raw
    try:
        with open(config.PRICING_HISTORY_FILE,"r",encoding="utf-8") as history_file:
            stored_history=json.load(history_file)
        candidate=stored_history.get("models",stored_history) if isinstance(stored_history,dict) else {}
        _history=candidate if isinstance(candidate,dict) else {}
    except FileNotFoundError:
        if isinstance(raw,dict): _history=raw.get("history",_history)
    registry: Dict[str, ModelPricing] = {}
    for item in entries:
        mp = ModelPricing(**item)
        _validate(mp)
        if mp.model in registry: raise ValueError(f"duplicate model identifier {mp.model!r} in pricing catalogue")
        registry[mp.model] = mp
    return registry


def _validate(mp: ModelPricing) -> None:
    if not isinstance(mp.model, str) or not mp.model.strip():
        raise ValueError("model name must be non-empty")
    if not isinstance(mp.provider, str) or not mp.provider.strip():
        raise ValueError(f"provider is required for model '{mp.model}'")
    if mp.currency != "USD":
        raise ValueError("Provider catalogue rates must use USD; convert for display separately")
    if isinstance(mp.pricing_version,bool) or not isinstance(mp.pricing_version,int) or mp.pricing_version < 1:
        raise ValueError("pricing_version must be >= 1")
    if mp.pricing_status not in {"official_verified", "manual_unverified", "estimated", "stale"}:
        raise ValueError("pricing_status must be official_verified, manual_unverified, estimated, or stale")
    if mp.pricing_status == "official_verified" and (not mp.source_url or not mp.last_verified or not mp.retrieved_at):
        raise ValueError("verified pricing requires source_url, last_verified, and retrieved_at")
    if mp.pricing_status=="official_verified":
        expected={"openai":"developers.openai.com","anthropic":"platform.claude.com","google":"ai.google.dev"}.get(mp.provider.lower())
        if not expected or urlparse(mp.source_url).hostname!=expected:
            raise ValueError("verified pricing provider does not match its registered official source host")
        for label,value in (("last_verified",mp.last_verified),("retrieved_at",mp.retrieved_at)):
            try: datetime.fromisoformat(value.replace("Z","+00:00"))
            except (ValueError,AttributeError): raise ValueError(f"{label} must be ISO-8601") from None
    if mp.effective_date:
        try: datetime.fromisoformat(mp.effective_date.replace("Z","+00:00"))
        except ValueError: raise ValueError("effective_date must be ISO-8601") from None
    if mp.pricing_conditions is not None and not isinstance(mp.pricing_conditions,dict):
        raise ValueError("pricing_conditions must be a mapping")
    if mp.pricing_tiers is not None and not isinstance(mp.pricing_tiers,list):
        raise ValueError("pricing_tiers must be a list")
    if mp.context_window is not None and (isinstance(mp.context_window,bool) or not isinstance(mp.context_window,int) or mp.context_window<0):
        raise ValueError("context_window must be a non-negative integer")
    if mp.pricing_tiers:
        for tier in mp.pricing_tiers:
            if not isinstance(tier,dict): raise ValueError("each pricing tier must be a mapping")
            for field in ("input","output","cached_input","cache_write_30m","cache_write_1h","cache_write_12h"):
                value=tier.get(field)
                if value is None: continue
                try: amount=value if isinstance(value,Decimal) else Decimal(str(value))
                except (InvalidOperation,TypeError): raise ValueError(f"invalid {field} in pricing_tiers") from None
                if not amount.is_finite() or amount<0: raise ValueError(f"{field} in pricing_tiers must be finite and non-negative")
    for name in ("input_price_per_million", "output_price_per_million",
                 "cached_input_price_per_million", "cache_write_price_per_million",
                 "batch_input_price_per_million", "batch_output_price_per_million"):
        value = getattr(mp, name)
        if value is None and name not in ("input_price_per_million", "output_price_per_million"):
            continue
        try:
            number = value if isinstance(value,Decimal) else Decimal(str(value))
        except (InvalidOperation, TypeError):
            raise ValueError(f"invalid {name} for model '{mp.model}'") from None
        if not number.is_finite() or number < 0:
            raise ValueError(f"{name} must be finite and non-negative for model '{mp.model}'")
    if mp.source_url and not mp.source_url.startswith("https://"):
        raise ValueError("source_url must use https")


def _get_registry() -> Dict[str, ModelPricing]:
    global _registry
    with _lock:
        if _registry is None:
            _registry = _load_file()
        return _registry


def reload_pricing(path=None) -> None:
    """Re-read pricing from disk (or from an alternate file)."""
    global _registry
    with _lock:
        _registry = _load_file(path)


def get_pricing(model: str) -> ModelPricing:
    reg = _get_registry()
    if model not in reg:
        raise UnknownModelError(
            f"Unknown model '{model}'. Supported: {sorted(reg)}"
        )
    # Legacy callers historically received float rates. Internal finance paths
    # use get_pricing_decimal() and retain Decimal end to end.
    entry=reg[model]
    legacy=replace(entry)
    for name in _PRICE_FIELDS:
        if getattr(legacy,name) is not None: setattr(legacy,name,float(getattr(legacy,name)))
    return legacy


_PRICE_FIELDS=("input_price_per_million","output_price_per_million","cached_input_price_per_million",
               "cache_write_price_per_million","batch_input_price_per_million","batch_output_price_per_million")


def get_pricing_decimal(model: str) -> ModelPricing:
    reg=_get_registry()
    if model not in reg: raise UnknownModelError(f"Unknown model '{model}'. Supported: {sorted(reg)}")
    return reg[model]


def list_models() -> List[str]:
    return sorted(_get_registry())


def list_pricing() -> List[ModelPricing]:
    return [get_pricing(m) for m in list_models()]


def list_pricing_decimal() -> List[ModelPricing]:
    return [_get_registry()[m] for m in list_models()]


def get_pricing_history(model: Optional[str] = None) -> dict | list:
    """Return immutable snapshots of prior price versions."""
    _get_registry()
    history=_history.get(model,[]) if model is not None else _history
    return json.loads(json.dumps(history,default=str))


def get_pricing_version(model: str, version: int) -> ModelPricing:
    """Resolve a specific current or preserved catalogue version."""
    current=get_pricing_decimal(model)
    if current.pricing_version==version: return current
    for item in _history.get(model,[]):
        for key in ("previous","current"):
            snapshot=item.get(key,{})
            if snapshot.get("pricing_version")==version:
                return ModelPricing(**snapshot)
    raise UnknownModelError(f"Pricing version {version} for model {model!r} is not available")


def pricing_freshness(entry: ModelPricing, max_age_days: int = 30) -> dict:
    """Report stale status without promoting unverified/manual prices to live."""
    max_age_days = max(1, int(os.getenv("COST_ENGINE_PRICING_MAX_AGE_DAYS", str(max_age_days))))
    if entry.pricing_status != "official_verified" or not entry.last_verified:
        return {"status": entry.pricing_status, "stale": True, "age_days": None}
    try:
        verified = datetime.fromisoformat(entry.last_verified.replace("Z", "+00:00"))
        if verified.tzinfo is None: verified = verified.replace(tzinfo=timezone.utc)
    except ValueError:
        return {"status": "invalid_verification_timestamp", "stale": True, "age_days": None}
    age = max(0, (datetime.now(timezone.utc)-verified).days)
    stale = age > max_age_days
    return {"status": "stale" if stale else "official_verified", "stale": stale, "age_days": age}


def upsert_pricing(entry: ModelPricing, persist: bool = True, *, _provenance=None) -> None:
    """Add or update a model's pricing; optionally write back to the JSON file."""
    _validate(entry)
    if entry.pricing_status=="official_verified" and _provenance is not _OFFICIAL_ADAPTER_PROVENANCE:
        raise ValueError("official verification can only be written by a registered provider adapter")
    reg = _get_registry()
    with _lock:
        old = reg.get(entry.model)
        changed_fields=_changed_price_fields(old,entry) if old is not None else []
        if old is not None and changed_fields:
            changed = changed_fields
            entry.pricing_version = max(entry.pricing_version, old.pricing_version + 1)
            _history.setdefault(entry.model, []).append({
                "changed_at": datetime.now(timezone.utc).isoformat(),
                "source_url": entry.source_url, "changed_fields": changed,
                "previous": old.to_dict(), "current": entry.to_dict(),
            })
        elif old is not None:
            # Verification refresh is metadata, not a new price version.
            entry.pricing_version=old.pricing_version
        reg[entry.model] = entry
    if persist:
        save_pricing()


def save_pricing(path=None) -> None:
    path = path or config.PRICING_FILE
    reg = _get_registry()
    meta = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if isinstance(existing, dict):
            meta = existing.get("_meta", {})
    except FileNotFoundError:
        pass
    payload = {"_meta": meta, "models": [reg[m].to_dict() for m in sorted(reg)]}
    _atomic_json(path,payload)
    _atomic_json(config.PRICING_HISTORY_FILE,{"models":_history})


def _changed_price_fields(old: ModelPricing, new: ModelPricing) -> list[str]:
    fields=(*_PRICE_FIELDS,"pricing_tier","pricing_conditions","pricing_tiers","currency")
    return [field for field in fields if getattr(old,field)!=getattr(new,field)]


def _atomic_json(path,payload):
    path=os.fspath(path); directory=os.path.dirname(path) or "."
    os.makedirs(directory,exist_ok=True)
    handle,tmp=tempfile.mkstemp(prefix=".pricing-",suffix=".tmp",dir=directory)
    try:
        with os.fdopen(handle,"w",encoding="utf-8") as out: json.dump(payload,out,indent=2,default=str)
        os.replace(tmp,path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def upsert_pricing_batch(entries: list[ModelPricing], *, _provenance=None) -> None:
    """Validate then apply one provider snapshot, preserving the prior registry on failure."""
    if not entries: raise ValueError("provider snapshot contains no pricing entries")
    seen=set()
    for entry in entries:
        _validate(entry)
        if entry.pricing_status=="official_verified" and _provenance is not _OFFICIAL_ADAPTER_PROVENANCE:
            raise ValueError("official verification can only be written by a registered provider adapter")
        if entry.model in seen: raise ValueError(f"duplicate model in provider snapshot: {entry.model}")
        seen.add(entry.model)
    registry=_get_registry()
    with _lock:
        old_registry=dict(registry); old_history=json.loads(json.dumps(_history,default=str))
        try:
            for entry in entries:
                old=old_registry.get(entry.model)
                changed=_changed_price_fields(old,entry) if old else []
                if old and changed:
                    entry.pricing_version=max(entry.pricing_version,old.pricing_version+1)
                    _history.setdefault(entry.model,[]).append({"changed_at":datetime.now(timezone.utc).isoformat(),
                        "retrieved_at":entry.retrieved_at,"verified_at":entry.last_verified,
                        "effective_date":entry.effective_date,"source_url":entry.source_url,
                        "model":entry.model,"provider":entry.provider,"pricing_version":entry.pricing_version,
                        "changed_fields":changed,"previous":old.to_dict(),"current":entry.to_dict()})
                elif old:
                    entry.pricing_version=old.pricing_version
                _registry[entry.model]=entry
            save_pricing()
        except Exception:
            _registry.clear(); _registry.update(old_registry)
            _history.clear(); _history.update(old_history)
            raise
