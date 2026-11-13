"""Typed data structures shared across the cost engine.

Plain dataclasses with `to_dict()` so Person 3 can return them from FastAPI
directly (or wrap them in Pydantic models).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional
from decimal import Decimal


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

    def __post_init__(self):
        for name in ("input_price_per_million", "output_price_per_million",
                     "cached_input_price_per_million", "cache_write_price_per_million",
                     "batch_input_price_per_million", "batch_output_price_per_million"):
            value=getattr(self,name)
            if value is not None and not isinstance(value,Decimal):
                setattr(self,name,Decimal(str(value)))

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
