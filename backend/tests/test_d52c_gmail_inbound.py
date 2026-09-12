import base64
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from backend.app.models import Client, Communication, CommunicationChannel, CommunicationDirection, Deal, ExternalMessage, ExternalMessageStatus, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, PipelineStage, User, UserRole
from backend.app.services.gmail_inbound import SYNC_LOOKBACK, process_gmail_inbound_message
from backend.app.services.integrations_adapters import GmailInboundMessage, GmailMessagePage, _parse_gmail_inbound_payload
from backend.app.services.gmail_inbound_lock import GMAIL_INBOUND_SYNC_LOCK_KEY, GMAIL_INBOUND_SYNC_LOCK_TTL_SECONDS, acquire_gmail_inbound_sync_lock, release_gmail_inbound_sync_lock
from backend.app.workers import integration_tasks
from backend.app.workers.celery_app import celery_app
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


def _client(session, *, name, email):
    client = Client(name=name, email=email)
    session.add(client)
    session.flush()
    return client


def _deal(session, *, name, client, stage, admin):
    deal = Deal(name=name, client_id=client.id, stage_id=stage.id, responsible_user_id=admin.id)
    session.add(deal)
    session.flush()
    return deal


def _outbound(session, *, connection, provider_message_id, thread, client, deal=None, status=ExternalMessageStatus.SENT, provider=IntegrationProvider.GMAIL, direction="OUTGOING"):
    message = ExternalMessage(integration_connection_id=connection.id, provider=provider, provider_message_id=provider_message_id, provider_thread_id=thread, client_id=client.id, deal_id=deal.id if deal else None, direction=direction, status=status, sender_identifier="corporate@example.test", recipient_identifier=client.email or "client@example.test", content="synthetic")
    session.add(message)
    session.commit()
    return message


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_inbound_exact_matching_thread_correlation_and_deduplication(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        first = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound())
        assert first.status is ExternalMessageStatus.RECEIVED and first.client_id == records.client.id and first.deal_id == records.deal.id
        assert first.communication_id is not None
        communication = session.get(Communication, first.communication_id)
        assert communication.channel is CommunicationChannel.EMAIL and communication.direction is CommunicationDirection.INCOMING and communication.content == "synthetic inbound body" and communication.read_at is None
        repeated = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound())
        assert repeated.id == first.id
        assert len(list(session.scalars(select(ExternalMessage).where(ExternalMessage.direction == "INCOMING")))) == 1
        assert len(list(session.scalars(select(Communication)))) == 1


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_inbound_unmatched_and_ambiguous_thread_remain_safe(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        unmatched = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="unmatched", sender="nobody@example.test", thread=None))
        assert unmatched.client_id is None and unmatched.deal_id is None and unmatched.communication_id is None
        second_deal = Deal(name="D52c second", client_id=records.client.id, stage_id=records.deal.stage_id, responsible_user_id=records.admin.id)
        session.add(second_deal); session.flush()
        session.add(ExternalMessage(integration_connection_id=records.connection.id, provider=IntegrationProvider.GMAIL, provider_message_id="outbound-2", provider_thread_id="known-thread", client_id=records.client.id, deal_id=second_deal.id, direction="OUTGOING", status=ExternalMessageStatus.SENT, sender_identifier="corporate@example.test", recipient_identifier="client@example.test", content="sent")); session.commit()
        ambiguous = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="ambiguous"))
        assert ambiguous.client_id == records.client.id and ambiguous.deal_id is None and ambiguous.communication_id is not None


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_same_thread_fallback_remains_idempotent_with_unique_email_identity(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        first = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="fallback-unique", sender="unknown@example.test", thread="known-thread"))
        assert first.client_id == records.client.id and first.deal_id == records.deal.id and first.communication_id is not None
        repeated = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="fallback-unique", sender="unknown@example.test", thread="known-thread"))
        assert repeated.id == first.id
        assert len(list(session.scalars(select(Communication).where(Communication.direction == CommunicationDirection.INCOMING)))) == 1


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_zero_email_matches_use_one_same_thread_sent_client_and_deal(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        message = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="fallback-zero", sender="unknown@example.test", thread="known-thread"))
        assert message.client_id == records.client.id and message.deal_id == records.deal.id and message.communication_id is not None


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_ambiguous_thread_or_absent_trusted_outbound_evidence_remains_unmatched(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        other = _client(session, name="Other", email="other@example.test")
        other_deal = _deal(session, name="Other deal", client=other, stage=records.deal.stage, admin=records.admin)
        _outbound(session, connection=records.connection, provider_message_id="other-thread-message", thread="known-thread", client=other, deal=other_deal)
        ambiguous = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="ambiguous-clients", sender="unknown@example.test", thread="known-thread"))
        no_thread = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="missing-thread", sender="unknown@example.test", thread=None))
        no_outbound = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="no-outbound", sender="unknown@example.test", thread="no-outbound-thread"))
        assert all(message.client_id is None and message.deal_id is None and message.communication_id is None for message in (ambiguous, no_thread, no_outbound))


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_wrong_connection_provider_and_non_sent_outbound_are_not_fallback_candidates(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        other_connection = IntegrationConnection(provider=IntegrationProvider.TELEGRAM, status=IntegrationConnectionStatus.CONNECTED, display_name="Telegram")
        session.add(other_connection); session.flush()
        _outbound(session, connection=other_connection, provider_message_id="wrong-connection", thread="wrong-connection-thread", client=records.client, deal=records.deal)
        _outbound(session, connection=records.connection, provider_message_id="wrong-provider", thread="wrong-provider-thread", client=records.client, deal=records.deal, provider=IntegrationProvider.TELEGRAM)
        _outbound(session, connection=records.connection, provider_message_id="pending", thread="pending-thread", client=records.client, deal=records.deal, status=ExternalMessageStatus.PENDING)
        _outbound(session, connection=records.connection, provider_message_id="incoming", thread="incoming-thread", client=records.client, deal=records.deal, direction="INCOMING", status=ExternalMessageStatus.RECEIVED)
        messages = [process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id=f"not-candidate-{index}", sender="unknown@example.test", thread=thread)) for index, thread in enumerate(("wrong-connection-thread", "wrong-provider-thread", "pending-thread", "incoming-thread"))]
        assert all(message.client_id is None and message.deal_id is None and message.communication_id is None for message in messages)


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_unique_email_is_not_overridden_and_fallback_client_with_ambiguous_deals_stays_client_level(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        other = _client(session, name="Other", email="other@example.test")
        other_deal = _deal(session, name="Other deal", client=other, stage=records.deal.stage, admin=records.admin)
        _outbound(session, connection=records.connection, provider_message_id="conflict", thread="conflict-thread", client=other, deal=other_deal)
        primary = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="unique-primary", sender=records.client.email, thread="conflict-thread"))
        assert primary.client_id == records.client.id and primary.deal_id is None and primary.communication_id is not None

        second_deal = _deal(session, name="Second deal", client=records.client, stage=records.deal.stage, admin=records.admin)
        _outbound(session, connection=records.connection, provider_message_id="same-client-second-deal", thread="known-thread", client=records.client, deal=second_deal)
        fallback = process_gmail_inbound_message(session, connection=records.connection, inbound=_inbound(message_id="fallback-ambiguous-deal", sender=records.client.email, thread="known-thread"))
        assert fallback.client_id == records.client.id and fallback.deal_id is None and fallback.communication_id is not None


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


