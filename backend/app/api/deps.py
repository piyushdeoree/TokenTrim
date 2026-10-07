from fastapi import Depends
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.database.session import get_db
from app.models.user import User
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False, description="JWT from POST /auth/login")
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False, description="API key from POST /api-keys")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Depends(api_key_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Accepts either `Authorization: Bearer <jwt>` or `X-API-Key: <key>`."""
    if creds is not None:
        return auth_service.authenticate_token(db, creds.credentials)
    if api_key:
        return auth_service.authenticate_api_key(db, api_key)
    raise UnauthorizedError("Authentication required.")


def get_bearer_token(creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    if creds is None:
        raise UnauthorizedError("Authentication required.")
    return creds.credentials
