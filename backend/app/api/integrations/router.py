from typing import Annotated
from uuid import UUID
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from backend.app.api.dependencies import get_current_user, require_admin
from backend.app.core.config import get_frontend_settings
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.integrations import GmailSyncStartResponse, GoogleOAuthStartResponse, IntegrationConnectionResponse, TelegramAvailabilityResponse, TelegramConfigurationResponse, TelegramMessageCreate, TelegramMessageLink
from backend.app.services.google_oauth import GoogleOAuthError, complete_google_oauth, disconnect_google_oauth, start_google_oauth
from backend.app.services.integrations import list_integration_connections, telegram_operational_available
from backend.app.services.gmail_inbound import GmailInboundError, request_gmail_inbound_sync
from backend.app.workers.integration_tasks import sync_gmail_inbound
from backend.app.workers.integration_tasks import send_telegram_external_message
from backend.app.core.config import get_telegram_settings
from backend.app.services.telegram import TelegramError, TelegramForbiddenError, TelegramIdempotencyConflictError, link_telegram_message, process_telegram_update, request_telegram_send, validate_telegram_configuration
router=APIRouter(prefix="/settings/integrations",tags=["integrations"])
@router.get("",response_model=list[IntegrationConnectionResponse])
def read_connections(session: Annotated[Session,Depends(get_db)], admin: Annotated[User,Depends(require_admin)]):
    return list_integration_connections(session)


@router.get("/telegram/availability", response_model=TelegramAvailabilityResponse)
def read_telegram_availability(session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    return TelegramAvailabilityResponse(available=telegram_operational_available(session))


@router.post("/google/connect", response_model=GoogleOAuthStartResponse)
def connect_google(session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]):
    return _start_google_oauth(session, admin)


@router.post("/google/reconnect", response_model=GoogleOAuthStartResponse)
def reconnect_google(session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]):
    return _start_google_oauth(session, admin)


@router.post("/google/disconnect", response_model=IntegrationConnectionResponse)
def disconnect_google(session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]):
    return disconnect_google_oauth(session)


@router.post("/gmail/sync", response_model=GmailSyncStartResponse, status_code=status.HTTP_202_ACCEPTED)
def sync_gmail(session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]):
    try:
        request_gmail_inbound_sync(session)
        sync_gmail_inbound.delay(trigger="manual")
        return GmailSyncStartResponse(status="RUNNING")
    except GmailInboundError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Gmail inbound synchronization is unavailable") from error
    except Exception:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Gmail synchronization queue is unavailable") from None


@router.post("/telegram/validate", response_model=TelegramConfigurationResponse)
def validate_telegram(session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]):
    try:
        validate_telegram_configuration(session)
        return TelegramConfigurationResponse(status="CONNECTED")
    except TelegramError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Telegram configuration is unavailable") from error


@router.post("/telegram/messages", status_code=status.HTTP_202_ACCEPTED)
def send_telegram(payload: TelegramMessageCreate, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)], idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]):
    try:
        key=idempotency_key.strip()
        if not key: raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Idempotency-Key is required")
        message, created=request_telegram_send(session, client_id=payload.client_id, deal_id=payload.deal_id, content=payload.content.strip(), idempotency_key=key, current_user=current_user)
        if created: send_telegram_external_message.delay(str(message.id))
        return {"status":"PENDING","external_message_id":message.id}
    except TelegramForbiddenError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Telegram send is forbidden") from error
    except TelegramIdempotencyConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Telegram idempotency key conflicts with a different request") from error
    except TelegramError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Telegram send is unavailable") from error


@router.post("/telegram/messages/{external_message_id}/link")
def link_telegram(external_message_id: UUID, payload: TelegramMessageLink, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try:
        return link_telegram_message(session, external_message_id=external_message_id, client_id=payload.client_id, current_user=current_user)
    except TelegramError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Telegram message cannot be linked") from error




@router.get("/google/callback", include_in_schema=False)
def google_callback(
    session: Annotated[Session, Depends(get_db)],
    state_value: str | None = Query(default=None, alias="state"),
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    try:
        complete_google_oauth(session, state=state_value, code=code, provider_error=error)
    except GoogleOAuthError:
        return _callback_redirect("error")
    return _callback_redirect("success")


def _start_google_oauth(session: Session, admin: User) -> GoogleOAuthStartResponse:
    try:
        result = start_google_oauth(session, admin=admin)
    except GoogleOAuthError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Google OAuth configuration is unavailable") from error
    return GoogleOAuthStartResponse(authorization_url=result.authorization_url)


def _callback_redirect(outcome: str) -> RedirectResponse:
    destination = f"{get_frontend_settings().frontend_origin.rstrip('/')}/crm/settings/integrations?{urlencode({'google_oauth': outcome})}"
    return RedirectResponse(destination, status_code=status.HTTP_303_SEE_OTHER)
