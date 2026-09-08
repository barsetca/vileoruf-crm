"""Google OAuth and encrypted-token lifecycle for the single corporate Google account."""
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_google_oauth_settings
from backend.app.models import (
    IntegrationConnection,
    IntegrationConnectionStatus,
    IntegrationOAuthState,
    IntegrationProvider,
    User,
    UserRole,
)
from backend.app.models.user import utc_now
from backend.app.services.integrations_adapters import ProviderErrorCode
from backend.app.services.integrations_crypto import IntegrationTokenError, decrypt_token_payload, encrypt_token_payload


GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
)
ACCESS_TOKEN_REFRESH_SKEW_SECONDS = 60


class GoogleOAuthError(ValueError):
    def __init__(self, code: ProviderErrorCode):
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True)
class GoogleOAuthStart:
    authorization_url: str


def start_google_oauth(session: Session, *, admin: User) -> GoogleOAuthStart:
    settings = _require_google_configuration()
    try:
        encrypt_token_payload(b"{}")
    except IntegrationTokenError as error:
        raise GoogleOAuthError(ProviderErrorCode.INVALID_CONFIGURATION) from error
    connection = _get_or_create_gmail_connection(session)
    state = secrets.token_urlsafe(32)
    session.add(
        IntegrationOAuthState(
            state_hash=_state_hash(state),
            integration_connection_id=connection.id,
            initiated_by_user_id=admin.id,
            expires_at=utc_now() + timedelta(seconds=settings.google_oauth_state_ttl_seconds),
        )
    )
    connection.status = IntegrationConnectionStatus.CONNECTING
    connection.last_error_code = None
    connection.last_error_at = None
    session.commit()
    parameters = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_OAUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return GoogleOAuthStart(authorization_url=f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(parameters)}")


def complete_google_oauth(session: Session, *, state: str | None, code: str | None, provider_error: str | None = None) -> IntegrationConnection:
    oauth_state = _consume_valid_state(session, state)
    connection = session.get(IntegrationConnection, oauth_state.integration_connection_id)
    if connection is None:
        session.rollback()
        raise GoogleOAuthError(ProviderErrorCode.PROVIDER_ERROR)
    if provider_error or not code:
        return _mark_connection_error(session, connection, ProviderErrorCode.PERMISSION_DENIED if provider_error else ProviderErrorCode.PROVIDER_ERROR)
    try:
        response = exchange_google_authorization_code(code)
        previous = _load_existing_token_payload(connection)
        payload = _token_payload_from_response(response, previous=previous)
        connection.encrypted_token_payload = encrypt_token_payload(json.dumps(payload, separators=(",", ":")).encode())
    except GoogleOAuthError as error:
        return _mark_connection_error(session, connection, error.code)
    except IntegrationTokenError:
        return _mark_connection_error(session, connection, ProviderErrorCode.INVALID_CONFIGURATION)
    now = utc_now()
    connection.status = IntegrationConnectionStatus.CONNECTED
    connection.connected_at = now
    connection.last_success_at = now
    connection.last_error_at = None
    connection.last_error_code = None
    session.commit()
    _synchronize_calendar_connection(session)
    session.refresh(connection)
    return connection


def disconnect_google_oauth(session: Session) -> IntegrationConnection:
    connection = _get_or_create_gmail_connection(session)
    connection.status = IntegrationConnectionStatus.DISCONNECTED
    connection.encrypted_token_payload = None
    connection.external_account_id = None
    connection.external_account_email = None
    connection.connected_at = None
    connection.last_success_at = None
    connection.last_error_at = None
    connection.last_error_code = None
    session.commit()
    _synchronize_calendar_connection(session)
    session.refresh(connection)
    return connection


