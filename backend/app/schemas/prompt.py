from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings


class AnalyzeRequest(BaseModel):
    prompt: str
    model: str = Field(min_length=1, max_length=100)
    project_id: int | None = Field(default=None, description="Optional: attribute this analysis to a project")

    @field_validator("prompt")
    @classmethod
    def prompt_valid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt must not be empty")
        if len(v) > settings.MAX_PROMPT_CHARS:
            raise ValueError(f"prompt must be at most {settings.MAX_PROMPT_CHARS} characters")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {"prompt": "Please could you kindly summarise the following text ...", "model": "gpt-4o-mini", "project_id": 1}})


class AnalyzeResponse(BaseModel):
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    reduction_percentage: float
    predicted_output_tokens: int
    estimated_cost: float
    potential_saving: float
    issues: list
    suggestions: list
    optimized_prompt: str

    model_config = ConfigDict(json_schema_extra={"example": {
        "original_tokens": 120, "optimized_tokens": 85, "tokens_saved": 35, "reduction_percentage": 29.17,
        "predicted_output_tokens": 150, "estimated_cost": 0.00009, "potential_saving": 0.00002,
        "issues": ["Redundant politeness phrases"], "suggestions": ["Remove filler words"],
        "optimized_prompt": "Summarise the following text ..."}})
