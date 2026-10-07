from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey


def list_for_user(db: Session, user_id: int) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.id)))


def get_for_user(db: Session, key_id: int, user_id: int) -> ApiKey | None:
    return db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id))


def get_by_hash(db: Session, key_hash: str) -> ApiKey | None:
    return db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True)))
