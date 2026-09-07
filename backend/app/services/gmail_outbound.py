"""D5.2b explicit Gmail outbound lifecycle; provider calls stay behind the adapter."""

from datetime import datetime
from email.utils import parseaddr
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import (
    Communication,
    CommunicationChannel,
    CommunicationDirection,
    CommunicationStatus,
    Deal,
    EmailDraft,
    EmailDraftState,
    ExternalMessage,
    ExternalMessageStatus,
    IntegrationConnection,
    IntegrationConnectionStatus,
    IntegrationProvider,
    User,
    UserRole,
)
from backend.app.models.user import utc_now
from backend.app.services.google_oauth import GoogleOAuthError, get_google_access_token
from backend.app.services.integrations_adapters import GmailAdapterError, ProviderErrorCode, RetryClass, send_gmail_message


class GmailOutboundError(ValueError):
    pass


class GmailOutboundNotFoundError(GmailOutboundError):
    pass


class GmailOutboundForbiddenError(GmailOutboundError):
    pass


class GmailOutboundValidationError(GmailOutboundError):
    def __init__(self, code: ProviderErrorCode):
        self.code = code
        super().__init__(code.value)


class GmailOutboundPersistenceError(RuntimeError):
    pass


def request_gmail_send(session: Session, *, deal_id: UUID, draft_id: UUID, current_user: User) -> ExternalMessage:
    draft, deal = _authorized_draft(session, deal_id=deal_id, draft_id=draft_id, current_user=current_user)
    existing = session.scalar(select(ExternalMessage).where(ExternalMessage.email_draft_id == draft.id))
    if existing is not None:
        return existing
    if draft.state is EmailDraftState.SENT:
        raise GmailOutboundValidationError(ProviderErrorCode.PROVIDER_ERROR)
    recipient = _recipient(deal.client.email)
    connection = session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider == IntegrationProvider.GMAIL))
    if connection is None or connection.status is not IntegrationConnectionStatus.CONNECTED or not connection.encrypted_token_payload:
        raise GmailOutboundValidationError(ProviderErrorCode.AUTH_REQUIRED)
    message = ExternalMessage(
        integration_connection_id=connection.id,
        provider=IntegrationProvider.GMAIL,
        email_draft_id=draft.id,
        client_id=deal.client_id,
        deal_id=deal.id,
        direction="OUTGOING",
        status=ExternalMessageStatus.PENDING,
        sender_identifier=connection.external_account_email or "corporate-gmail",
        recipient_identifier=recipient,
        subject=draft.subject,
        content=draft.body,
    )
    session.add(message)
    try:
        session.commit()
        session.refresh(message)
        return message
    except IntegrityError:
        session.rollback()
        existing = session.scalar(select(ExternalMessage).where(ExternalMessage.email_draft_id == draft.id))
        if existing is not None:
            return existing
        raise GmailOutboundPersistenceError from None
    except SQLAlchemyError as error:
        session.rollback()
        raise GmailOutboundPersistenceError from error


def execute_gmail_send(session: Session, *, external_message_id: UUID) -> ExternalMessage:
    message = session.get(ExternalMessage, external_message_id)
    if message is None:
        raise GmailOutboundNotFoundError
    if message.status is not ExternalMessageStatus.PENDING:
        return message
    connection = session.get(IntegrationConnection, message.integration_connection_id)
    if connection is None or connection.status is not IntegrationConnectionStatus.CONNECTED:
        return _finish_failure(session, message, ProviderErrorCode.AUTH_REQUIRED, ExternalMessageStatus.FAILED)
    try:
        access_token = get_google_access_token(session, connection=connection)
        result = send_gmail_message(access_token=access_token, recipient=message.recipient_identifier, subject=message.subject or "", body=message.content)
    except GoogleOAuthError as error:
        return _finish_failure(session, message, error.code, ExternalMessageStatus.FAILED)
    except GmailAdapterError as error:
        outcome = ExternalMessageStatus.UNKNOWN if error.retry_class is RetryClass.UNCERTAIN else ExternalMessageStatus.FAILED
        return _finish_failure(session, message, error.code, outcome)
    return _finalize_success(session, message, result.provider_message_id, result.provider_thread_id)


