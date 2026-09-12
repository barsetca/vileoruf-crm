from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


if TYPE_CHECKING:
    from backend.app.models.client import Client
    from backend.app.models.deal import Deal


class CommunicationChannel(str, Enum):
    EMAIL = "EMAIL"
    TELEGRAM = "TELEGRAM"
    WHATSAPP = "WHATSAPP"
    MANUAL = "MANUAL"
    OTHER = "OTHER"


class CommunicationDirection(str, Enum):
    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"


class CommunicationStatus(str, Enum):
    RECORDED = "RECORDED"


class Communication(Base):
    __tablename__ = "communications"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id"), nullable=False, index=True
    )
    deal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("deals.id"), nullable=True, index=True
    )
    channel: Mapped[CommunicationChannel] = mapped_column(
        SqlEnum(CommunicationChannel, name="communication_channel"), nullable=False
    )
    direction: Mapped[CommunicationDirection] = mapped_column(
        SqlEnum(CommunicationDirection, name="communication_direction"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[CommunicationStatus] = mapped_column(
        SqlEnum(CommunicationStatus, name="communication_status"), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    client: Mapped["Client"] = relationship(back_populates="communications")
    deal: Mapped["Deal | None"] = relationship(back_populates="communications")
