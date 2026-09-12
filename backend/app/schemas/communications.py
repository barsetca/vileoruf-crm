from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from backend.app.models import (
    CommunicationChannel,
    CommunicationDirection,
    CommunicationStatus,
)


CommunicationContent = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CommunicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    deal_id: UUID | None
    channel: CommunicationChannel
    direction: CommunicationDirection
    content: str
    occurred_at: datetime
    status: CommunicationStatus
    read_at: datetime | None


class UnreadCommunicationClient(BaseModel):
    client_id: UUID
    client_name: str
    channels: list[CommunicationChannel]
    unread_count: int
    deal_id: UUID | None = None
    deal_name: str | None = None


class IncomingCommunicationSummary(BaseModel):
    unread_count: int
    clients: list[UnreadCommunicationClient]


class CommunicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: UUID
    deal_id: UUID | None = None
    channel: CommunicationChannel
    direction: CommunicationDirection
    content: CommunicationContent
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Communication timestamp must include a timezone")
        return value
