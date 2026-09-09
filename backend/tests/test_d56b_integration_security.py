import asyncio
import os

import httpx
import pytest

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, User, UserRole
from backend.tests.test_d52a_google_oauth import isolated_database
import backend.app.services.integrations as integration_service


def _request(method, path):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path)
    return asyncio.run(send())


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_integration_management_is_admin_only_and_connection_response_is_safe(isolated_database, monkeypatch):
    with isolated_database() as session:
        admin = User(email="d56b-admin@example.test", password_hash="x", display_name="Admin", role=UserRole.ADMIN, is_active=True)
        manager = User(email="d56b-manager@example.test", password_hash="x", display_name="Manager", role=UserRole.MANAGER, is_active=True)
        gmail = IntegrationConnection(provider=IntegrationProvider.GMAIL, status=IntegrationConnectionStatus.ERROR, display_name="Gmail", external_account_email="safe@example.test", encrypted_token_payload="must-not-appear", last_error_code="AUTH_REQUIRED")
        session.add_all([admin, manager, gmail]); session.commit()
        monkeypatch.setattr(integration_service, "synchronize_google_calendar_connection", lambda _: None)

        assert _request("GET", "/settings/integrations").status_code == 401
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: manager
        try:
            assert _request("GET", "/settings/integrations").status_code == 403
            assert _request("POST", "/settings/integrations/google/connect").status_code == 403
            assert _request("POST", "/settings/integrations/google/reconnect").status_code == 403
            assert _request("POST", "/settings/integrations/google/disconnect").status_code == 403
            assert _request("POST", "/settings/integrations/gmail/sync").status_code == 403
            assert _request("POST", "/settings/integrations/telegram/validate").status_code == 403
            app.dependency_overrides[get_current_user] = lambda: admin
            response = _request("GET", "/settings/integrations")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        gmail_payload = next(item for item in response.json() if item["provider"] == "GMAIL")
        assert gmail_payload["last_error_code"] == "AUTH_REQUIRED"
        assert "encrypted_token_payload" not in gmail_payload
        assert "must-not-appear" not in response.text
