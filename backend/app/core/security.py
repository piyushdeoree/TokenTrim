import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at). The jti lets us revoke on logout."""
    jti = uuid.uuid4().hex
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "jti": jti, "exp": expires, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM), jti, expires


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError if invalid or expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


API_KEY_PREFIX = "acp_"


def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, display_prefix, sha256_hash). Only the hash is stored."""
    full = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return full, full[:10], hash_api_key(full)


def hash_api_key(key: str) -> str:
    # API keys are high-entropy random strings, so a fast hash is appropriate (unlike passwords).
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
