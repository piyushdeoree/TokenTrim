from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    original_text: Mapped[str] = mapped_column(Text)
    optimized_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    analysis: Mapped["PromptAnalysis"] = relationship(back_populates="prompt", uselist=False, cascade="all, delete-orphan")


class PromptAnalysis(Base):
    __tablename__ = "prompt_analysis"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id", ondelete="CASCADE"), unique=True)
    original_tokens: Mapped[int] = mapped_column(Integer)
    optimized_tokens: Mapped[int] = mapped_column(Integer)
    tokens_saved: Mapped[int] = mapped_column(Integer)
    reduction_percentage: Mapped[float] = mapped_column(Float)
    predicted_output_tokens: Mapped[int] = mapped_column(Integer)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    prompt: Mapped[Prompt] = relationship(back_populates="analysis")
