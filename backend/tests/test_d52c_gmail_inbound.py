import base64
import os
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from backend.app.models import Client, Communication, CommunicationChannel, CommunicationDirection, Deal, ExternalMessage, ExternalMessageStatus, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, PipelineStage, User, UserRole
from backend.app.services.gmail_inbound import SYNC_LOOKBACK, process_gmail_inbound_message
from backend.app.services.integrations_adapters import GmailInboundMessage, GmailMessagePage, _parse_gmail_inbound_payload
import backend.app.services.gmail_inbound as gmail_inbound
from backend.tests.test_d52a_google_oauth import isolated_database


def _records(session):
    admin = User(email="d52c-admin@example.test", password_hash="synthetic", display_name="Admin", role=UserRole.ADMIN, is_active=True)
    client = Client(name="D52c client", email="client@example.test")
    stage = PipelineStage(name="D52c stage", position=92)
    session.add_all([admin, client, stage]); session.flush()
    deal = Deal(name="D52c deal", client_id=client.id, stage_id=stage.id, responsible_user_id=admin.id)
    connection = IntegrationConnection(provider=IntegrationProvider.GMAIL, status=IntegrationConnectionStatus.CONNECTED, display_name="Gmail", encrypted_token_payload="ciphertext")
    session.add_all([deal, connection]); session.flush()
    outbound = ExternalMessage(integration_connection_id=connection.id, provider=IntegrationProvider.GMAIL, provider_message_id="outbound-id", provider_thread_id="known-thread", client_id=client.id, deal_id=deal.id, direction="OUTGOING", status=ExternalMessageStatus.SENT, sender_identifier="corporate@example.test", recipient_identifier="client@example.test", subject="sent", content="sent")
    session.add(outbound); session.commit()
    return SimpleNamespace(admin=admin, client=client, deal=deal, connection=connection)


def _inbound(message_id="inbound-id", sender="client@example.test", thread="known-thread"):
    return GmailInboundMessage(provider_message_id=message_id, provider_thread_id=thread, sender=sender, recipient="corporate@example.test", subject="reply", content="synthetic inbound body", provider_created_at=datetime(2026, 9, 7, tzinfo=timezone.utc))


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_inbound_exact_matching_thread_correlation_and_deduplication(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        first = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound())
        assert first.status is ExternalMessageStatus.RECEIVED and first.client_id == records.client.id and first.deal_id == records.deal.id
        assert first.communication_id is not None
        communication = session.get(Communication, first.communication_id)
        assert communication.channel is CommunicationChannel.EMAIL and communication.direction is CommunicationDirection.INCOMING and communication.content == "synthetic inbound body"
        repeated = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound())
        assert repeated.id == first.id
        assert len(list(session.scalars(select(ExternalMessage).where(ExternalMessage.direction == "INCOMING")))) == 1
        assert len(list(session.scalars(select(Communication)))) == 1


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_inbound_unmatched_and_ambiguous_thread_remain_safe(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        unmatched = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="unmatched", sender="nobody@example.test"))
        assert unmatched.client_id is None and unmatched.deal_id is None and unmatched.communication_id is None
        second_deal = Deal(name="D52c second", client_id=records.client.id, stage_id=records.deal.stage_id, responsible_user_id=records.admin.id)
        session.add(second_deal); session.flush()
        session.add(ExternalMessage(integration_connection_id=records.connection.id, provider=IntegrationProvider.GMAIL, provider_message_id="outbound-2", provider_thread_id="known-thread", client_id=records.client.id, deal_id=second_deal.id, direction="OUTGOING", status=ExternalMessageStatus.SENT, sender_identifier="corporate@example.test", recipient_identifier="client@example.test", content="sent")); session.commit()
        ambiguous = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="ambiguous"))
        assert ambiguous.client_id == records.client.id and ambiguous.deal_id is None and ambiguous.communication_id is not None


def test_gmail_multipart_parser_prefers_plain_text():
    encoded = base64.urlsafe_b64encode(b"plain synthetic content").decode().rstrip("=")
    message = _parse_gmail_inbound_payload({"id": "provider-id", "threadId": "thread-id", "payload": {"headers": [{"name": "From", "value": "Sender <sender@example.test>"}, {"name": "To", "value": "corporate@example.test"}, {"name": "Subject", "value": "Synthetic"}, {"name": "Date", "value": "Mon, 07 Sep 2026 10:00:00 +0000"}], "mimeType": "multipart/alternative", "parts": [{"mimeType": "text/html", "body": {"data": base64.urlsafe_b64encode(b"<p>html</p>").decode().rstrip("=")}}, {"mimeType": "text/plain", "body": {"data": encoded}}]}})
    assert message.provider_message_id == "provider-id" and message.provider_thread_id == "thread-id"
    assert message.sender == "sender@example.test" and message.content == "plain synthetic content" and message.provider_created_at is not None


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_bounded_sync_initializes_then_processes_one_fake_page(isolated_database, monkeypatch):
    with isolated_database() as session:
        records = _records(session)
        first = gmail_inbound.execute_gmail_inbound_sync(session)
        assert first == {"initialized": True, "processed": 0}
        checkpoint = records.connection.inbound_sync_after
        captured = {}
        monkeypatch.setattr(gmail_inbound, "get_google_access_token", lambda session, connection: "synthetic-access")
        def list_page(**kwargs):
            captured.update(kwargs)
            return GmailMessagePage(message_ids=("incoming-page-id",), next_page_token=None)
        monkeypatch.setattr(gmail_inbound, "list_gmail_inbound_message_ids", list_page)
        monkeypatch.setattr(gmail_inbound, "get_gmail_inbound_message", lambda **kwargs: _inbound(message_id="incoming-page-id", thread=None))
        second = gmail_inbound.execute_gmail_inbound_sync(session)
        assert second == {"initialized": False, "processed": 1, "has_more": False}
        assert captured["after"] == checkpoint - SYNC_LOOKBACK
        connection = session.get(IntegrationConnection, records.connection.id)
        assert connection.inbound_sync_status == "IDLE" and connection.inbound_sync_page_token is None and connection.last_inbound_sync_at is not None
