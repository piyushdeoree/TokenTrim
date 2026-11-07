from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import NotFoundError
from app.models.api_key import ApiKey
from app.models.user import User
from app.repositories import api_key_repository


def create(db: Session, user: User, name: str) -> tuple[ApiKey, str]:
    full, prefix, key_hash = security.generate_api_key()
    key = ApiKey(user_id=user.id, name=name, prefix=prefix, key_hash=key_hash)
    db.add(key)
    db.commit()
    return key, full


def revoke(db: Session, user: User, key_id: int) -> None:
    key = api_key_repository.get_for_user(db, key_id, user.id)
    if key is None:
        raise NotFoundError("API key not found.")
    db.delete(key)
    db.commit()
