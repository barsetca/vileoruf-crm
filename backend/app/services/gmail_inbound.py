"""Bounded D5.2c Gmail inbound synchronization and CRM finalization."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import Client, Communication, CommunicationChannel, CommunicationDirection, CommunicationStatus, Deal, ExternalMessage, ExternalMessageStatus, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider
from backend.app.models.user import utc_now
from backend.app.services.ai.deal_prediction import invalidate_latest_deal_prediction
from backend.app.services.ai.next_best_action import invalidate_latest_next_best_action
from backend.app.services.business import invalidate_latest_lead_scoring
from backend.app.services.google_oauth import GoogleOAuthError, get_google_access_token
from backend.app.services.integrations_adapters import GmailAdapterError, GmailInboundMessage, ProviderErrorCode, get_gmail_inbound_message, list_gmail_inbound_message_ids

SYNC_PAGE_SIZE = 25
# Gmail search indexing can lag a just-arrived message. Re-read a small,
# bounded overlap; provider-message uniqueness makes that overlap idempotent.
SYNC_LOOKBACK = timedelta(minutes=5)


class GmailInboundError(ValueError):
    def __init__(self, code: ProviderErrorCode):
        self.code = code
        super().__init__(code.value)


def request_gmail_inbound_sync(session: Session) -> IntegrationConnection:
    connection = get_usable_gmail_inbound_connection(session)
    if connection.inbound_sync_status != "RUNNING":
        connection.inbound_sync_status = "RUNNING"
        connection.inbound_sync_error_code = None
        session.commit()
        session.refresh(connection)
    return connection


def get_usable_gmail_inbound_connection(session: Session) -> IntegrationConnection:
    connection = _gmail_connection(session)
    _ensure_usable(connection)
    return connection


def execute_gmail_inbound_sync(session: Session) -> dict:
    connection = _gmail_connection(session)
    _ensure_usable(connection)
    started_at = utc_now()
    if connection.inbound_sync_after is None:
        connection.inbound_sync_after = started_at
        connection.inbound_sync_page_token = None
        connection.inbound_sync_status = "IDLE"
        connection.last_inbound_sync_at = started_at
        session.commit()
        return {"initialized": True, "processed": 0}
    try:
        access_token = get_google_access_token(session, connection=connection)
        query_after = connection.inbound_sync_after - SYNC_LOOKBACK
        page = list_gmail_inbound_message_ids(access_token=access_token, after=query_after, page_token=connection.inbound_sync_page_token, max_results=SYNC_PAGE_SIZE)
        processed = 0
        for provider_message_id in page.message_ids:
            inbound = get_gmail_inbound_message(access_token=access_token, provider_message_id=provider_message_id)
            process_gmail_inbound_message(session, connection=connection, inbound=inbound)
            processed += 1
        connection.inbound_sync_page_token = page.next_page_token
        if page.next_page_token is None:
            connection.inbound_sync_after = started_at
        connection.inbound_sync_status = "IDLE"
        connection.last_inbound_sync_at = utc_now()
        connection.inbound_sync_error_code = None
        session.commit()
        return {"initialized": False, "processed": processed, "has_more": page.next_page_token is not None}
    except GoogleOAuthError as error:
        return _fail_sync(session, connection, error.code)
    except GmailAdapterError as error:
        return _fail_sync(session, connection, error.code)
    except SQLAlchemyError:
        session.rollback()
        connection = _gmail_connection(session)
        return _fail_sync(session, connection, ProviderErrorCode.PROVIDER_ERROR)


def process_gmail_inbound_message(session: Session, *, connection: IntegrationConnection, inbound: GmailInboundMessage) -> ExternalMessage:
    existing = session.scalar(select(ExternalMessage).where(ExternalMessage.integration_connection_id == connection.id, ExternalMessage.provider_message_id == inbound.provider_message_id))
    if existing is not None:
        return existing
    client = _exact_client(session, inbound.sender)
    if client is None:
        client = _thread_client(session, connection=connection, thread_id=inbound.provider_thread_id)
    deal = _thread_deal(session, connection=connection, client_id=client.id if client else None, thread_id=inbound.provider_thread_id)
    message = ExternalMessage(integration_connection_id=connection.id, provider=IntegrationProvider.GMAIL, provider_message_id=inbound.provider_message_id, provider_thread_id=inbound.provider_thread_id, client_id=client.id if client else None, deal_id=deal.id if deal else None, direction="INCOMING", status=ExternalMessageStatus.RECEIVED, sender_identifier=inbound.sender, recipient_identifier=inbound.recipient, subject=inbound.subject or None, content=inbound.content, provider_created_at=inbound.provider_created_at, received_at=utc_now())
    session.add(message)
    if client is not None:
        communication = Communication(client_id=client.id, deal_id=deal.id if deal else None, channel=CommunicationChannel.EMAIL, direction=CommunicationDirection.INCOMING, content=inbound.content, occurred_at=inbound.provider_created_at or utc_now(), status=CommunicationStatus.RECORDED)
        session.add(communication)
        session.flush()
        message.communication_id = communication.id
        if deal is not None:
            invalidate_latest_lead_scoring(session, deal_id=deal.id)
            invalidate_latest_deal_prediction(session, deal_id=deal.id)
            invalidate_latest_next_best_action(session, deal_id=deal.id)
    try:
        session.commit()
        session.refresh(message)
        return message
    except IntegrityError:
        session.rollback()
        existing = session.scalar(select(ExternalMessage).where(ExternalMessage.integration_connection_id == connection.id, ExternalMessage.provider_message_id == inbound.provider_message_id))
        if existing is not None:
            return existing
        raise


def _exact_client(session: Session, sender: str) -> Client | None:
    matches = list(session.scalars(select(Client).where(func.lower(func.trim(Client.email)) == sender.lower())))
    return matches[0] if len(matches) == 1 else None


def _thread_client(session: Session, *, connection: IntegrationConnection, thread_id: str | None) -> Client | None:
    if not thread_id:
        return None
    client_ids = set(session.scalars(select(ExternalMessage.client_id).where(ExternalMessage.integration_connection_id == connection.id, ExternalMessage.provider == IntegrationProvider.GMAIL, ExternalMessage.direction == "OUTGOING", ExternalMessage.status == ExternalMessageStatus.SENT, ExternalMessage.provider_thread_id == thread_id, ExternalMessage.client_id.is_not(None))))
    if len(client_ids) != 1:
        return None
    return session.get(Client, next(iter(client_ids)))


def _thread_deal(session: Session, *, connection: IntegrationConnection, client_id, thread_id: str | None) -> Deal | None:
    if client_id is None or not thread_id:
        return None
    deal_ids = set(session.scalars(select(ExternalMessage.deal_id).where(ExternalMessage.integration_connection_id == connection.id, ExternalMessage.provider == IntegrationProvider.GMAIL, ExternalMessage.direction == "OUTGOING", ExternalMessage.status == ExternalMessageStatus.SENT, ExternalMessage.provider_thread_id == thread_id, ExternalMessage.client_id == client_id, ExternalMessage.deal_id.is_not(None))))
    if len(deal_ids) != 1:
        return None
    deal = session.get(Deal, next(iter(deal_ids)))
    return deal if deal is not None and deal.client_id == client_id else None


def _gmail_connection(session: Session) -> IntegrationConnection:
    connection = session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider == IntegrationProvider.GMAIL))
    if connection is None:
        raise GmailInboundError(ProviderErrorCode.AUTH_REQUIRED)
    return connection


def _ensure_usable(connection: IntegrationConnection) -> None:
    if connection.status is not IntegrationConnectionStatus.CONNECTED or not connection.encrypted_token_payload:
        raise GmailInboundError(ProviderErrorCode.AUTH_REQUIRED)


def _fail_sync(session: Session, connection: IntegrationConnection, code: ProviderErrorCode) -> dict:
    connection.inbound_sync_status = "ERROR"
    connection.inbound_sync_error_code = code.value
    session.commit()
    return {"initialized": False, "processed": 0, "error": code.value}
