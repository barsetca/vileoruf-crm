import asyncio
import os
from collections.abc import Iterator
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.api.dependencies import get_current_user
from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import IntegrationConnection, IntegrationConnectionStatus, IntegrationOAuthState, IntegrationProvider, User, UserRole
from backend.app.models.user import utc_now
from backend.app.schemas.integrations import IntegrationConnectionResponse
from backend.app.services.google_oauth import GoogleOAuthError, complete_google_oauth, disconnect_google_oauth, get_google_access_token, start_google_oauth
from backend.app.services.integrations_adapters import ProviderErrorCode
import backend.app.api.integrations.router as router_module
import backend.app.services.google_oauth as google_oauth
import backend.app.services.integrations_crypto as crypto


def _settings():
    return SimpleNamespace(
        google_oauth_client_id="synthetic-client-id",
        google_oauth_client_secret=SecretStr("synthetic-client-secret"),
        google_oauth_redirect_uri="http://localhost:8000/settings/integrations/google/callback",
        google_oauth_state_ttl_seconds=600,
    )


@pytest.fixture(autouse=True)
def oauth_configuration(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(google_oauth, "get_google_oauth_settings", _settings)
    monkeypatch.setattr(crypto, "get_integration_security_settings", lambda: SimpleNamespace(integration_token_encryption_key=SecretStr(key)))


@pytest.fixture
def isolated_database() -> Iterator[sessionmaker[Session]]:
    source = make_url(os.environ["DATABASE_URL"])
    name = f"vileoruf_d52a_{uuid4().hex}"
    maintenance = create_engine(source.set(database="postgres"), isolation_level="AUTOCOMMIT")
    url = source.set(database=name)
    engine = None
    with maintenance.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    get_settings.cache_clear()
    try:
        command.upgrade(Config("backend/alembic.ini"), "head")
        engine = create_engine(url)
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        get_settings.cache_clear()
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        if engine is not None:
            engine.dispose()
        with maintenance.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        maintenance.dispose()


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_google_oauth_encrypted_state_refresh_and_disconnect_lifecycle(isolated_database, monkeypatch):
    with isolated_database() as session:
        admin = User(email="d52a-admin@example.test", password_hash="synthetic", display_name="Admin", role=UserRole.ADMIN, is_active=True)
        session.add(admin)
        session.commit()

        started = start_google_oauth(session, admin=admin)
        query = parse_qs(urlparse(started.authorization_url).query)
        state = query["state"][0]
        assert query["scope"][0].split() == list(google_oauth.GOOGLE_OAUTH_SCOPES)
        assert query["access_type"] == ["offline"]
        oauth_state = session.scalar(select(IntegrationOAuthState))
        assert oauth_state.state_hash != state and oauth_state.consumed_at is None
        connection = session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider == IntegrationProvider.GMAIL))
        assert connection.status is IntegrationConnectionStatus.CONNECTING

        monkeypatch.setattr(google_oauth, "exchange_google_authorization_code", lambda code: {"access_token": "synthetic-access", "refresh_token": "synthetic-refresh", "expires_in": 0, "scope": " ".join(google_oauth.GOOGLE_OAUTH_SCOPES), "token_type": "Bearer"})
        connected = complete_google_oauth(session, state=state, code="synthetic-code")
        assert connected.status is IntegrationConnectionStatus.CONNECTED
        assert connected.encrypted_token_payload is not None and "synthetic-access" not in connected.encrypted_token_payload
        safe_response = IntegrationConnectionResponse.model_validate(connected).model_dump()
        assert "encrypted_token_payload" not in safe_response

        monkeypatch.setattr(google_oauth, "refresh_google_access_token", lambda refresh_token: {"access_token": "refreshed-access", "expires_in": 3600, "token_type": "Bearer"})
        assert get_google_access_token(session, connection=connected) == "refreshed-access"
        payload = google_oauth._load_token_payload(connected)
        assert payload["refresh_token"] == "synthetic-refresh"

        with pytest.raises(GoogleOAuthError) as invalid_state:
            complete_google_oauth(session, state="invalid-state", code="synthetic-code")
        assert invalid_state.value.code is ProviderErrorCode.AUTH_REQUIRED

        disconnected = disconnect_google_oauth(session)
        assert disconnected.status is IntegrationConnectionStatus.DISCONNECTED
        assert disconnected.encrypted_token_payload is None


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_expired_or_missing_state_does_not_exchange_code(isolated_database, monkeypatch):
    with isolated_database() as session:
        admin = User(email="expired-admin@example.test", password_hash="synthetic", display_name="Admin", role=UserRole.ADMIN, is_active=True)
        connection = IntegrationConnection(provider=IntegrationProvider.GMAIL, status=IntegrationConnectionStatus.CONNECTING, display_name="Gmail")
        session.add_all([admin, connection])
        session.flush()
        session.add(IntegrationOAuthState(state_hash=google_oauth._state_hash("expired-state"), integration_connection_id=connection.id, initiated_by_user_id=admin.id, expires_at=utc_now() - timedelta(seconds=1)))
        session.commit()
        called = False
        def exchange(code):
            nonlocal called
            called = True
            return {}
        monkeypatch.setattr(google_oauth, "exchange_google_authorization_code", exchange)
        with pytest.raises(GoogleOAuthError):
            complete_google_oauth(session, state="expired-state", code="synthetic-code")
        with pytest.raises(GoogleOAuthError):
            complete_google_oauth(session, state=None, code="synthetic-code")
        assert called is False


def _request(method, path):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path)
    return asyncio.run(send())


def test_google_management_api_admin_manager_and_unauthenticated_boundaries(monkeypatch):
    admin = User(email="api-admin@example.test", password_hash="synthetic", display_name="Admin", role=UserRole.ADMIN, is_active=True)
    manager = User(email="api-manager@example.test", password_hash="synthetic", display_name="Manager", role=UserRole.MANAGER, is_active=True)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        app.dependency_overrides[get_current_user] = lambda: manager
        assert _request("POST", "/settings/integrations/google/connect").status_code == 403
        app.dependency_overrides[get_current_user] = lambda: admin
        monkeypatch.setattr(router_module, "start_google_oauth", lambda session, admin: SimpleNamespace(authorization_url="https://accounts.google.test/oauth?state=opaque"))
        response = _request("POST", "/settings/integrations/google/connect")
        assert response.status_code == 200
        assert response.json() == {"authorization_url": "https://accounts.google.test/oauth?state=opaque"}
        async def unauthenticated():
            from fastapi import HTTPException
            raise HTTPException(401, "Authentication required")
        app.dependency_overrides[get_current_user] = unauthenticated
        assert _request("POST", "/settings/integrations/google/reconnect").status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_google_oauth_requires_valid_encryption_configuration(monkeypatch):
    monkeypatch.setattr(crypto, "get_integration_security_settings", lambda: SimpleNamespace(integration_token_encryption_key=None))
    with pytest.raises(GoogleOAuthError) as error:
        start_google_oauth(None, admin=SimpleNamespace(id=uuid4()))
    assert error.value.code is ProviderErrorCode.INVALID_CONFIGURATION
