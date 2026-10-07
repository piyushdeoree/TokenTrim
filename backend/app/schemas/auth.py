from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt ignores bytes beyond 72
    full_name: str = Field(min_length=1, max_length=150)

    model_config = ConfigDict(json_schema_extra={
        "example": {"email": "dev@example.com", "password": "S3cure-pass!", "full_name": "Dev User"}})


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime
