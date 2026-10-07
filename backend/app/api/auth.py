from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_bearer_token, get_current_user
from app.core.rate_limit import check_rate_limit
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Create an account")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    return auth_service.register(db, body.email, body.password, body.full_name)


@router.post("/login", response_model=TokenResponse, summary="Log in and receive a JWT access token")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    check_rate_limit(f"login:{body.email.lower()}", limit=10)  # slows password guessing
    token, _jti, expires = auth_service.login(db, body.email, body.password)
    return TokenResponse(access_token=token, expires_at=expires)


@router.get("/me", response_model=UserOut, summary="Current user")
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke the current JWT")
def logout(token: str = Depends(get_bearer_token), _user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    auth_service.logout(db, token)