def mark_dispatch_failure(session: Session, *, external_message_id: UUID) -> ExternalMessage:
    message = session.get(ExternalMessage, external_message_id)
    if message is None:
        raise GmailOutboundNotFoundError
    if message.status is ExternalMessageStatus.PENDING:
        return _finish_failure(session, message, ProviderErrorCode.PROVIDER_UNAVAILABLE, ExternalMessageStatus.FAILED)
    return message


def _authorized_draft(session: Session, *, deal_id: UUID, draft_id: UUID, current_user: User) -> tuple[EmailDraft, Deal]:
    deal = session.get(Deal, deal_id)
    if deal is None:
        raise GmailOutboundNotFoundError
    if current_user.role is UserRole.MANAGER and deal.responsible_user_id != current_user.id:
        raise GmailOutboundForbiddenError
    draft = session.scalar(select(EmailDraft).where(EmailDraft.id == draft_id, EmailDraft.deal_id == deal_id))
    if draft is None:
        raise GmailOutboundNotFoundError
    return draft, deal


def _recipient(value: str | None) -> str:
    if not value:
        raise GmailOutboundValidationError(ProviderErrorCode.INVALID_RECIPIENT)
    display, address = parseaddr(value.strip())
    if display or address != value.strip() or address.count("@") != 1 or address.startswith("@") or address.endswith("@"):
        raise GmailOutboundValidationError(ProviderErrorCode.INVALID_RECIPIENT)
    local, domain = address.rsplit("@", 1)
    if not local or "." not in domain or any(char.isspace() for char in address):
        raise GmailOutboundValidationError(ProviderErrorCode.INVALID_RECIPIENT)
    return address.lower()


def _finish_failure(session: Session, message: ExternalMessage, code: ProviderErrorCode, status: ExternalMessageStatus) -> ExternalMessage:
    message.status = status
    message.last_error_code = code.value
    try:
        session.commit()
        session.refresh(message)
        return message
    except SQLAlchemyError as error:
        session.rollback()
        raise GmailOutboundPersistenceError from error


def _finalize_success(session: Session, message: ExternalMessage, provider_message_id: str, provider_thread_id: str | None) -> ExternalMessage:
    if message.status is ExternalMessageStatus.SENT:
        return message
    draft = session.get(EmailDraft, message.email_draft_id)
    if draft is None:
        return _finish_failure(session, message, ProviderErrorCode.PROVIDER_ERROR, ExternalMessageStatus.UNKNOWN)
    communication = Communication(
        client_id=message.client_id,
        deal_id=message.deal_id,
        channel=CommunicationChannel.EMAIL,
        direction=CommunicationDirection.OUTGOING,
        content=_communication_content(message.subject or "", message.content),
        occurred_at=utc_now(),
        status=CommunicationStatus.RECORDED,
    )
    message.provider_message_id = provider_message_id
    message.provider_thread_id = provider_thread_id
    message.provider_created_at = utc_now()
    message.sent_at = utc_now()
    message.status = ExternalMessageStatus.SENT
    message.last_error_code = None
    session.add(communication)
    try:
        session.flush()
        message.communication_id = communication.id
        draft.state = EmailDraftState.SENT
        session.commit()
        session.refresh(message)
        return message
    except IntegrityError:
        session.rollback()
        existing = session.get(ExternalMessage, message.id)
        if existing is not None and existing.status is ExternalMessageStatus.SENT:
            return existing
        raise GmailOutboundPersistenceError from None
    except SQLAlchemyError as error:
        session.rollback()
        raise GmailOutboundPersistenceError from error


def _communication_content(subject: str, body: str) -> str:
    return f"Subject: {subject}\n\n{body}"
