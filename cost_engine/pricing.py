"""Centralized model-pricing registry.

Prices live in ``data/pricing.json`` (see config.PRICING_FILE) and nowhere
else. Update prices by editing the JSON or calling ``upsert_pricing``.
"""
from __future__ import annotations

import json
import os
import threading
import tempfile
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import math
from typing import Dict, List, Optional

from . import config
from .currency import is_valid_currency, normalize_currency
from .models import ModelPricing

SUPPORTED_PROVIDERS = {"openai", "google", "gemini", "anthropic", "claude"}

PROVIDER_CANONICAL = {
    "openai": "openai",
    "google": "google",
    "gemini": "google",
    "anthropic": "anthropic",
    "claude": "anthropic",
}

def is_supported_provider(provider: str) -> bool:
    """Check if the provider name is supported."""
    if not isinstance(provider, str):
        return False
    return provider.strip().casefold() in SUPPORTED_PROVIDERS

def normalize_provider(provider: str) -> str:
    """Normalize a provider alias to its canonical name."""
    if not isinstance(provider, str) or not is_supported_provider(provider):
        raise ValueError(f"Unsupported provider: {provider!r}. Supported providers: ['openai', 'google', 'anthropic']")
    return PROVIDER_CANONICAL[provider.strip().casefold()]

_lock = threading.RLock()
_registry: Optional[Dict[str, ModelPricing]] = None
_provider_index: Optional[Dict[str, set[str]]] = None
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
    candidate_history = _history
    try:
        with open(config.PRICING_HISTORY_FILE,"r",encoding="utf-8") as history_file:
            stored_history=json.load(history_file)
        candidate=stored_history.get("models",stored_history) if isinstance(stored_history,dict) else {}
        candidate_history=candidate if isinstance(candidate,dict) else {}
    except FileNotFoundError:
        if isinstance(raw,dict): candidate_history=raw.get("history",candidate_history)
    registry: Dict[str, ModelPricing] = {}
    for item in entries:
        mp = ModelPricing(**item)
        _validate(mp)
        if mp.model in registry: raise ValueError(f"duplicate model identifier {mp.model!r} in pricing catalogue")
        registry[mp.model] = mp
    _history = candidate_history
    return registry


def _validate(mp: ModelPricing) -> None:
    if not isinstance(mp.model, str) or not mp.model.strip():
        raise ValueError("model name must be non-empty")
    if not isinstance(mp.provider, str) or not mp.provider.strip():
        raise ValueError(f"provider is required for model '{mp.model}'")
    if isinstance(mp.quality_tier, bool) or not isinstance(mp.quality_tier, int) or mp.quality_tier not in {1, 2, 3}:
        raise ValueError("quality_tier must be one of 1, 2, or 3")
    if mp.pricing_tier is not None and (not isinstance(mp.pricing_tier, str) or not mp.pricing_tier.strip()):
        raise ValueError("pricing_tier must be a non-empty string when provided")
    if not isinstance(mp.currency, str) or not is_valid_currency(mp.currency):
        raise ValueError(f"Invalid currency code {mp.currency!r}; must be a valid ISO 4217 code")
    if isinstance(mp.pricing_version,bool) or not isinstance(mp.pricing_version,int) or mp.pricing_version < 1:
        raise ValueError("pricing_version must be >= 1")
    if mp.pricing_status not in {"official_verified", "manual_unverified", "estimated", "stale"}:
        raise ValueError("pricing_status must be official_verified, manual_unverified, estimated, or stale")
    if mp.pricing_status == "official_verified" and (not mp.source_url or not mp.last_verified or not mp.retrieved_at):
        raise ValueError("verified pricing requires source_url, last_verified, and retrieved_at")
    for label, value in (("last_verified", mp.last_verified), ("retrieved_at", mp.retrieved_at)):
        if value is not None:
            try:
                parsed_timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed_timestamp.tzinfo is None: raise ValueError
            except (ValueError, TypeError, AttributeError):
                raise ValueError(f"{label} must be a timezone-aware ISO-8601 timestamp") from None
    if mp.pricing_status=="official_verified":
        expected={"openai":"https://developers.openai.com/api/docs/pricing",
                  "anthropic":"https://platform.claude.com/docs/en/about-claude/pricing",
                  "google":"https://ai.google.dev/gemini-api/docs/pricing"}.get(mp.provider.lower())
        if not expected or mp.source_url != expected:
            raise ValueError("verified pricing provider/source URL does not match its registered official source")
    if mp.effective_date:
        try: datetime.fromisoformat(mp.effective_date.replace("Z","+00:00"))
        except (ValueError, TypeError, AttributeError): raise ValueError("effective_date must be ISO-8601") from None
    if mp.pricing_conditions is not None and not isinstance(mp.pricing_conditions,dict):
        raise ValueError("pricing_conditions must be a mapping")
    if mp.pricing_tiers is not None and not isinstance(mp.pricing_tiers,list):
        raise ValueError("pricing_tiers must be a list")
    if mp.context_window is not None and (isinstance(mp.context_window,bool) or not isinstance(mp.context_window,int) or mp.context_window<0):
        raise ValueError("context_window must be a non-negative integer")
    if mp.pricing_tiers:
        for tier in mp.pricing_tiers:
            if not isinstance(tier,dict): raise ValueError("each pricing tier must be a mapping")
            for field in ("input","output","cached_input","cache_write","cache_write_5m",
                          "cache_write_1h","cache_write_30m","cache_write_12h"):
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
        try: legacy_number = float(number)
        except (OverflowError, ValueError):
            raise ValueError(f"{name} exceeds the legacy pricing response range for model '{mp.model}'") from None
        if not math.isfinite(legacy_number):
            raise ValueError(f"{name} exceeds the legacy pricing response range for model '{mp.model}'")
    if mp.source_url is not None:
        if not isinstance(mp.source_url, str) or not mp.source_url.startswith("https://"):
            raise ValueError("source_url must be an https URL")


