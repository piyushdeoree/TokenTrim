from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "AI Cost Intelligence Platform API"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_cost"
    SECRET_KEY: str  # required: no default so a missing secret fails fast
    OPENAI_API_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    RATE_LIMIT_PER_MINUTE: int = 30
    MAX_PROMPT_CHARS: int = 50000
    USE_STUB_ENGINES: bool = False
    SEED_ON_STARTUP: bool = True


settings = Settings()
