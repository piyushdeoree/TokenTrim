import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import ConflictError, UnauthorizedError
from app.models.user import User
from app.repositories import api_key_repository, user_repository
from datetime import datetime, timezone


def register(db: Session, email: str, password: str, full_name: str) -> User:
    if user_repository.get_by_email(db, email):
        raise ConflictError("An account with this email already exists.")
    try:
        user = user_repository.create(db, email, full_name, security.hash_password(password))
        db.commit()
    except IntegrityError:  # race with a concurrent registration
        db.rollback()
        raise ConflictError("An account with this email already exists.")
    return user


def login(db: Session, email: str, password: str):
    user = user_repository.get_by_email(db, email)
    # Same message for unknown email and wrong password: don't leak which accounts exist.
    if not user or not user.is_active or not security.verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password.")
    return security.create_access_token(user.id)


def authenticate_token(db: Session, token: str) -> User:
    try:
        payload = security.decode_access_token(token)
        user_id, jti = int(payload["sub"]), payload["jti"]
    except (jwt.PyJWTError, KeyError, ValueError):
        raise UnauthorizedError("Invalid or expired token.")
    if user_repository.is_token_revoked(db, jti):
        raise UnauthorizedError("Token has been revoked.")
    user = user_repository.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")
    return user


def authenticate_api_key(db: Session, raw_key: str) -> User:
    key = api_key_repository.get_by_hash(db, security.hash_api_key(raw_key))
    if not key:
        raise UnauthorizedError("Invalid API key.")
    user = user_repository.get_by_id(db, key.user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")
    key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return user


def logout(db: Session, token: str) -> None:
    """JWTs are stateless, so logout = add the token's jti to a blocklist until it expires."""
    try:
        payload = security.decode_access_token(token)
    except jwt.PyJWTError:
        return
    user_repository.revoke_token(db, payload["jti"], datetime.fromtimestamp(payload["exp"], tz=timezone.utc))
    db.commit()
