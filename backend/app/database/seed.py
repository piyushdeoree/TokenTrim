"""Seeds sample models/pricing so the backend runs standalone.

The prices below are ILLUSTRATIVE PLACEHOLDERS. Person 2's pricing module (or an admin
script) should replace them with real provider prices. Pricing lives only in the database;
the frontend reads it from GET /models/pricing.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.llm_model import LLMModel, ModelPricing

SAMPLE = [
    # name, provider, display, context, input $/1k, output $/1k
    ("gpt-4o", "openai", "GPT-4o", 128000, "0.0025", "0.0100"),
    ("gpt-4o-mini", "openai", "GPT-4o mini", 128000, "0.00015", "0.0006"),
    ("claude-sonnet", "anthropic", "Claude Sonnet", 200000, "0.0030", "0.0150"),
    ("claude-haiku", "anthropic", "Claude Haiku", 200000, "0.0008", "0.0040"),
]


def seed_models(db: Session) -> None:
    if db.scalar(select(LLMModel.id).limit(1)) is not None:
        return
    for name, provider, display, ctx, p_in, p_out in SAMPLE:
        m = LLMModel(name=name, provider=provider, display_name=display, context_window=ctx)
        m.pricing.append(ModelPricing(input_price_per_1k=Decimal(p_in), output_price_per_1k=Decimal(p_out)))
        db.add(m)
    db.commit()
