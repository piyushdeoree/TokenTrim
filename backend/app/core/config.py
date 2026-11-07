
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore"
    )

    PROJECT_NAME: str = "TokenTrim API"

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/tokentrim"

    SECRET_KEY: str
    OPENAI_API_KEY: str = ""

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000"
    ]

    RATE_LIMIT_PER_MINUTE: int = 30
    MAX_PROMPT_CHARS: int = 50000

    USE_STUB_ENGINES: bool = False
    SEED_ON_STARTUP: bool = True


settings = Settings()
