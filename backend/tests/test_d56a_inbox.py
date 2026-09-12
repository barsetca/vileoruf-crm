import asyncio
import os
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import func, select

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import AIAnalysis, AIAnalysisStatus, AIFunctionType, AIResultLanguage, Client, Communication, Deal, ExternalMessage, ExternalMessageStatus, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, PipelineStage, User, UserRole
from backend.app.models.user import utc_now
from backend.app.services.inbox import list_unmatched_external_messages
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
        assert set(items[0]) == {"id", "provider", "channel", "sender_identifier", "content", "subject", "occurred_at", "sender_username", "sender_first_name", "sender_last_name"}
        assert "recipient_identifier" not in items[0] and "integration_connection_id" not in items[0]
        assert items[1]["sender_identifier"] == visible_gmail.sender_identifier and items[1]["subject"] == "Synthetic subject"
        assert items[0]["sender_username"] is None and items[0]["sender_first_name"] is None and items[0]["sender_last_name"] is None


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_p17_inbox_filters_and_admin_bulk_delete_never_deletes_linked_history(isolated_database):
    with isolated_database() as session:
        admin = User(email="p17-delete-admin@example.test", password_hash="x", display_name="Admin", role=UserRole.ADMIN, is_active=True)
        manager = User(email="p17-delete-manager@example.test", password_hash="x", display_name="Manager", role=UserRole.MANAGER, is_active=True)
        client = Client(name="P1.7 preserved client")
        telegram = IntegrationConnection(provider=IntegrationProvider.TELEGRAM, status=IntegrationConnectionStatus.CONNECTED, display_name="Telegram")
        gmail = IntegrationConnection(provider=IntegrationProvider.GMAIL, status=IntegrationConnectionStatus.CONNECTED, display_name="Gmail")
        session.add_all([admin, manager, client, telegram, gmail]); session.flush()
        email = _message(gmail, IntegrationProvider.GMAIL, offset=41)
        tg = _message(telegram, IntegrationProvider.TELEGRAM, offset=42)
        history = Communication(client_id=client.id, channel="EMAIL", direction="INCOMING", content="preserved", occurred_at=utc_now(), status="RECORDED", read_at=None)
        session.add(history); session.flush()
        linked = _message(gmail, IntegrationProvider.GMAIL, client_id=client.id, communication_id=history.id, offset=43)
        session.add_all([email, tg, linked]); session.commit()
        app.dependency_overrides[get_db] = lambda: session
        try:
            app.dependency_overrides[get_current_user] = lambda: admin
            all_items = _request("GET", "/inbox/external-messages")
            email_items = _request("GET", "/inbox/external-messages?channel=EMAIL")
            tg_items = _request("GET", "/inbox/external-messages?channel=TELEGRAM")
            summary = _request("GET", "/inbox/summary")
            forbidden_target = _request("POST", "/inbox/external-messages/bulk-delete", {"external_message_ids": [str(email.id), str(linked.id)]})
            app.dependency_overrides[get_current_user] = lambda: manager
            forbidden_role = _request("POST", "/inbox/external-messages/bulk-delete", {"external_message_ids": [str(email.id)]})
            app.dependency_overrides[get_current_user] = lambda: admin
            deleted = _request("POST", "/inbox/external-messages/bulk-delete", {"external_message_ids": [str(email.id), str(tg.id)]})
        finally:
            app.dependency_overrides.clear()
        assert all_items.status_code == email_items.status_code == tg_items.status_code == summary.status_code == 200
        assert {item["id"] for item in all_items.json()} == {str(email.id), str(tg.id)}
        assert [item["id"] for item in email_items.json()] == [str(email.id)]
        assert [item["id"] for item in tg_items.json()] == [str(tg.id)]
        assert summary.json() == {"email": 1, "telegram": 1}
        assert forbidden_target.status_code == 409 and forbidden_role.status_code == 403 and deleted.status_code == 204
        assert session.get(ExternalMessage, email.id) is None and session.get(ExternalMessage, tg.id) is None
        assert session.get(ExternalMessage, linked.id) is not None and session.get(Communication, history.id) is not None and session.get(Client, client.id) is not None


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


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_inbox_telegram_deal_link_is_authoritative_idempotent_and_makes_scoring_stale(isolated_database):
    with isolated_database() as session:
        admin = User(email="p16-admin@example.test", password_hash="x", display_name="Admin", role=UserRole.ADMIN, is_active=True)
        client_a = Client(name="P1.6 Deal Client A")
        client_b = Client(name="P1.6 Contradictory Client B")
        stage = PipelineStage(name="P1.6 Active", position=91)
        telegram = IntegrationConnection(provider=IntegrationProvider.TELEGRAM, status=IntegrationConnectionStatus.CONNECTED, display_name="Telegram")
        session.add_all([admin, client_a, client_b, stage, telegram]); session.flush()
        deal = Deal(name="P1.6 selected Deal", client_id=client_a.id, stage_id=stage.id, responsible_user_id=admin.id)
        session.add(deal); session.flush()
        analysis = AIAnalysis(deal_id=deal.id, function_type=AIFunctionType.LEAD_SCORING, status=AIAnalysisStatus.SUCCESS, language=AIResultLanguage.RU, prompt_version="p16", started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), duration_ms=1, input_fingerprint="a" * 64, input_snapshot={}, result_payload={"overall_score": "50"}, is_outdated=False, attempt_count=1)
        unmatched = _message(telegram, IntegrationProvider.TELEGRAM, content="P1.6 deal link", offset=11)
        session.add_all([analysis, unmatched]); session.commit()
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: admin
        try:
            first = _request("POST", f"/inbox/external-messages/{unmatched.id}/link", {"client_id": str(client_b.id), "deal_id": str(deal.id)})
            repeated = _request("POST", f"/inbox/external-messages/{unmatched.id}/link", {"client_id": str(client_b.id), "deal_id": str(deal.id)})
        finally:
            app.dependency_overrides.clear()
        linked = session.get(ExternalMessage, unmatched.id)
        communication = session.get(Communication, linked.communication_id)
        assert first.status_code == repeated.status_code == 200
        assert linked.client_id == client_a.id and linked.deal_id == deal.id
        assert communication.client_id == client_a.id and communication.deal_id == deal.id
        assert client_a.telegram_provider_user_id == unmatched.sender_identifier and client_b.telegram_provider_user_id is None
        assert session.scalar(select(func.count()).select_from(Communication)) == 1
        assert session.get(AIAnalysis, analysis.id).is_outdated is True
        assert unmatched.id not in {item.id for item in list_unmatched_external_messages(session, limit=25, offset=0)}


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_p17_matched_incoming_is_unread_then_assignable_readable_and_detachable(isolated_database):
    with isolated_database() as session:
        admin = User(email="p17-admin@example.test", password_hash="x", display_name="Admin", role=UserRole.ADMIN, is_active=True)
        client = Client(name="P1.7 Иван", telegram_provider_user_id="p17-provider-id")
        stage = PipelineStage(name="P1.7 Active", position=93)
        connection = IntegrationConnection(provider=IntegrationProvider.TELEGRAM, status=IntegrationConnectionStatus.CONNECTED, display_name="Telegram")
        session.add_all([admin, client, stage, connection]); session.flush()
        deal_a = Deal(name="P1.7 Deal A", client_id=client.id, stage_id=stage.id, responsible_user_id=admin.id)
        deal_b = Deal(name="P1.7 Deal B", client_id=client.id, stage_id=stage.id, responsible_user_id=admin.id)
        other_client = Client(name="P1.7 other")
        communication = Communication(client_id=client.id, channel="TELEGRAM", direction="INCOMING", content="P1.7 inbound", occurred_at=utc_now(), status="RECORDED", read_at=None)
        session.add_all([deal_a, deal_b, other_client, communication]); session.flush()
        other_deal = Deal(name="P1.7 foreign Deal", client_id=other_client.id, stage_id=stage.id, responsible_user_id=admin.id)
        archived_deal = Deal(name="P1.7 archived Deal", client_id=client.id, stage_id=stage.id, responsible_user_id=admin.id, archived_at=utc_now())
        session.add_all([other_deal, archived_deal]); session.flush()
        external = _message(connection, IntegrationProvider.TELEGRAM, client_id=client.id, communication_id=communication.id, content="P1.7 inbound")
        session.add(external); session.commit()
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: admin
        try:
            summary = _request("GET", "/communications/incoming-summary")
            listed = _request("GET", f"/communications?client_id={communication.client_id}")
            foreign = _request("POST", f"/communications/{communication.id}/assign-deal?deal_id={other_deal.id}")
            archived = _request("POST", f"/communications/{communication.id}/assign-deal?deal_id={archived_deal.id}")
            assigned = _request("POST", f"/communications/{communication.id}/assign-deal?deal_id={deal_b.id}")
            marked = _request("POST", f"/communications/{communication.id}/read")
            marked_again = _request("POST", f"/communications/{communication.id}/read")
            detached = _request("POST", f"/communications/{communication.id}/detach-deal")
        finally:
            app.dependency_overrides.clear()
        fresh = session.get(Communication, communication.id)
        linked = session.get(ExternalMessage, external.id)
        assert summary.status_code == 200, summary.text
        assert listed.status_code == 200 and listed.json()[0]["read_at"] is None
        assert foreign.status_code == archived.status_code == 422
        assert assigned.status_code == 200, assigned.text
        assert marked.status_code == 200, marked.text
        assert marked_again.status_code == 200 and marked_again.json()["read_at"] == marked.json()["read_at"]
        assert detached.status_code == 200, detached.text
        assert summary.json()["unread_count"] == 1 and summary.json()["clients"][0]["client_id"] == str(client.id)
        assert marked.json()["read_at"] is not None
        assert fresh.client_id == client.id and fresh.deal_id is None and fresh.read_at is not None
        assert linked.client_id == client.id and linked.deal_id is None


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_inbox_telegram_deal_link_conflicts_and_archived_targets_are_atomic(isolated_database):
    with isolated_database() as session:
        admin = User(email="p16-conflict-admin@example.test", password_hash="x", display_name="Admin", role=UserRole.ADMIN, is_active=True)
        other = User(email="p16-other-manager@example.test", password_hash="x", display_name="Other", role=UserRole.MANAGER, is_active=True)
        target = Client(name="P1.6 target", telegram_provider_user_id="different-target-id")
        owner = Client(name="P1.6 identity owner", telegram_provider_user_id="owned-sender-id")
        stage = PipelineStage(name="P1.6 Active Conflict", position=92)
        telegram = IntegrationConnection(provider=IntegrationProvider.TELEGRAM, status=IntegrationConnectionStatus.CONNECTED, display_name="Telegram")
        session.add_all([admin, other, target, owner, stage, telegram]); session.flush()
        deal = Deal(name="P1.6 conflict Deal", client_id=target.id, stage_id=stage.id, responsible_user_id=admin.id)
        archived = Deal(name="P1.6 archived Deal", client_id=target.id, stage_id=stage.id, responsible_user_id=admin.id, archived_at=utc_now())
        session.add_all([deal, archived]); session.flush()
        target_conflict = _message(telegram, IntegrationProvider.TELEGRAM, offset=21)
        owner_conflict = _message(telegram, IntegrationProvider.TELEGRAM, offset=22); owner_conflict.sender_identifier = owner.telegram_provider_user_id
        archived_message = _message(telegram, IntegrationProvider.TELEGRAM, offset=23)
        forbidden_message = _message(telegram, IntegrationProvider.TELEGRAM, offset=24)
        session.add_all([target_conflict, owner_conflict, archived_message, forbidden_message]); session.commit()
        app.dependency_overrides[get_db] = lambda: session
        try:
            app.dependency_overrides[get_current_user] = lambda: admin
            target_response = _request("POST", f"/inbox/external-messages/{target_conflict.id}/link", {"deal_id": str(deal.id)})
            owner_response = _request("POST", f"/inbox/external-messages/{owner_conflict.id}/link", {"deal_id": str(deal.id)})
            archived_response = _request("POST", f"/inbox/external-messages/{archived_message.id}/link", {"deal_id": str(archived.id)})
            app.dependency_overrides[get_current_user] = lambda: other
            forbidden_response = _request("POST", f"/inbox/external-messages/{forbidden_message.id}/link", {"deal_id": str(deal.id)})
        finally:
            app.dependency_overrides.clear()
        assert [item.status_code for item in (target_response, owner_response, archived_response, forbidden_response)] == [422, 422, 422, 422]
        for message in (target_conflict, owner_conflict, archived_message, forbidden_message):
            fresh = session.get(ExternalMessage, message.id)
            assert fresh.client_id is None and fresh.deal_id is None and fresh.communication_id is None
        assert target.telegram_provider_user_id == "different-target-id"
        assert owner.telegram_provider_user_id == "owned-sender-id"
        assert session.scalar(select(func.count()).select_from(Communication)) == 0
