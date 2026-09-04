from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, SmallInteger, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.user import utc_now


if TYPE_CHECKING:
    from backend.app.models.deal import Deal


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("target_hourly_rate > 0", name="ck_categories_target_hourly_rate_positive"),
        CheckConstraint("target_effort > 0", name="ck_categories_target_effort_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_es: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    target_hourly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    target_effort: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    services: Mapped[list["Service"]] = relationship(back_populates="category")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_es: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    category: Mapped[Category] = relationship(back_populates="services")
    deals: Mapped[list["Deal"]] = relationship(back_populates="service")


class LeadScoringSettings(Base):
    __tablename__ = "lead_scoring_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_lead_scoring_settings_singleton"),
        CheckConstraint(
            "service_fit_weight + commercial_value_weight + lead_quality_weight + feasibility_weight = 100",
            name="ck_lead_scoring_settings_weights_total",
        ),
        CheckConstraint(
            "service_fit_weight >= 0 AND commercial_value_weight >= 0 AND lead_quality_weight >= 0 AND feasibility_weight >= 0",
            name="ck_lead_scoring_settings_weights_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1, server_default="1")
    service_fit_weight: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=30, server_default="30")
    commercial_value_weight: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=30, server_default="30")
    lead_quality_weight: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=15, server_default="15")
    feasibility_weight: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=25, server_default="25")
    commercial_value_scale: Mapped[list[dict[str, str | int]]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())