def _get_registry() -> Dict[str, ModelPricing]:
    global _registry, _provider_index
    with _lock:
        if _registry is None:
            _registry = _load_file()
        if _provider_index is None:
            _provider_index = _build_provider_index(_registry)
        return _registry


def _build_provider_index(registry: Dict[str, ModelPricing]) -> Dict[str, set[str]]:
    index: Dict[str, set[str]] = {}
    for model, entry in registry.items():
        prov = entry.provider.casefold()
        canonical = PROVIDER_CANONICAL.get(prov, prov)
        index.setdefault(prov, set()).add(model)
        index.setdefault(canonical, set()).add(model)
        if canonical == "google":
            index.setdefault("gemini", set()).add(model)
        elif canonical == "anthropic":
            index.setdefault("claude", set()).add(model)
    return index


def reload_pricing(path=None) -> None:
    """Re-read pricing from disk (or from an alternate file)."""
    global _registry, _provider_index
    with _lock:
        candidate = _load_file(path)
        _registry = candidate
        _provider_index = _build_provider_index(candidate)


def get_pricing(model: str) -> ModelPricing:
    # Legacy callers historically received float rates. Return a detached copy
    # so callers cannot mutate the in-memory cache or nested condition data.
    entry = _get_pricing_cached(model)
    legacy=_copy_pricing(entry)
    for name in _PRICE_FIELDS:
        if getattr(legacy,name) is not None: setattr(legacy,name,float(getattr(legacy,name)))
    return legacy


_PRICE_FIELDS=("input_price_per_million","output_price_per_million","cached_input_price_per_million",
               "cache_write_price_per_million","batch_input_price_per_million","batch_output_price_per_million")


def get_pricing_decimal(model: str) -> ModelPricing:
    return _copy_pricing(_get_pricing_cached(model))


def _copy_pricing(entry: ModelPricing) -> ModelPricing:
    """Copy mutable metadata while reusing immutable scalar Decimal values."""
    copied = replace(entry)
    copied.pricing_conditions = deepcopy(entry.pricing_conditions)
    copied.pricing_tiers = deepcopy(entry.pricing_tiers)
    return copied


def _get_pricing_cached(model: str) -> ModelPricing:
    """Internal read-only snapshot; registry entries are replaced, never edited in place."""
    with _lock:
        reg = _get_registry()
        if model not in reg: raise UnknownModelError(f"Unknown model '{model}'. Supported: {sorted(reg)}")
        return reg[model]


def list_models(provider: Optional[str] = None) -> List[str]:
    with _lock:
        reg = _get_registry()
        if provider is None:
            return sorted(reg)
        assert _provider_index is not None
        return sorted(_provider_index.get(provider.casefold(), set()))


def list_pricing(provider: Optional[str] = None) -> List[ModelPricing]:
    return [get_pricing(m) for m in list_models(provider)]


def list_pricing_decimal(provider: Optional[str] = None) -> List[ModelPricing]:
    return [get_pricing_decimal(m) for m in list_models(provider)]


def pricing_cache_info() -> dict:
    """Expose safe diagnostics for the in-memory JSON-backed pricing cache."""
    with _lock:
        reg = _get_registry()
        assert _provider_index is not None
        return {"loaded": True, "model_count": len(reg),
                "providers": {name: len(models) for name, models in sorted(_provider_index.items())}}


def get_pricing_history(model: Optional[str] = None) -> dict | list:
    """Return immutable snapshots of prior price versions."""
    with _lock:
        _get_registry()
        history=_history.get(model,[]) if model is not None else _history
        return json.loads(json.dumps(history,default=str))


def get_pricing_version(model: str, version: int) -> ModelPricing:
    """Resolve a specific current or preserved catalogue version."""
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError("pricing version must be a positive integer")
    current=get_pricing_decimal(model)
    if current.pricing_version==version: return current
    with _lock:
        for item in _history.get(model,[]):
            for key in ("previous","current"):
                snapshot=item.get(key,{})
                if snapshot.get("pricing_version")==version:
                    return ModelPricing(**snapshot)
    raise UnknownModelError(f"Pricing version {version} for model {model!r} is not available")


