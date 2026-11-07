from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.llm_model import ModelOut, PricingOut
from app.services import model_service

router = APIRouter(prefix="/models", tags=["Models & pricing"])


@router.get("", response_model=list[ModelOut], summary="Active LLMs with current pricing")
def list_models(_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return model_service.list_models(db)


# Must be declared BEFORE /{model_id}, otherwise "pricing" is parsed as a model id.
@router.get("/pricing", response_model=list[PricingOut], summary="Current pricing for all active models")
def list_pricing(_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return model_service.list_pricing(db)


@router.get("/{model_id}", response_model=ModelOut)
def get_model(model_id: int, _user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return model_service.get_model(db, model_id)
