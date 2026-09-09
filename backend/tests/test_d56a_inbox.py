import asyncio
import os
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Client, Communication, ExternalMessage, ExternalMessageStatus, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, User, UserRole
from backend.app.models.user import utc_now
from backend.tests.test_d52a_google_oauth import isolated_database


def _request(method, path, payload=None):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, json=payload)
    return asyncio.run(send())


def _message(connection, provider, *, direction="INCOMING", client_id=None, communication_id=None, content="synthetic inbound", offset=0):
    now = utc_now() + timedelta(minutes=offset)
    return ExternalMessage(
        integration_connection_id=connection.id, provider=provider, provider_message_id=f"synthetic-{provider.value}-{offset}-{direction}",
        client_id=client_id, communication_id=communication_id, direction=direction, status=ExternalMessageStatus.RECEIVED,
        sender_identifier=f"sender-{offset}", recipient_identifier="crm", subject="Synthetic subject", content=content,
        provider_created_at=now, received_at=now,
    )


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_inbox_api_is_authenticated_bounded_safe_and_only_returns_unmatched_inbound(isolated_database):
    with isolated_database() as session:
        admin = User(email="d56a-admin@example.test", password_hash="x", display_name="Admin", role=UserRole.ADMIN, is_active=True)
        manager = User(email="d56a-manager@example.test", password_hash="x", display_name="Manager", role=UserRole.MANAGER, is_active=True)
        client = Client(name="Already linked")
        telegram = IntegrationConnection(provider=IntegrationProvider.TELEGRAM, status=IntegrationConnectionStatus.CONNECTED, display_name="Telegram")
        gmail = IntegrationConnection(provider=IntegrationProvider.GMAIL, status=IntegrationConnectionStatus.CONNECTED, display_name="Gmail")
        session.add_all([admin, manager, client, telegram, gmail]); session.commit()
        visible_telegram = _message(telegram, IntegrationProvider.TELEGRAM, content="telegram visible", offset=2)
        visible_gmail = _message(gmail, IntegrationProvider.GMAIL, content="gmail visible", offset=1)
        ignored_outgoing = _message(telegram, IntegrationProvider.TELEGRAM, direction="OUTGOING", offset=3)
        ignored_matched = _message(gmail, IntegrationProvider.GMAIL, client_id=client.id, offset=4)
        session.add_all([visible_telegram, visible_gmail, ignored_outgoing, ignored_matched]); session.commit()

        assert _request("GET", "/inbox/external-messages").status_code == 401
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: manager
        try:
            response = _request("GET", "/inbox/external-messages?limit=1&offset=0")
            manager_response = _request("GET", "/inbox/external-messages?limit=25&offset=0")
            app.dependency_overrides[get_current_user] = lambda: admin
            admin_response = _request("GET", "/inbox/external-messages?limit=25&offset=0")
        finally:
            app.dependency_overrides.clear()
        assert response.status_code == manager_response.status_code == admin_response.status_code == 200
        items = admin_response.json()
        assert [item["id"] for item in items] == [str(visible_telegram.id), str(visible_gmail.id)]
        assert response.json()[0]["id"] == str(visible_telegram.id)
        assert set(items[0]) == {"id", "provider", "channel", "sender_identifier", "content", "subject", "occurred_at"}
        assert "recipient_identifier" not in items[0] and "integration_connection_id" not in items[0]


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_inbox_manual_link_reuses_telegram_rules_and_creates_one_communication(isolated_database):
    with isolated_database() as session:
        manager = User(email="d56a-link-manager@example.test", password_hash="x", display_name="Manager", role=UserRole.MANAGER, is_active=True)
        target = Client(name="Selected existing client")
        telegram = IntegrationConnection(provider=IntegrationProvider.TELEGRAM, status=IntegrationConnectionStatus.CONNECTED, display_name="Telegram")
        session.add_all([manager, target, telegram]); session.commit()
        unmatched = _message(telegram, IntegrationProvider.TELEGRAM, content="controlled unmatched telegram", offset=1)
        session.add(unmatched); session.commit()
        initial_clients = session.scalar(select(func.count()).select_from(Client))
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: manager
        try:
            first = _request("POST", f"/inbox/external-messages/{unmatched.id}/link", {"client_id": str(target.id)})
            repeated = _request("POST", f"/inbox/external-messages/{unmatched.id}/link", {"client_id": str(target.id)})
        finally:
            app.dependency_overrides.clear()
        linked = session.get(ExternalMessage, unmatched.id)
        communication = session.get(Communication, linked.communication_id)
        assert first.status_code == repeated.status_code == 200
        assert linked.client_id == target.id and linked.deal_id is None and linked.communication_id
        assert target.telegram_provider_user_id == unmatched.sender_identifier
        assert communication.client_id == target.id and communication.deal_id is None and communication.channel.value == "TELEGRAM"
        assert session.scalar(select(func.count()).select_from(Communication)) == 1
        assert session.scalar(select(func.count()).select_from(Client)) == initial_clients
