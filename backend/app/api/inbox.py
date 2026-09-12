from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import CommunicationChannel, IntegrationProvider, User
from backend.app.services.inbox import InboxError, delete_unmatched_external_messages, link_unmatched_external_message, list_unmatched_external_messages, unmatched_counts


router = APIRouter(prefix="/inbox", tags=["inbox"])


class InboxExternalMessageResponse(BaseModel):
    id: UUID
    provider: IntegrationProvider
    channel: CommunicationChannel
    sender_identifier: str
    content: str
    subject: str | None
    sender_username: str | None
    sender_first_name: str | None
    sender_last_name: str | None
    occurred_at: datetime


class InboxMessageLink(BaseModel):
    client_id: UUID | None = None
    deal_id: UUID | None = None


class InboxDeleteRequest(BaseModel):
    external_message_ids: list[UUID]


class InboxSummaryResponse(BaseModel):
    email: int
    telegram: int


def _response(message) -> InboxExternalMessageResponse:
    channel = CommunicationChannel.TELEGRAM if message.provider is IntegrationProvider.TELEGRAM else CommunicationChannel.EMAIL if message.provider is IntegrationProvider.GMAIL else CommunicationChannel.OTHER
    return InboxExternalMessageResponse(
        id=message.id,
        provider=message.provider,
        channel=channel,
        sender_identifier=message.sender_identifier,
        content=message.content,
        subject=message.subject,
        sender_username=message.sender_username,
        sender_first_name=message.sender_first_name,
        sender_last_name=message.sender_last_name,
        occurred_at=message.provider_created_at or message.received_at or message.created_at,
    )


@router.get("/external-messages", response_model=list[InboxExternalMessageResponse])
def read_unmatched_external_messages(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    channel: CommunicationChannel | None = None,
):
    provider = IntegrationProvider.GMAIL if channel is CommunicationChannel.EMAIL else IntegrationProvider.TELEGRAM if channel is CommunicationChannel.TELEGRAM else None
    if channel is not None and provider is None:
        return []
    return [_response(message) for message in list_unmatched_external_messages(session, limit=limit, offset=offset, provider=provider)]


@router.get("/summary", response_model=InboxSummaryResponse)
def read_unmatched_summary(session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    counts = unmatched_counts(session)
    return InboxSummaryResponse(email=counts.get(IntegrationProvider.GMAIL, 0), telegram=counts.get(IntegrationProvider.TELEGRAM, 0))


@router.post("/external-messages/{external_message_id}/link", response_model=InboxExternalMessageResponse)
def link_unmatched_message(
    external_message_id: UUID,
    payload: InboxMessageLink,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return _response(link_unmatched_external_message(session, external_message_id=external_message_id, client_id=payload.client_id, deal_id=payload.deal_id, current_user=current_user))
    except InboxError as error:
        raise HTTPException(status_code=422, detail="Inbox message cannot be linked") from error


@router.post("/external-messages/bulk-delete", status_code=204)
def bulk_delete_unmatched_messages(payload: InboxDeleteRequest, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try:
        delete_unmatched_external_messages(session, external_message_ids=payload.external_message_ids, current_user=current_user)
    except InboxError as error:
        if current_user.role.value != "ADMIN":
            raise HTTPException(status_code=403, detail="Administrator access required") from error
        raise HTTPException(status_code=409, detail="Selected messages are no longer unmatched") from error
