from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import bearer, get_current_user, get_session_user
from app.core.errors import AppError, unauthorized
from app.core.rate_limit import auth_limit
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.database.session import get_db
from app.models import RevokedToken, User
from app.repositories.crud import get_user_by_email
from app.schemas.schemas import LoginRequest, MessageOut, TokenOut, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])
_DUMMY_HASH = None


@router.post("/register", response_model=UserOut, status_code=201, dependencies=[Depends(auth_limit)],
             summary="Register a new account", responses={409: {"description": "Email already registered"}})
def register(body: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, body.email):
        raise AppError(409, "EMAIL_TAKEN", "An account with this email already exists.")
    user = User(email=body.email.lower(), full_name=body.full_name.strip(), hashed_password=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "EMAIL_TAKEN", "An account with this email already exists.")
    return user


@router.post("/login", response_model=TokenOut, dependencies=[Depends(auth_limit)], summary="Log in, get a JWT",
             responses={401: {"description": "Invalid credentials"}})
def login(body: LoginRequest, db: Session = Depends(get_db)):
    global _DUMMY_HASH
    user = get_user_by_email(db, body.email)
    if user is None:  # equalise timing so unknown emails aren't distinguishable
        _DUMMY_HASH = _DUMMY_HASH or hash_password("dummy-password")
        verify_password(body.password, _DUMMY_HASH)
    if user is None or not user.is_active or not verify_password(body.password, user.hashed_password):
        raise unauthorized("INVALID_CREDENTIALS", "Incorrect email or password.")
    token, expires_in = create_access_token(user.id)
    return TokenOut(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserOut, summary="Current user")
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", response_model=MessageOut,
             summary="Log out (revokes the current JWT via a server-side blocklist)")
def logout(creds=Depends(bearer), user: User = Depends(get_session_user), db: Session = Depends(get_db)):
    payload = decode_token(creds.credentials)
    now = datetime.now(timezone.utc)
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))  # housekeeping
    db.add(RevokedToken(jti=payload["jti"], expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)))
    db.commit()
    return MessageOut(message="Logged out.")