def get_google_access_token(session: Session, *, connection: IntegrationConnection) -> str:
    if connection.provider is not IntegrationProvider.GMAIL or connection.status is not IntegrationConnectionStatus.CONNECTED:
        raise GoogleOAuthError(ProviderErrorCode.AUTH_REQUIRED)
    try:
        payload = _load_token_payload(connection)
    except GoogleOAuthError as error:
        _mark_connection_error(session, connection, error.code)
        raise
    except IntegrationTokenError:
        _mark_connection_error(session, connection, ProviderErrorCode.INVALID_CONFIGURATION)
        raise GoogleOAuthError(ProviderErrorCode.INVALID_CONFIGURATION) from None
    if not _access_token_needs_refresh(payload):
        return payload["access_token"]
    try:
        refreshed = refresh_google_access_token(payload["refresh_token"])
        payload = _token_payload_from_response(refreshed, previous=payload)
        connection.encrypted_token_payload = encrypt_token_payload(json.dumps(payload, separators=(",", ":")).encode())
        connection.last_success_at = utc_now()
        session.commit()
        return payload["access_token"]
    except GoogleOAuthError as error:
        _mark_connection_error(session, connection, error.code)
        raise
    except IntegrationTokenError:
        _mark_connection_error(session, connection, ProviderErrorCode.INVALID_CONFIGURATION)
        raise GoogleOAuthError(ProviderErrorCode.INVALID_CONFIGURATION) from None


def get_google_authorized_scopes(connection: IntegrationConnection) -> frozenset[str]:
    """Return persisted, encrypted OAuth scopes without exposing the token payload."""
    payload = _load_token_payload(connection)
    scopes = payload.get("scopes")
    if not isinstance(scopes, list) or not all(isinstance(scope, str) for scope in scopes):
        raise GoogleOAuthError(ProviderErrorCode.AUTH_REQUIRED)
    return frozenset(scopes)


def exchange_google_authorization_code(code: str) -> dict:
    settings = _require_google_configuration()
    return _request_google_token(
        {
            "code": code,
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret.get_secret_value(),
            "redirect_uri": settings.google_oauth_redirect_uri,
            "grant_type": "authorization_code",
        }
    )


def refresh_google_access_token(refresh_token: str) -> dict:
    settings = _require_google_configuration()
    return _request_google_token(
        {
            "refresh_token": refresh_token,
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret.get_secret_value(),
            "grant_type": "refresh_token",
        }
    )


def _request_google_token(data: dict[str, str]) -> dict:
    try:
        response = httpx.post(GOOGLE_TOKEN_ENDPOINT, data=data, timeout=20.0)
    except httpx.RequestError as error:
        raise GoogleOAuthError(ProviderErrorCode.PROVIDER_UNAVAILABLE) from error
    if response.status_code >= 500:
        raise GoogleOAuthError(ProviderErrorCode.PROVIDER_UNAVAILABLE)
    if response.status_code >= 400:
        error_name = _safe_json_value(response, "error")
        if error_name in {"invalid_grant", "invalid_client", "unauthorized_client"}:
            raise GoogleOAuthError(ProviderErrorCode.AUTH_REQUIRED)
        if error_name in {"access_denied", "insufficient_scope"}:
            raise GoogleOAuthError(ProviderErrorCode.PERMISSION_DENIED)
        raise GoogleOAuthError(ProviderErrorCode.PROVIDER_ERROR)
    try:
        payload = response.json()
    except ValueError as error:
        raise GoogleOAuthError(ProviderErrorCode.PROVIDER_ERROR) from error
    if not isinstance(payload, dict):
        raise GoogleOAuthError(ProviderErrorCode.PROVIDER_ERROR)
    return payload


def _get_or_create_gmail_connection(session: Session) -> IntegrationConnection:
    connection = session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider == IntegrationProvider.GMAIL))
    if connection is None:
        connection = IntegrationConnection(provider=IntegrationProvider.GMAIL, status=IntegrationConnectionStatus.DISCONNECTED, display_name="Gmail")
        session.add(connection)
        session.flush()
    return connection


