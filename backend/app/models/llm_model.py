from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class LLMModel(Base):
    """The `models` table. Named LLMModel to avoid clashing with the app.models package."""
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pricing: Mapped[list["ModelPricing"]] = relationship(
        back_populates="model", cascade="all, delete-orphan", order_by="ModelPricing.effective_from.desc()"
    )


class ModelPricing(Base):
    __tablename__ = "model_pricing"
    __table_args__ = (
        CheckConstraint("input_price_per_1k >= 0 AND output_price_per_1k >= 0", name="ck_pricing_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), index=True)
    input_price_per_1k: Mapped[Decimal] = mapped_column(Numeric(14, 8))
    output_price_per_1k: Mapped[Decimal] = mapped_column(Numeric(14, 8))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    model: Mapped[LLMModel] = relationship(back_populates="pricing")
