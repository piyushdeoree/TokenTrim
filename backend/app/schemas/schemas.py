from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import get_settings


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth / users ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt ignores bytes past 72
    full_name: str = Field(min_length=1, max_length=120)
    model_config = ConfigDict(json_schema_extra={
        "example": {"email": "alice@example.com", "password": "S3curePassw0rd", "full_name": "Alice Doe"}})


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)
    model_config = ConfigDict(json_schema_extra={"example": {"email": "alice@example.com", "password": "S3curePassw0rd"}})


class UserOut(ORM):
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until expiry")


class MessageOut(BaseModel):
    message: str


# ---------- projects ----------
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    team_id: int | None = Field(default=None, description="Optional: create the project inside a team")
    model_config = ConfigDict(json_schema_extra={
        "example": {"name": "Support Chatbot", "description": "Prompts for the support bot", "team_id": None}})


class ProjectUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class ProjectOut(ORM):
    id: int
    name: str
    description: str | None
    owner_id: int
    team_id: int | None
    created_at: datetime
    updated_at: datetime


# ---------- api keys ----------
class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    model_config = ConfigDict(json_schema_extra={"example": {"name": "CI pipeline"}})


class ApiKeyOut(ORM):
    id: int
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None


class ApiKeyCreated(ApiKeyOut):
    secret: str = Field(description="Shown ONLY once, at creation time. Not recoverable afterwards.")


# ---------- teams ----------
Role = Literal["owner", "admin", "member"]


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class TeamOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    my_role: Role


class MemberAdd(BaseModel):
    email: EmailStr
    role: Literal["admin", "member"] = "member"
    model_config = ConfigDict(json_schema_extra={"example": {"email": "bob@example.com", "role": "member"}})


class MemberRoleUpdate(BaseModel):
    role: Literal["admin", "member"]


class MemberOut(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str
    role: Role
    joined_at: datetime


# ---------- models / pricing ----------
class PricingOut(BaseModel):
    input_price_per_1k: float
    output_price_per_1k: float
    currency: str
    effective_from: datetime


class ModelOut(BaseModel):
    id: int
    name: str
    provider: str
    context_window: int | None
    is_active: bool
    pricing: PricingOut | None


class PricingRow(PricingOut):
    model_config = ConfigDict(protected_namespaces=())
    model_id: int
    model_name: str
    provider: str


# ---------- analysis ----------
class AnalyzeRequest(BaseModel):
    prompt: str
    model: str = Field(min_length=1, max_length=100)
    project_id: int | None = Field(default=None, description="Optional: attribute usage to a project")
    model_config = ConfigDict(json_schema_extra={"example": {
        "prompt": "Please kindly summarize the following article in three bullet points.",
        "model": "gpt-4o-mini", "project_id": 1}})

    @field_validator("prompt")
    @classmethod
    def _prompt_ok(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Prompt must not be empty.")
        if len(v) > get_settings().max_prompt_chars:
            raise ValueError(f"Prompt exceeds the maximum length of {get_settings().max_prompt_chars} characters.")
        return v


class AnalyzeResponse(BaseModel):
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    reduction_percentage: float
    predicted_output_tokens: int
    estimated_cost: float
    potential_saving: float
    issues: list[str]
    suggestions: list[str]
    optimized_prompt: str
    model_config = ConfigDict(json_schema_extra={"example": {
        "original_tokens": 14, "optimized_tokens": 10, "tokens_saved": 4, "reduction_percentage": 28.57,
        "predicted_output_tokens": 150, "estimated_cost": 0.0000921, "potential_saving": 0.0000006,
        "issues": ["Filler words detected"], "suggestions": ["Remove 'please kindly'"],
        "optimized_prompt": "Summarize the following article in three bullet points."}})


# ---------- usage ----------
class UsageOut(BaseModel):
    id: int
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    potential_saving: float
    project_id: int | None
    user_id: int
    team_id: int | None


# ---------- dashboard ----------
class OverviewOut(BaseModel):
    total_tokens: int
    total_cost: float
    total_prompts: int
    total_savings: float
    average_reduction: float
    model_config = ConfigDict(json_schema_extra={"example": {
        "total_tokens": 12840, "total_cost": 0.42, "total_prompts": 37, "total_savings": 0.06,
        "average_reduction": 18.4}})


class PeriodUsage(BaseModel):
    period: str = Field(description="YYYY-MM-DD for daily, YYYY-MM for monthly")
    tokens: int
    cost: float
    prompts: int


class CostByModel(BaseModel):
    model: str
    tokens: int
    cost: float
    prompts: int


class CostByProject(BaseModel):
    project_id: int | None
    project_name: str
    tokens: int
    cost: float
    prompts: int


class RecentActivity(BaseModel):
    id: int
    timestamp: datetime
    model: str
    project_id: int | None
    project_name: str | None
    total_tokens: int
    estimated_cost: float
    potential_saving: float


class ProjectHistory(BaseModel):
    project_id: int
    project_name: str
    prompts: int
    tokens: int
    cost: float
    savings: float
    last_activity: datetime | None


class ForecastPoint(BaseModel):
    date: str
    estimated_cost: float


class ForecastOut(BaseModel):
    horizon_days: int
    total_forecast_cost: float
    daily: list[ForecastPoint]
