from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    team_id: int | None = None

    model_config = ConfigDict(json_schema_extra={
        "example": {"name": "Support Chatbot", "description": "Cost tracking for the support bot", "team_id": None}})


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    owner_id: int
    team_id: int | None
    created_at: datetime
    updated_at: datetime
