"""Typed data structures shared across the cost engine.

Plain dataclasses with `to_dict()` so Person 3 can return them from FastAPI
directly (or wrap them in Pydantic models).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Optional, Any
from decimal import Decimal, InvalidOperation


@dataclass
class ModelPricing:
    model: str
    provider: str
    input_price_per_million: Decimal
    output_price_per_million: Decimal
    context_window: Optional[int] = None
    quality_tier: int = 2  # 1 = basic, 2 = standard, 3 = frontier (editable judgment)
    notes: str = ""
    display_name: Optional[str] = None
    cached_input_price_per_million: Optional[Decimal] = None
    cache_write_price_per_million: Optional[Decimal] = None
    batch_input_price_per_million: Optional[Decimal] = None
    batch_output_price_per_million: Optional[Decimal] = None
    currency: str = "USD"
    pricing_tier: Optional[str] = None
    effective_date: Optional[str] = None
    source_url: Optional[str] = None
    last_verified: Optional[str] = None
    pricing_status: str = "manual_unverified"
    pricing_version: int = 1
    retrieved_at: Optional[str] = None
    pricing_conditions: Optional[dict] = None
    pricing_tiers: Optional[list] = None
    pricing_unit: str = "per 1,000,000 tokens"

    @property
    def pricing_source(self) -> Optional[str]:
        return self.source_url

    @property
    def verification_status(self) -> str:
        return self.pricing_status

    @property
    def last_updated(self) -> Optional[str]:
        return self.last_verified or self.retrieved_at

    def __post_init__(self):
        for name in ("input_price_per_million", "output_price_per_million",
                     "cached_input_price_per_million", "cache_write_price_per_million",
                     "batch_input_price_per_million", "batch_output_price_per_million"):
            value=getattr(self,name)
            if value is not None and not isinstance(value,Decimal):
                try: setattr(self,name,Decimal(str(value)))
                except (InvalidOperation, TypeError, ValueError):
                    raise ValueError(f"{name} must be a decimal value") from None
        if self.pricing_tiers is not None:
            normalized = []
            tier_rates = ("input", "output", "cached_input", "cache_write",
                          "cache_write_5m", "cache_write_1h", "cache_write_30m", "cache_write_12h")
            for tier in self.pricing_tiers:
                if not isinstance(tier, dict):
                    normalized.append(tier)
                    continue
                tier = dict(tier)
                for name in tier_rates:
                    value = tier.get(name)
                    if value is not None and not isinstance(value, Decimal):
                        try: tier[name] = Decimal(str(value))
                        except (InvalidOperation, TypeError, ValueError):
                            raise ValueError(f"pricing tier {name} must be a decimal value") from None
                normalized.append(tier)
            self.pricing_tiers = normalized

    def to_dict(self) -> dict:
        data=asdict(self)
        for name in ("input_price_per_million", "output_price_per_million",
                     "cached_input_price_per_million", "cache_write_price_per_million",
                     "batch_input_price_per_million", "batch_output_price_per_million"):
            if data[name] is not None: data[name]=str(data[name])
        return data


@dataclass
class CostBreakdown:
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    provider: Optional[str] = None
    pricing_version: int = 1
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    batch: bool = False
    pricing_tier: str = "standard"
    applied_input_rate: Optional[float] = None
    applied_output_rate: Optional[float] = None
    other_charges: float = 0.0
    currency: str = "USD"
    calculation_timestamp: Optional[str] = None
    estimate_type: str = "estimated"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CostEstimate:
    """Estimated cost: output tokens are PREDICTED, not billed values."""

    model: str
    input_tokens: int
    predicted_output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    estimated_cost: float
    prediction_source: str = "caller_supplied"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_api_dict(self) -> dict:
        """Section 10 'required output' shape."""
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "predicted_output_tokens": self.predicted_output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_input_cost": self.input_cost,
            "estimated_output_cost": self.output_cost,
            "estimated_total_cost": self.estimated_cost,
        }


@dataclass
class SavingsResult:
    """Consumes Person 1's optimization output."""

    model: str
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    optimization_percentage: float
    original_input_cost: float
    optimized_input_cost: float
    input_cost_saved: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ActualCostResult:
    """Calculated execution cost using actual provider-reported token usage.

    Standardized result contract for BYOK (Bring Your Own API Key) integrations.
    """
    provider: str
    model: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    actual_cost: Optional[float]
    currency: Optional[str]
    pricing_status: str
    pricing_verification: Optional[str]
    actual_cost_decimal: Optional[Decimal] = None
    input_cost: Optional[float] = None
    output_cost: Optional[float] = None
    input_cost_decimal: Optional[Decimal] = None
    output_cost_decimal: Optional[Decimal] = None
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    pricing_unit: str = "per 1,000,000 tokens"
    pricing_source: Optional[str] = None
    last_verified: Optional[str] = None
    pricing_version: Optional[int] = None
    estimate_type: str = "actual"
    calculation_timestamp: Optional[str] = None
    applied_input_rate: Optional[float] = None
    applied_output_rate: Optional[float] = None
    unsupported_components: list[str] = field(default_factory=list)
    error_details: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.actual_cost_decimal is not None:
            data["actual_cost_decimal"] = str(self.actual_cost_decimal)
        if self.input_cost_decimal is not None:
            data["input_cost_decimal"] = str(self.input_cost_decimal)
        if self.output_cost_decimal is not None:
            data["output_cost_decimal"] = str(self.output_cost_decimal)
        return data

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self.to_dict()

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    def items(self):
        return self.to_dict().items()

