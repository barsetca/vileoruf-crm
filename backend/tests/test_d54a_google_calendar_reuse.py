import json
import os
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import select

from backend.app.models import IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, User, UserRole
from backend.app.services.google_calendar import (
    GOOGLE_CALENDAR_EVENTS_SCOPE,
    GoogleCalendarError,
    get_google_calendar_access_token,
    synchronize_google_calendar_connection,
)
from backend.app.services.google_oauth import GOOGLE_OAUTH_SCOPES, complete_google_oauth, start_google_oauth
from backend.app.services.integrations_adapters import ProviderErrorCode, google_calendar_authorization_headers
from backend.app.services.integrations_crypto import encrypt_token_payload
import backend.app.services.google_calendar as google_calendar
import backend.app.services.google_oauth as google_oauth
import backend.app.services.integrations_crypto as crypto
from backend.tests.test_d52a_google_oauth import isolated_database


@pytest.fixture(autouse=True)
def oauth_configuration(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(
        google_oauth,
        "get_google_oauth_settings",
        lambda: SimpleNamespace(
            google_oauth_client_id="synthetic-client-id",
            google_oauth_client_secret=SecretStr("synthetic-client-secret"),
            google_oauth_redirect_uri="http://localhost:8000/settings/integrations/google/callback",
            google_oauth_state_ttl_seconds=600,
        ),
    )
    monkeypatch.setattr(crypto, "get_integration_security_settings", lambda: SimpleNamespace(integration_token_encryption_key=SecretStr(key)))


def _payload(*, scopes):
    return encrypt_token_payload(json.dumps({"access_token": "synthetic-access", "refresh_token": "synthetic-refresh", "expires_at": "2099-01-01T00:00:00+00:00", "scopes": list(scopes), "token_type": "Bearer"}).encode())


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_calendar_connection_reuses_gmail_token_owner_without_copying_payload(isolated_database, monkeypatch):
    with isolated_database() as session:
        admin = User(email="d54a-admin@example.test", password_hash="synthetic", display_name="Admin", role=UserRole.ADMIN, is_active=True)
        session.add(admin)
        session.commit()
        started = start_google_oauth(session, admin=admin)
        state = parse_qs(urlparse(started.authorization_url).query)["state"][0]
        monkeypatch.setattr(google_oauth, "exchange_google_authorization_code", lambda code: {"access_token": "synthetic-access", "refresh_token": "synthetic-refresh", "expires_in": 3600, "scope": " ".join(GOOGLE_OAUTH_SCOPES)})
        gmail = complete_google_oauth(session, state=state, code="synthetic-code")

        calendar = session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider == IntegrationProvider.GOOGLE_CALENDAR))
        assert calendar is not None
        assert calendar.status is IntegrationConnectionStatus.CONNECTED
        assert calendar.encrypted_token_payload is None
        assert gmail.encrypted_token_payload is not None

        observed = []
        monkeypatch.setattr(google_calendar, "get_google_access_token", lambda session, connection: observed.append(connection.id) or "shared-access")
        assert get_google_calendar_access_token(session) == "shared-access"
        assert observed == [gmail.id]
        assert google_calendar_authorization_headers(access_token="shared-access") == {"Authorization": "Bearer shared-access"}


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_calendar_missing_scope_is_safe_error_and_does_not_degrade_gmail(isolated_database):
    with isolated_database() as session:
        gmail = IntegrationConnection(
            provider=IntegrationProvider.GMAIL,
            status=IntegrationConnectionStatus.CONNECTED,
            display_name="Gmail",
            encrypted_token_payload=_payload(scopes=[scope for scope in GOOGLE_OAUTH_SCOPES if scope != GOOGLE_CALENDAR_EVENTS_SCOPE]),
        )
        session.add(gmail)
        session.commit()

        calendar = synchronize_google_calendar_connection(session)
        assert calendar.status is IntegrationConnectionStatus.ERROR
        assert calendar.last_error_code == ProviderErrorCode.PERMISSION_DENIED.value
        assert calendar.encrypted_token_payload is None
        assert session.get(IntegrationConnection, gmail.id).status is IntegrationConnectionStatus.CONNECTED
        with pytest.raises(GoogleCalendarError) as error:
            get_google_calendar_access_token(session)
        assert error.value.code is ProviderErrorCode.PERMISSION_DENIED


def test_calendar_adapter_refuses_empty_token_without_exposing_it():
    with pytest.raises(Exception) as error:
        google_calendar_authorization_headers(access_token="")
    assert "access_token" not in str(error.value)
