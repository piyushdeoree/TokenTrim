from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import RevokedToken, User


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create(db: Session, email: str, full_name: str, hashed_password: str) -> User:
    user = User(email=email.lower(), full_name=full_name, hashed_password=hashed_password)
    db.add(user)
    db.flush()
    return user


def is_token_revoked(db: Session, jti: str) -> bool:
    return db.get(RevokedToken, jti) is not None


def revoke_token(db: Session, jti: str, expires_at) -> None:
    if db.get(RevokedToken, jti) is None:
        db.add(RevokedToken(jti=jti, expires_at=expires_at))
