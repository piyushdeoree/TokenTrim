from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["owner", "admin", "member"]


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class TeamOut(BaseModel):
    id: int
    name: str
    owner_id: int
    my_role: Role
    created_at: datetime


class MemberInvite(BaseModel):
    email: EmailStr
    role: Literal["admin", "member"] = "member"


class MemberRoleUpdate(BaseModel):
    role: Literal["admin", "member"]


class MemberOut(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str
    role: Role
    joined_at: datetime
