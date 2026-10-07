from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ts(**kw):
    return mapped_column(DateTime(timezone=True), default=utcnow, **kw)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _ts()


class RevokedToken(Base):
    """JWT logout strategy: blocklist of revoked token ids (jti) until they expire."""
    __tablename__ = "revoked_tokens"
    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = _ts()


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_member"),
        CheckConstraint("role IN ('owner','admin','member')", name="ck_team_member_role"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10), default="member")
    joined_at: Mapped[datetime] = _ts()


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_project_owner_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    prefix: Mapped[str] = mapped_column(String(16))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = _ts()
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AIModel(Base):
    __tablename__ = "models"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(60))
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ModelPricing(Base):
    __tablename__ = "model_pricing"
    __table_args__ = (
        UniqueConstraint("model_id", "effective_from", name="uq_pricing_model_effective"),
        CheckConstraint("input_price_per_1k >= 0 AND output_price_per_1k >= 0", name="ck_pricing_nonneg"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), index=True)
    input_price_per_1k: Mapped[float] = mapped_column(Float)
    output_price_per_1k: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True,
                                                   index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()


class PromptAnalysis(Base):
    __tablename__ = "prompt_analysis"
    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id", ondelete="CASCADE"), unique=True)
    original_tokens: Mapped[int] = mapped_column(Integer)
    optimized_tokens: Mapped[int] = mapped_column(Integer)
    tokens_saved: Mapped[int] = mapped_column(Integer)
    reduction_percentage: Mapped[float] = mapped_column(Float)
    predicted_output_tokens: Mapped[int] = mapped_column(Integer)
    optimized_prompt: Mapped[str] = mapped_column(Text)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = _ts()


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        Index("ix_usage_user_created", "user_id", "created_at"),
        Index("ix_usage_project_created", "project_id", "created_at"),
        CheckConstraint("input_tokens >= 0 AND output_tokens >= 0 AND total_tokens >= 0", name="ck_usage_nonneg"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    prompt_id: Mapped[int | None] = mapped_column(ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    total_tokens: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = _ts()


class CostRecord(Base):
    __tablename__ = "cost_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    usage_id: Mapped[int] = mapped_column(ForeignKey("usage_records.id", ondelete="CASCADE"), unique=True)
    estimated_cost: Mapped[float] = mapped_column(Float)
    potential_saving: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = _ts()
