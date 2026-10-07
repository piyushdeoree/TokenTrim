from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.llm_model import LLMModel, ModelPricing
from app.repositories import model_repository
from app.schemas.llm_model import ModelOut, PricingOut


def current_pricing(model: LLMModel) -> ModelPricing | None:
    return model.pricing[0] if model.pricing else None  # relationship is ordered newest-first


def pricing_out(model: LLMModel) -> PricingOut | None:
    p = current_pricing(model)
    if p is None:
        return None
    return PricingOut(
        model_id=model.id, model=model.name, provider=model.provider,
        input_price_per_1k=float(p.input_price_per_1k), output_price_per_1k=float(p.output_price_per_1k),
        currency=p.currency, effective_from=p.effective_from)


def model_out(model: LLMModel) -> ModelOut:
    return ModelOut(id=model.id, name=model.name, provider=model.provider, display_name=model.display_name,
                    context_window=model.context_window, is_active=model.is_active, pricing=pricing_out(model))


def list_models(db: Session) -> list[ModelOut]:
    return [model_out(m) for m in model_repository.list_active(db)]


def list_pricing(db: Session) -> list[PricingOut]:
    return [p for m in model_repository.list_active(db) if (p := pricing_out(m))]


def get_model(db: Session, model_id: int) -> ModelOut:
    m = model_repository.get(db, model_id)
    if m is None:
        raise NotFoundError("Model not found.")
    return model_out(m)
