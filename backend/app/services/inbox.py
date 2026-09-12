"""Bounded, provider-neutral operational queue for unmatched inbound messages."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import (
    Client,
    Communication,
    CommunicationChannel,
    CommunicationDirection,
    CommunicationStatus,
    ExternalMessage,
    IntegrationProvider,
    UserRole,
)
from backend.app.models.user import utc_now
from backend.app.services.telegram import TelegramError, link_telegram_message


class InboxError(ValueError):
    pass


def _unmatched_conditions(provider: IntegrationProvider | None = None):
    conditions = [
        ExternalMessage.direction == "INCOMING",
        ExternalMessage.client_id.is_(None),
        ExternalMessage.communication_id.is_(None),
    ]
    if provider is not None:
        conditions.append(ExternalMessage.provider == provider)
    return conditions


def list_unmatched_external_messages(session: Session, *, limit: int, offset: int, provider: IntegrationProvider | None = None) -> list[ExternalMessage]:
    """Return only actionable inbound facts, newest first, without provider payloads."""
    statement = (
        select(ExternalMessage)
        .where(*_unmatched_conditions(provider))
        .order_by(
            ExternalMessage.provider_created_at.desc().nullslast(),
            ExternalMessage.received_at.desc().nullslast(),
            ExternalMessage.created_at.desc(),
            ExternalMessage.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement))


def unmatched_counts(session: Session) -> dict[IntegrationProvider, int]:
    rows = session.execute(
        select(ExternalMessage.provider, func.count())
        .where(*_unmatched_conditions())
        .group_by(ExternalMessage.provider)
    ).all()
    return {provider: count for provider, count in rows}


def delete_unmatched_external_messages(session: Session, *, external_message_ids: list[UUID], current_user: object) -> int:
    if getattr(current_user, "role", None) is not UserRole.ADMIN:
        raise InboxError
    if not external_message_ids:
        return 0
    messages = list(session.scalars(select(ExternalMessage).where(ExternalMessage.id.in_(external_message_ids)).with_for_update()))
    if len(messages) != len(set(external_message_ids)) or any(
        message.direction != "INCOMING" or message.client_id is not None or message.communication_id is not None
        for message in messages
    ):
        session.rollback()
        raise InboxError
    try:
        for message in messages:
            session.delete(message)
        session.commit()
        return len(messages)
    except Exception:
        session.rollback()
        raise InboxError


def link_unmatched_external_message(
    session: Session, *, external_message_id: UUID, client_id: UUID | None = None, deal_id: UUID | None = None, current_user: object
) -> ExternalMessage:
    """Attach one unmatched inbound fact to an existing Client exactly once."""
    message = session.get(ExternalMessage, external_message_id)
    if not message or message.direction != "INCOMING" or (not deal_id and (not client_id or not session.get(Client, client_id))):
        raise InboxError
    if message.provider is IntegrationProvider.TELEGRAM:
        try:
            return link_telegram_message(
                session,
                external_message_id=external_message_id,
                client_id=client_id,
                deal_id=deal_id,
                current_user=current_user,
            )
        except TelegramError as error:
            raise InboxError from error
    if message.communication_id:
        return message

    channel = CommunicationChannel.EMAIL if message.provider is IntegrationProvider.GMAIL else CommunicationChannel.OTHER
    message.client_id = client_id
    communication = Communication(
        client_id=client_id,
        deal_id=None,
        channel=channel,
        direction=CommunicationDirection.INCOMING,
        content=message.content,
        occurred_at=message.provider_created_at or message.received_at or utc_now(),
        status=CommunicationStatus.RECORDED,
        read_at=None,
    )
    session.add(communication)
    session.flush()
    message.communication_id = communication.id
    session.commit()
    session.refresh(message)
    return message
