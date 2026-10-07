from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Overview(BaseModel):
    total_tokens: int
    total_cost: float
    total_prompts: int
    total_savings: float
    average_reduction: float

    model_config = ConfigDict(json_schema_extra={"example": {
        "total_tokens": 15400, "total_cost": 0.42, "total_prompts": 37, "total_savings": 0.07, "average_reduction": 18.5}})


class DailyUsage(BaseModel):
    date: str  # YYYY-MM-DD
    tokens: int
    cost: float
    requests: int


class MonthlyUsage(BaseModel):
    month: str  # YYYY-MM
    tokens: int
    cost: float
    requests: int


class CostByModel(BaseModel):
    model: str
    tokens: int
    cost: float
    requests: int


class CostByProject(BaseModel):
    project_id: int | None
    project: str
    tokens: int
    cost: float
    requests: int


class RecentActivity(BaseModel):
    usage_id: int
    timestamp: datetime
    model: str
    project_id: int | None
    project: str | None
    total_tokens: int
    estimated_cost: float
    potential_saving: float


class ProjectHistory(BaseModel):
    project_id: int
    project: str
    requests: int
    tokens: int
    cost: float
    savings: float
    last_activity: datetime | None


class Forecast(BaseModel):
    horizon_days: int
    daily_forecast: list[float]
    total_forecast: float
