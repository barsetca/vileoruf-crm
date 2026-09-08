"""Google Calendar authorization reuse boundary; event operations intentionally do not live here yet."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider
from backend.app.models.user import utc_now
from backend.app.services.google_oauth import GoogleOAuthError, get_google_access_token, get_google_authorized_scopes
from backend.app.services.integrations_adapters import ProviderErrorCode


GOOGLE_CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"


class GoogleCalendarError(ValueError):
    def __init__(self, code: ProviderErrorCode):
        self.code = code
        super().__init__(code.value)


def synchronize_google_calendar_connection(session: Session) -> IntegrationConnection:
    """Persist a safe Calendar status derived from the single Gmail token owner.

    Calendar deliberately has its own provider record but never receives a copy of
    the encrypted Google payload.
    """
    calendar = _get_or_create_calendar_connection(session)
    gmail = session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider == IntegrationProvider.GMAIL))
    if gmail is None:
        _set_disconnected(calendar)
    elif gmail.status is not IntegrationConnectionStatus.CONNECTED:
        _copy_owner_state(calendar, gmail)
    else:
        try:
            authorized_scopes = get_google_authorized_scopes(gmail)
        except GoogleOAuthError as error:
            _set_error(calendar, error.code)
        except Exception:
            _set_error(calendar, ProviderErrorCode.AUTH_REQUIRED)
        else:
            if GOOGLE_CALENDAR_EVENTS_SCOPE not in authorized_scopes:
                _set_error(calendar, ProviderErrorCode.PERMISSION_DENIED)
            else:
                _set_connected(calendar, gmail)
    session.commit()
    session.refresh(calendar)
    return calendar


def get_google_calendar_access_token(session: Session) -> str:
    """Return a refreshed shared Google token only after Calendar scope validation."""
    calendar = synchronize_google_calendar_connection(session)
    if calendar.status is not IntegrationConnectionStatus.CONNECTED:
        raise GoogleCalendarError(_calendar_error_code(calendar))
    gmail = session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider == IntegrationProvider.GMAIL))
    if gmail is None:
        raise GoogleCalendarError(ProviderErrorCode.AUTH_REQUIRED)
    try:
        return get_google_access_token(session, connection=gmail)
    except GoogleOAuthError as error:
        _set_error(calendar, error.code)
        session.commit()
        raise GoogleCalendarError(error.code) from error


def _get_or_create_calendar_connection(session: Session) -> IntegrationConnection:
    connection = session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider == IntegrationProvider.GOOGLE_CALENDAR))
    if connection is None:
        connection = IntegrationConnection(
            provider=IntegrationProvider.GOOGLE_CALENDAR,
            status=IntegrationConnectionStatus.DISCONNECTED,
            display_name="Google Calendar",
        )
        session.add(connection)
        session.flush()
    return connection


def _set_disconnected(calendar: IntegrationConnection) -> None:
    calendar.status = IntegrationConnectionStatus.DISCONNECTED
    calendar.external_account_id = None
    calendar.external_account_email = None
    calendar.connected_at = None
    calendar.last_success_at = None
    calendar.last_error_at = None
    calendar.last_error_code = None
    calendar.encrypted_token_payload = None


def _copy_owner_state(calendar: IntegrationConnection, gmail: IntegrationConnection) -> None:
    calendar.status = gmail.status
    calendar.external_account_id = gmail.external_account_id
    calendar.external_account_email = gmail.external_account_email
    calendar.connected_at = gmail.connected_at
    calendar.last_success_at = gmail.last_success_at
    calendar.last_error_at = gmail.last_error_at
    calendar.last_error_code = gmail.last_error_code
    calendar.encrypted_token_payload = None


def _set_connected(calendar: IntegrationConnection, gmail: IntegrationConnection) -> None:
    calendar.status = IntegrationConnectionStatus.CONNECTED
    calendar.external_account_id = gmail.external_account_id
    calendar.external_account_email = gmail.external_account_email
    calendar.connected_at = gmail.connected_at
    calendar.last_success_at = gmail.last_success_at or utc_now()
    calendar.last_error_at = None
    calendar.last_error_code = None
    calendar.encrypted_token_payload = None


def _set_error(calendar: IntegrationConnection, code: ProviderErrorCode) -> None:
    calendar.status = IntegrationConnectionStatus.ERROR
    calendar.last_error_code = code.value
    calendar.last_error_at = utc_now()
    calendar.encrypted_token_payload = None


def _calendar_error_code(calendar: IntegrationConnection) -> ProviderErrorCode:
    try:
        return ProviderErrorCode(calendar.last_error_code or ProviderErrorCode.AUTH_REQUIRED.value)
    except ValueError:
        return ProviderErrorCode.AUTH_REQUIRED
