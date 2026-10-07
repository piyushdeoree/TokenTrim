from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session_user
from app.core.errors import AppError, not_found
from app.core.security import generate_api_key
from app.database.session import get_db
from app.models import ApiKey, User
from app.schemas.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter(prefix="/api-keys", tags=["API Keys"])
MAX_KEYS_PER_USER = 20


@router.post("", response_model=ApiKeyCreated, status_code=201,
             summary="Create an API key (the secret is returned only once)")
def create_key(body: ApiKeyCreate, user: User = Depends(get_session_user), db: Session = Depends(get_db)):
    count = len(db.scalars(select(ApiKey.id).where(ApiKey.user_id == user.id)).all())
    if count >= MAX_KEYS_PER_USER:
        raise AppError(409, "API_KEY_LIMIT", f"You can have at most {MAX_KEYS_PER_USER} API keys.")
    raw, prefix, key_hash = generate_api_key()
    key = ApiKey(user_id=user.id, name=body.name.strip(), prefix=prefix, key_hash=key_hash)
    db.add(key)
    db.commit()
    return ApiKeyCreated(id=key.id, name=key.name, prefix=key.prefix, created_at=key.created_at,
                         last_used_at=None, secret=raw)


@router.get("", response_model=list[ApiKeyOut], summary="List your API keys (no secrets)")
def list_keys(user: User = Depends(get_session_user), db: Session = Depends(get_db)):
    return db.scalars(select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.id)).all()


@router.delete("/{key_id}", status_code=204, summary="Revoke/delete an API key")
def delete_key(key_id: int, user: User = Depends(get_session_user), db: Session = Depends(get_db)):
    key = db.get(ApiKey, key_id)
    if key is None or key.user_id != user.id:
        raise not_found("api key")
    db.delete(key)
    db.commit()
    return Response(status_code=204)
