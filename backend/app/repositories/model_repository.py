from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.llm_model import LLMModel


def list_active(db: Session) -> list[LLMModel]:
    return list(db.scalars(
        select(LLMModel).options(selectinload(LLMModel.pricing)).where(LLMModel.is_active.is_(True)).order_by(LLMModel.id)
    ))


def get(db: Session, model_id: int) -> LLMModel | None:
    return db.scalar(select(LLMModel).options(selectinload(LLMModel.pricing)).where(LLMModel.id == model_id))


def get_by_name(db: Session, name: str) -> LLMModel | None:
    return db.scalar(
        select(LLMModel).options(selectinload(LLMModel.pricing))
        .where(LLMModel.name == name, LLMModel.is_active.is_(True))
    )
