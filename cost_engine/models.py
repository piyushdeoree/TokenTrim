"""Typed data structures shared across the cost engine.

Plain dataclasses with `to_dict()` so Person 3 can return them from FastAPI
directly (or wrap them in Pydantic models).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Optional


@dataclass
class ModelPricing:
    model: str
    provider: str
    input_price_per_million: float
    output_price_per_million: float
    context_window: Optional[int] = None
    quality_tier: int = 2  # 1 = basic, 2 = standard, 3 = frontier (editable judgment)
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CostBreakdown:
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float

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