def _consume_valid_state(session: Session, state: str | None) -> IntegrationOAuthState:
    if not state:
        raise GoogleOAuthError(ProviderErrorCode.AUTH_REQUIRED)
    oauth_state = session.scalar(select(IntegrationOAuthState).where(IntegrationOAuthState.state_hash == _state_hash(state)))
    now = utc_now()
    if oauth_state is None or oauth_state.consumed_at is not None or oauth_state.expires_at <= now:
        raise GoogleOAuthError(ProviderErrorCode.AUTH_REQUIRED)
    actor = session.get(User, oauth_state.initiated_by_user_id)
    if actor is None or not actor.is_active or actor.role is not UserRole.ADMIN:
        raise GoogleOAuthError(ProviderErrorCode.AUTH_REQUIRED)
    oauth_state.consumed_at = now
    session.commit()
    return oauth_state


def _mark_connection_error(session: Session, connection: IntegrationConnection, code: ProviderErrorCode) -> IntegrationConnection:
    connection.status = IntegrationConnectionStatus.ERROR
    connection.last_error_code = code.value
    connection.last_error_at = utc_now()
    session.commit()
    session.refresh(connection)
    return connection


def _load_token_payload(connection: IntegrationConnection) -> dict:
    if not connection.encrypted_token_payload:
        raise GoogleOAuthError(ProviderErrorCode.AUTH_REQUIRED)
    try:
        payload = json.loads(decrypt_token_payload(connection.encrypted_token_payload))
    except (IntegrationTokenError, ValueError, TypeError) as error:
        raise IntegrationTokenError("Integration token payload is invalid") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
        raise IntegrationTokenError("Integration token payload is invalid")
    return payload


def _token_payload_from_response(response: dict, *, previous: dict | None) -> dict:
    access_token = response.get("access_token")
    expires_in = response.get("expires_in")
    refresh_token = response.get("refresh_token") or (previous or {}).get("refresh_token")
    if not isinstance(access_token, str) or not access_token or not isinstance(refresh_token, str) or not refresh_token:
        raise GoogleOAuthError(ProviderErrorCode.AUTH_REQUIRED)
    try:
        expires_at = utc_now() + timedelta(seconds=max(0, int(expires_in)))
    except (TypeError, ValueError) as error:
        raise GoogleOAuthError(ProviderErrorCode.PROVIDER_ERROR) from error
    scopes = response.get("scope") or (previous or {}).get("scopes") or list(GOOGLE_OAUTH_SCOPES)
    if isinstance(scopes, str):
        scopes = scopes.split()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at.isoformat(),
        "scopes": list(scopes),
        "token_type": response.get("token_type") or (previous or {}).get("token_type") or "Bearer",
    }


def _access_token_needs_refresh(payload: dict) -> bool:
    try:
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if expires_at.tzinfo is None:
            return True
        return expires_at <= utc_now() + timedelta(seconds=ACCESS_TOKEN_REFRESH_SKEW_SECONDS)
    except (KeyError, TypeError, ValueError):
        return True


def _require_google_configuration():
    settings = get_google_oauth_settings()
    if not settings.google_oauth_client_id or settings.google_oauth_client_secret is None:
        raise GoogleOAuthError(ProviderErrorCode.INVALID_CONFIGURATION)
    return settings


def _load_existing_token_payload(connection: IntegrationConnection) -> dict | None:
    if not connection.encrypted_token_payload:
        return None
    return _load_token_payload(connection)


def _state_hash(state: str) -> str:
    return hashlib.sha256(state.encode()).hexdigest()


def _safe_json_value(response: httpx.Response, key: str) -> str | None:
    try:
        value = response.json().get(key)
    except (ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def _synchronize_calendar_connection(session: Session) -> None:
    # Local import prevents the Calendar reuse service from creating an import cycle.
    from backend.app.services.google_calendar import synchronize_google_calendar_connection

    synchronize_google_calendar_connection(session)
