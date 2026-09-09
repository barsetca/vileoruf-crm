from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import CommunicationChannel, IntegrationProvider, User
from backend.app.services.inbox import InboxError, link_unmatched_external_message, list_unmatched_external_messages


router = APIRouter(prefix="/inbox", tags=["inbox"])


class InboxExternalMessageResponse(BaseModel):
    id: UUID
    provider: IntegrationProvider
    channel: CommunicationChannel
    sender_identifier: str
    content: str
    subject: str | None
    occurred_at: datetime


class InboxMessageLink(BaseModel):
    client_id: UUID


def _response(message) -> InboxExternalMessageResponse:
    channel = CommunicationChannel.TELEGRAM if message.provider is IntegrationProvider.TELEGRAM else CommunicationChannel.EMAIL if message.provider is IntegrationProvider.GMAIL else CommunicationChannel.OTHER
    return InboxExternalMessageResponse(
        id=message.id,
        provider=message.provider,
        channel=channel,
        sender_identifier=message.sender_identifier,
        content=message.content,
        subject=message.subject,
        occurred_at=message.provider_created_at or message.received_at or message.created_at,
    )


@router.get("/external-messages", response_model=list[InboxExternalMessageResponse])
def read_unmatched_external_messages(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return [_response(message) for message in list_unmatched_external_messages(session, limit=limit, offset=offset)]


@router.post("/external-messages/{external_message_id}/link", response_model=InboxExternalMessageResponse)
def link_unmatched_message(
    external_message_id: UUID,
    payload: InboxMessageLink,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return _response(link_unmatched_external_message(session, external_message_id=external_message_id, client_id=payload.client_id, current_user=current_user))
    except InboxError as error:
        raise HTTPException(status_code=422, detail="Inbox message cannot be linked") from error