def pricing_freshness(entry: ModelPricing, max_age_days: int = 30) -> dict:
    """Report stale status without promoting unverified/manual prices to live."""
    try:
        max_age_days = max(1, int(os.getenv("COST_ENGINE_PRICING_MAX_AGE_DAYS", str(max_age_days))))
    except (TypeError, ValueError):
        max_age_days = 30
    if entry.pricing_status != "official_verified" or not entry.last_verified:
        return {"status": entry.pricing_status, "stale": True, "age_days": None}
    try:
        verified = datetime.fromisoformat(entry.last_verified.replace("Z", "+00:00"))
        if verified.tzinfo is None: verified = verified.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError, AttributeError):
        return {"status": "invalid_verification_timestamp", "stale": True, "age_days": None}
    age = max(0, (datetime.now(timezone.utc)-verified).days)
    stale = age > max_age_days
    return {"status": "stale" if stale else "official_verified", "stale": stale, "age_days": age}


def upsert_pricing(entry: ModelPricing, persist: bool = True, *, _provenance=None) -> None:
    """Add or update a model's pricing; optionally write back to the JSON file."""
    entry = _copy_pricing(entry)
    _validate(entry)
    if entry.pricing_status=="official_verified" and _provenance is not _OFFICIAL_ADAPTER_PROVENANCE:
        raise ValueError("official verification can only be written by a registered provider adapter")
    global _provider_index
    reg = _get_registry()
    with _lock:
        old = reg.get(entry.model)
        old_history = deepcopy(_history)
        old_index = _provider_index
        if old is not None and _is_older_verification(old, entry):
            raise ValueError("refusing to replace newer verified pricing with an older snapshot")
        try:
            changed_fields=_changed_price_fields(old,entry) if old is not None else []
            if old is not None and changed_fields:
                entry.pricing_version = max(entry.pricing_version, old.pricing_version + 1)
                _history.setdefault(entry.model, []).append({
                    "changed_at": datetime.now(timezone.utc).isoformat(),
                    "retrieved_at": entry.retrieved_at, "verified_at": entry.last_verified,
                    "effective_date": entry.effective_date, "provider": entry.provider,
                    "model": entry.model, "pricing_version": entry.pricing_version,
                    "source_url": entry.source_url, "changed_fields": changed_fields,
                    "previous": old.to_dict(), "current": entry.to_dict(),
                })
            elif old is not None:
                entry.pricing_version=old.pricing_version
            reg[entry.model] = entry
            _provider_index = _build_provider_index(reg)
            if persist:
                save_pricing()
        except Exception:
            if old is None:
                reg.pop(entry.model, None)
            else:
                reg[entry.model] = old
            _history.clear(); _history.update(old_history)
            _provider_index = old_index or _build_provider_index(reg)
            raise


def save_pricing(path=None) -> None:
    path = path or config.PRICING_FILE
    with _lock:
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
    fields=(*_PRICE_FIELDS,"pricing_tier","pricing_conditions","pricing_tiers","currency",
            "effective_date","context_window","provider","pricing_unit")
    return [field for field in fields if getattr(old,field,None)!=getattr(new,field,None)]


def _is_older_verification(old: ModelPricing, new: ModelPricing) -> bool:
    if old.pricing_status != "official_verified" or new.pricing_status != "official_verified":
        return False
    try:
        old_time = datetime.fromisoformat((old.last_verified or "").replace("Z", "+00:00"))
        new_time = datetime.fromisoformat((new.last_verified or "").replace("Z", "+00:00"))
        if old_time.tzinfo is None: old_time = old_time.replace(tzinfo=timezone.utc)
        if new_time.tzinfo is None: new_time = new_time.replace(tzinfo=timezone.utc)
        return new_time < old_time
    except (TypeError, ValueError):
        return False


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
    entries = [_copy_pricing(entry) for entry in entries]
    seen=set()
    for entry in entries:
        _validate(entry)
        if entry.pricing_status=="official_verified" and _provenance is not _OFFICIAL_ADAPTER_PROVENANCE:
            raise ValueError("official verification can only be written by a registered provider adapter")
        if entry.model in seen: raise ValueError(f"duplicate model in provider snapshot: {entry.model}")
        seen.add(entry.model)
    global _provider_index
    registry=_get_registry()
    with _lock:
        old_registry=dict(registry); old_history=json.loads(json.dumps(_history,default=str))
        try:
            for entry in entries:
                old=old_registry.get(entry.model)
                if old and _is_older_verification(old,entry):
                    raise ValueError(f"refusing to replace newer verified pricing for {entry.model!r} with an older snapshot")
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
            _provider_index = _build_provider_index(_registry)
            save_pricing()
        except Exception:
            _registry.clear(); _registry.update(old_registry)
            _history.clear(); _history.update(old_history)
            _provider_index = _build_provider_index(_registry)
            raise
