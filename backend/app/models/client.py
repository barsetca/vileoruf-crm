from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.user import utc_now


if TYPE_CHECKING:
    from backend.app.models.communication import Communication
    from backend.app.models.deal import Deal
    from backend.app.models.task import Task


class ClientStatus(str, Enum):
    CUSTOMER = "CUSTOMER"
    CLIENT = "CLIENT"


class PreferredCommunicationLanguage(str, Enum):
    RU = "RU"
    EN = "EN"
    ES = "ES"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telegram: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ClientStatus] = mapped_column(
        SqlEnum(ClientStatus, name="client_status"),
        nullable=False,
        default=ClientStatus.CUSTOMER,
        server_default=ClientStatus.CUSTOMER.value,
    )
    preferred_communication_language: Mapped[PreferredCommunicationLanguage] = mapped_column(
        SqlEnum(PreferredCommunicationLanguage, name="preferred_communication_language"),
        nullable=False,
        default=PreferredCommunicationLanguage.RU,
        server_default=PreferredCommunicationLanguage.RU.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
    deals: Mapped[list["Deal"]] = relationship(back_populates="client")
    communications: Mapped[list["Communication"]] = relationship(back_populates="client")
    tasks: Mapped[list["Task"]] = relationship(back_populates="client")