class _FakeRedis:
    values = {}
    calls = []

    def set(self, key, value, *, nx, ex):
        self.calls.append((key, nx, ex))
        if key in self.values:
            return False
        self.values[key] = value
        return True

    def eval(self, _script, _keys, key, token):
        if self.values.get(key) == token:
            del self.values[key]
            return 1
        return 0

    def close(self):
        return None


@contextmanager
def _session_context(value):
    yield value


def test_periodic_gmail_schedule_is_registered_for_integrations_every_60_seconds():
    schedule = celery_app.conf.beat_schedule["gmail-inbound-sync-every-60-seconds"]
    assert schedule == {"task": "integrations.gmail.periodic_dispatch", "schedule": 60.0, "options": {"queue": "integrations"}}


def test_periodic_dispatch_uses_existing_inbound_task_and_skips_unavailable(monkeypatch):
    connection = SimpleNamespace(id="safe-integration-id")
    dispatched = []
    monkeypatch.setattr(integration_tasks, "SessionLocal", lambda: _session_context(object()))
    monkeypatch.setattr(integration_tasks, "get_usable_gmail_inbound_connection", lambda _: connection)
    monkeypatch.setattr(integration_tasks.sync_gmail_inbound, "delay", lambda **kwargs: dispatched.append(kwargs))
    assert integration_tasks.dispatch_periodic_gmail_inbound_sync() == {"dispatched": True}
    assert dispatched == [{"trigger": "periodic"}]

    monkeypatch.setattr(integration_tasks, "get_usable_gmail_inbound_connection", lambda _: (_ for _ in ()).throw(gmail_inbound.GmailInboundError(gmail_inbound.ProviderErrorCode.AUTH_REQUIRED)))
    assert integration_tasks.dispatch_periodic_gmail_inbound_sync() == {"dispatched": False, "reason": "unavailable"}
    assert dispatched == [{"trigger": "periodic"}]


