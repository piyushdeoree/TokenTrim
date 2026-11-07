from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import not_found
from app.database.session import get_db
from app.models import AIModel, User
from app.repositories.crud import current_pricing
from app.schemas.schemas import ModelOut, PricingOut, PricingRow

router = APIRouter(prefix="/models", tags=["Models & Pricing"])


def _pricing(db: Session, model_id: int) -> PricingOut | None:
    p = current_pricing(db, model_id)
    return PricingOut(input_price_per_1k=p.input_price_per_1k, output_price_per_1k=p.output_price_per_1k,
                      currency=p.currency, effective_from=p.effective_from) if p else None


def _model_out(db: Session, m: AIModel) -> ModelOut:
    return ModelOut(id=m.id, name=m.name, provider=m.provider, context_window=m.context_window,
                    is_active=m.is_active, pricing=_pricing(db, m.id))


@router.get("", response_model=list[ModelOut], summary="List supported models with current pricing")
def list_models(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_model_out(db, m) for m in db.scalars(select(AIModel).where(AIModel.is_active).order_by(AIModel.id))]


# NOTE: declared before "/{model_id}" so "pricing" is not parsed as an id.
@router.get("/pricing", response_model=list[PricingRow], summary="Current pricing for every active model")
def list_pricing(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = []
    for m in db.scalars(select(AIModel).where(AIModel.is_active).order_by(AIModel.id)):
        p = _pricing(db, m.id)
        if p:
            rows.append(PricingRow(model_id=m.id, model_name=m.name, provider=m.provider, **p.model_dump()))
    return rows


@router.get("/{model_id}", response_model=ModelOut, summary="One model with current pricing")
def get_model(model_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.get(AIModel, model_id)
    if m is None:
        raise not_found("model")
    return _model_out(db, m)
