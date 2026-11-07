from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories import api_key_repository
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from app.services import api_key_service

router = APIRouter(prefix="/api-keys", tags=["API keys"])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED,
             summary="Create an API key (the secret is returned only once)")
def create_key(body: ApiKeyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    key, raw = api_key_service.create(db, user, body.name)
    return ApiKeyCreated(**ApiKeyOut.model_validate(key).model_dump(), key=raw)


@router.get("", response_model=list[ApiKeyOut], summary="List your keys (prefix only, never the secret)")
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return api_key_repository.list_for_user(db, user.id)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a key")
def delete_key(key_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    api_key_service.revoke(db, user, key_id)