def test_gmail_redis_lock_owner_release_and_bounded_stale_recovery(monkeypatch):
    _FakeRedis.values = {}
    _FakeRedis.calls = []
    monkeypatch.setattr("backend.app.services.gmail_inbound_lock.redis.Redis.from_url", lambda *_args, **_kwargs: _FakeRedis())
    first = acquire_gmail_inbound_sync_lock()
    assert first is not None
    assert _FakeRedis.calls == [(GMAIL_INBOUND_SYNC_LOCK_KEY, True, GMAIL_INBOUND_SYNC_LOCK_TTL_SECONDS)]
    assert acquire_gmail_inbound_sync_lock() is None
    release_gmail_inbound_sync_lock(first)
    assert acquire_gmail_inbound_sync_lock() is not None
    # Redis expiry is the bounded recovery mechanism after a worker crash.
    _FakeRedis.values.clear()
    assert acquire_gmail_inbound_sync_lock() is not None


def test_periodic_and_manual_tasks_share_single_flight_lock_and_release_after_terminal_result(monkeypatch):
    connection = SimpleNamespace(id="safe-integration-id")
    lock = object()
    released = []
    executed = []
    monkeypatch.setattr(integration_tasks, "SessionLocal", lambda: _session_context(object()))
    monkeypatch.setattr(integration_tasks, "acquire_gmail_inbound_sync_lock", lambda: lock)
    monkeypatch.setattr(integration_tasks, "release_gmail_inbound_sync_lock", lambda value: released.append(value))
    monkeypatch.setattr(integration_tasks, "request_gmail_inbound_sync", lambda _: connection)
    monkeypatch.setattr(integration_tasks, "execute_gmail_inbound_sync", lambda _: executed.append(1) or {"initialized": False, "processed": 1, "has_more": False})
    assert integration_tasks.sync_gmail_inbound(trigger="periodic") == {"initialized": False, "processed": 1, "has_more": False}
    assert executed == [1] and released == [lock]

    monkeypatch.setattr(integration_tasks, "acquire_gmail_inbound_sync_lock", lambda: None)
    assert integration_tasks.sync_gmail_inbound(trigger="manual") == {"skipped": "overlap"}
    assert integration_tasks.sync_gmail_inbound(trigger="periodic") == {"skipped": "overlap"}
    assert executed == [1]


def test_gmail_sync_lock_releases_after_error_without_celery_autoretry(monkeypatch):
    connection = SimpleNamespace(id="safe-integration-id")
    lock = object()
    released = []
    calls = []
    monkeypatch.setattr(integration_tasks, "SessionLocal", lambda: _session_context(object()))
    monkeypatch.setattr(integration_tasks, "acquire_gmail_inbound_sync_lock", lambda: lock)
    monkeypatch.setattr(integration_tasks, "release_gmail_inbound_sync_lock", lambda value: released.append(value))
    monkeypatch.setattr(integration_tasks, "request_gmail_inbound_sync", lambda _: connection)
    monkeypatch.setattr(integration_tasks, "execute_gmail_inbound_sync", lambda _: calls.append(1) or {"initialized": False, "processed": 0, "error": "PROVIDER_UNAVAILABLE"})
    assert integration_tasks.sync_gmail_inbound(trigger="manual")["error"] == "PROVIDER_UNAVAILABLE"
    assert calls == [1] and released == [lock]
    assert not hasattr(integration_tasks.sync_gmail_inbound, "autoretry_for")
