"""D5.3 Telegram Bot boundary; credentials remain environment-only."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_telegram_settings
from backend.app.models import Client, Communication, CommunicationChannel, CommunicationDirection, CommunicationStatus, Deal, ExternalMessage, ExternalMessageStatus, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, User, UserRole
from backend.app.models.user import utc_now
from backend.app.services.integrations_adapters import GmailAdapterError, ProviderErrorCode, RetryClass, send_telegram_message, validate_telegram_bot

class TelegramError(ValueError):
    def __init__(self, code: ProviderErrorCode): self.code=code; super().__init__(code.value)
class TelegramForbiddenError(TelegramError): pass
class TelegramIdempotencyConflictError(TelegramError): pass

def validate_telegram_configuration(session: Session) -> IntegrationConnection:
    settings=get_telegram_settings(); token=settings.telegram_bot_token.get_secret_value() if settings.telegram_bot_token else None
    if not token: raise TelegramError(ProviderErrorCode.AUTH_REQUIRED)
    try: bot=validate_telegram_bot(token=token)
    except GmailAdapterError as error: raise TelegramError(error.code) from error
    connection=session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider==IntegrationProvider.TELEGRAM))
    if connection is None:
        connection=IntegrationConnection(provider=IntegrationProvider.TELEGRAM,status=IntegrationConnectionStatus.CONNECTED,display_name="Telegram",external_account_id=str(bot["id"]),external_account_email=bot.get("username"),connected_at=utc_now(),last_success_at=utc_now())
        session.add(connection)
    else:
        connection.status=IntegrationConnectionStatus.CONNECTED; connection.external_account_id=str(bot["id"]); connection.external_account_email=bot.get("username"); connection.connected_at=connection.connected_at or utc_now(); connection.last_success_at=utc_now(); connection.last_error_code=None
    session.commit(); session.refresh(connection); return connection

def process_telegram_update(session: Session, update: dict) -> ExternalMessage | None:
    message=update.get("message") if isinstance(update,dict) else None
    if not isinstance(message,dict) or not isinstance(message.get("message_id"),int) or not isinstance(message.get("text"),str): return None
    chat=message.get("chat") or {}; sender=message.get("from") or {}
    if chat.get("type") != "private" or not isinstance(chat.get("id"),int) or not isinstance(sender.get("id"),int): return None
    connection=session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider==IntegrationProvider.TELEGRAM, IntegrationConnection.status==IntegrationConnectionStatus.CONNECTED))
    if connection is None: raise TelegramError(ProviderErrorCode.AUTH_REQUIRED)
    provider_id=str(update["update_id"]) if isinstance(update.get("update_id"),int) else f"{chat['id']}:{message['message_id']}"
    existing=session.scalar(select(ExternalMessage).where(ExternalMessage.integration_connection_id==connection.id,ExternalMessage.provider_message_id==provider_id))
    if existing: return existing
    identity=str(sender["id"])
    clients=list(session.scalars(select(Client).where(Client.telegram_provider_user_id==identity)))
    client=clients[0] if len(clients)==1 else None
    external=ExternalMessage(integration_connection_id=connection.id,provider=IntegrationProvider.TELEGRAM,provider_message_id=provider_id,provider_thread_id=str(chat["id"]),client_id=client.id if client else None,direction="INCOMING",status=ExternalMessageStatus.RECEIVED,sender_identifier=identity,recipient_identifier=str(chat["id"]),content=message["text"],provider_created_at=utc_now(),received_at=utc_now())
    session.add(external)
    if client:
        comm=Communication(client_id=client.id,deal_id=None,channel=CommunicationChannel.TELEGRAM,direction=CommunicationDirection.INCOMING,content=message["text"],occurred_at=utc_now(),status=CommunicationStatus.RECORDED); session.add(comm); session.flush(); external.communication_id=comm.id
    try: session.commit(); session.refresh(external); return external
    except IntegrityError: session.rollback(); return session.scalar(select(ExternalMessage).where(ExternalMessage.integration_connection_id==connection.id,ExternalMessage.provider_message_id==provider_id))

def link_telegram_message(session: Session, *, external_message_id: UUID, client_id: UUID, current_user: User) -> ExternalMessage:
    message=session.get(ExternalMessage,external_message_id); client=session.get(Client,client_id)
    if not message or message.provider is not IntegrationProvider.TELEGRAM or message.direction!="INCOMING" or not client: raise TelegramError(ProviderErrorCode.INVALID_RECIPIENT)
    if message.communication_id: return message
    if client.telegram_provider_user_id and client.telegram_provider_user_id != message.sender_identifier: raise TelegramError(ProviderErrorCode.INVALID_RECIPIENT)
    duplicate=session.scalar(select(Client).where(Client.telegram_provider_user_id==message.sender_identifier,Client.id!=client.id))
    if duplicate: raise TelegramError(ProviderErrorCode.INVALID_RECIPIENT)
    client.telegram_provider_user_id=message.sender_identifier; message.client_id=client.id
    comm=Communication(client_id=client.id,deal_id=None,channel=CommunicationChannel.TELEGRAM,direction=CommunicationDirection.INCOMING,content=message.content,occurred_at=message.provider_created_at or utc_now(),status=CommunicationStatus.RECORDED); session.add(comm); session.flush(); message.communication_id=comm.id; session.commit(); session.refresh(message); return message

def request_telegram_send(session: Session, *, client_id: UUID, deal_id: UUID|None, content: str, idempotency_key: str, current_user: User) -> tuple[ExternalMessage, bool]:
    client=session.get(Client,client_id)
    if not client or not client.telegram_provider_user_id: raise TelegramError(ProviderErrorCode.INVALID_RECIPIENT)
    if deal_id:
        deal=session.get(Deal,deal_id)
        if not deal or deal.client_id!=client.id: raise TelegramError(ProviderErrorCode.INVALID_RECIPIENT)
        if current_user.role is UserRole.MANAGER and deal.responsible_user_id!=current_user.id: raise TelegramForbiddenError(ProviderErrorCode.PERMISSION_DENIED)
    connection=session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider==IntegrationProvider.TELEGRAM,IntegrationConnection.status==IntegrationConnectionStatus.CONNECTED))
    if not connection: raise TelegramError(ProviderErrorCode.AUTH_REQUIRED)
    existing=session.scalar(select(ExternalMessage).where(ExternalMessage.integration_connection_id==connection.id,ExternalMessage.idempotency_key==idempotency_key))
    if existing is not None:
        if _same_outbound_request(existing, client_id=client.id, deal_id=deal_id, content=content): return existing, False
        raise TelegramIdempotencyConflictError(ProviderErrorCode.PROVIDER_ERROR)
    msg=ExternalMessage(integration_connection_id=connection.id,provider=IntegrationProvider.TELEGRAM,client_id=client.id,deal_id=deal_id,direction="OUTGOING",status=ExternalMessageStatus.PENDING,sender_identifier=connection.external_account_id or "telegram-bot",recipient_identifier=client.telegram_provider_user_id,content=content,idempotency_key=idempotency_key)
    session.add(msg)
    try: session.commit(); session.refresh(msg); return msg, True
    except IntegrityError:
        session.rollback()
        existing=session.scalar(select(ExternalMessage).where(ExternalMessage.integration_connection_id==connection.id,ExternalMessage.idempotency_key==idempotency_key))
        if existing is not None:
            if _same_outbound_request(existing, client_id=client.id, deal_id=deal_id, content=content): return existing, False
            raise TelegramIdempotencyConflictError(ProviderErrorCode.PROVIDER_ERROR)
        raise

def _same_outbound_request(message: ExternalMessage, *, client_id: UUID, deal_id: UUID|None, content: str) -> bool:
    return message.provider is IntegrationProvider.TELEGRAM and message.direction=="OUTGOING" and message.client_id==client_id and message.deal_id==deal_id and message.content==content

def execute_telegram_send(session: Session, *, external_message_id: UUID) -> ExternalMessage:
    msg=session.get(ExternalMessage,external_message_id)
    if not msg or msg.status is not ExternalMessageStatus.PENDING: return msg
    settings=get_telegram_settings(); token=settings.telegram_bot_token.get_secret_value() if settings.telegram_bot_token else None
    if not token: return _finish(session,msg,ExternalMessageStatus.FAILED,ProviderErrorCode.AUTH_REQUIRED)
    try: result=send_telegram_message(token=token,chat_id=msg.recipient_identifier,content=msg.content)
    except GmailAdapterError as error: return _finish(session,msg,ExternalMessageStatus.UNKNOWN if error.retry_class is RetryClass.UNCERTAIN else ExternalMessageStatus.FAILED,error.code)
    comm=Communication(client_id=msg.client_id,deal_id=msg.deal_id,channel=CommunicationChannel.TELEGRAM,direction=CommunicationDirection.OUTGOING,content=msg.content,occurred_at=utc_now(),status=CommunicationStatus.RECORDED); session.add(comm); session.flush(); msg.provider_message_id=result.provider_message_id; msg.provider_thread_id=result.chat_id; msg.communication_id=comm.id; msg.status=ExternalMessageStatus.SENT; msg.sent_at=utc_now(); msg.provider_created_at=utc_now(); session.commit(); session.refresh(msg); return msg

def _finish(session,msg,status,code): msg.status=status; msg.last_error_code=code.value; session.commit(); session.refresh(msg); return msg
