from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (CheckConstraint("input_tokens >= 0 AND output_tokens >= 0", name="ck_usage_tokens"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    prompt_id: Mapped[int | None] = mapped_column(ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    total_tokens: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    model = relationship("LLMModel")
    project = relationship("Project")
    cost = relationship("CostRecord", uselist=False, back_populates="usage", cascade="all, delete-orphan")


class CostRecord(Base):
    __tablename__ = "cost_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    usage_record_id: Mapped[int] = mapped_column(ForeignKey("usage_records.id", ondelete="CASCADE"), unique=True)
    pricing_id: Mapped[int | None] = mapped_column(ForeignKey("model_pricing.id", ondelete="SET NULL"), nullable=True)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(14, 8))      # cost of the ORIGINAL prompt
    optimized_cost: Mapped[Decimal] = mapped_column(Numeric(14, 8))      # cost if the optimized prompt is used
    potential_saving: Mapped[Decimal] = mapped_column(Numeric(14, 8))    # estimated - optimized
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usage: Mapped[UsageRecord] = relationship(back_populates="cost")
