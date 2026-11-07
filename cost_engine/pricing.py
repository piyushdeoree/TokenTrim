"""Centralized model-pricing registry.

Prices live in ``data/pricing.json`` (see config.PRICING_FILE) and nowhere
else. Update prices by editing the JSON or calling ``upsert_pricing``.
"""
from __future__ import annotations

import json
import threading
from typing import Dict, List, Optional

from . import config
from .models import ModelPricing

_lock = threading.Lock()
_registry: Optional[Dict[str, ModelPricing]] = None


class UnknownModelError(KeyError):
    """Raised when a model is not present in the pricing registry."""


def _load_file(path=None) -> Dict[str, ModelPricing]:
    path = path or config.PRICING_FILE
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    entries = raw["models"] if isinstance(raw, dict) else raw
    registry: Dict[str, ModelPricing] = {}
    for item in entries:
        mp = ModelPricing(**item)
        _validate(mp)
        registry[mp.model] = mp
    return registry


def _validate(mp: ModelPricing) -> None:
    if not mp.model:
        raise ValueError("model name must be non-empty")
    if mp.input_price_per_million < 0 or mp.output_price_per_million < 0:
        raise ValueError(f"negative price for model '{mp.model}'")


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
    return reg[model]


def list_models() -> List[str]:
    return sorted(_get_registry())


def list_pricing() -> List[ModelPricing]:
    return [_get_registry()[m] for m in list_models()]


def upsert_pricing(entry: ModelPricing, persist: bool = True) -> None:
    """Add or update a model's pricing; optionally write back to the JSON file."""
    _validate(entry)
    reg = _get_registry()
    with _lock:
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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
