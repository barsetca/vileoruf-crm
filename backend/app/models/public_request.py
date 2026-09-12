from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.client import PreferredCommunicationLanguage
from backend.app.models.user import utc_now


if TYPE_CHECKING:
    from backend.app.models.business import Service
    from backend.app.models.client import Client
    from backend.app.models.deal import Deal


class PublicRequest(Base):
    """Immutable historical snapshot of one accepted public form submission."""

    __tablename__ = "public_requests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    deal_id: Mapped[UUID] = mapped_column(ForeignKey("deals.id"), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telegram: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_communication_language: Mapped[PreferredCommunicationLanguage] = mapped_column(
        SqlEnum(PreferredCommunicationLanguage, name="preferred_communication_language"),
        nullable=False,
    )
    deal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id"), nullable=False, index=True)
    service_name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    service_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    service_name_es: Mapped[str] = mapped_column(String(255), nullable=False)
    estimated_budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    personal_data_consent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    personal_data_consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    personal_data_consent_version: Mapped[str] = mapped_column(String(32), nullable=False)
    privacy_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    client: Mapped["Client"] = relationship(back_populates="public_requests")
    deal: Mapped["Deal"] = relationship(back_populates="public_request")
    service: Mapped["Service"] = relationship(back_populates="public_requests")
