from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PricingOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: int
    model: str
    provider: str
    input_price_per_1k: float
    output_price_per_1k: float
    currency: str
    effective_from: datetime


class ModelOut(BaseModel):
    id: int
    name: str
    provider: str
    display_name: str
    context_window: int | None
    is_active: bool
    pricing: PricingOut | None = None
