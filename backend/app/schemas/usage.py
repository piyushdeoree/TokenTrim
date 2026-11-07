from datetime import datetime

from pydantic import BaseModel


class UsageOut(BaseModel):
    id: int
    timestamp: datetime
    model: str
    project_id: int | None
    user_id: int
    team_id: int | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float


class UsagePage(BaseModel):
    items: list[UsageOut]
    total: int
    limit: int
    offset: int
