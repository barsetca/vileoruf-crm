import asyncio
import os
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.app.api.integrations import telegram_webhook as telegram_webhook_module
from backend.app.api.integrations import router as integrations_router
from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Client, Communication, Deal, ExternalMessage, ExternalMessageStatus, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, PipelineStage, User, UserRole
from backend.app.services import telegram
from backend.app.services.integrations_adapters import GmailAdapterError, ProviderErrorCode, RetryClass, TelegramSendResult
from backend.tests.test_d52a_google_oauth import isolated_database


def _records(session):
    admin=User(email="d53-admin@example.test",password_hash="x",display_name="Admin",role=UserRole.ADMIN,is_active=True)
    client=Client(name="Telegram client",telegram_provider_user_id="1001")
    stage=PipelineStage(name="D53 stage",position=93)
    connection=IntegrationConnection(provider=IntegrationProvider.TELEGRAM,status=IntegrationConnectionStatus.CONNECTED,display_name="Telegram",external_account_id="bot")
    session.add_all([admin,client,stage,connection]); session.commit(); return SimpleNamespace(admin=admin,client=client,stage=stage,connection=connection)


def _update(update_id=9001, user_id=1001, text="synthetic telegram", username="not-authoritative"):
    return {"update_id":update_id,"message":{"message_id":7,"text":text,"from":{"id":user_id,"username":username},"chat":{"id":user_id,"type":"private"}}}


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")
def test_inbound_exact_match_unmatched_link_and_dedup(isolated_database):
    with isolated_database() as session:
        r=_records(session)
        first=telegram.process_telegram_update(session,_update())
        assert first.status is ExternalMessageStatus.RECEIVED and first.client_id==r.client.id and first.communication_id
        assert telegram.process_telegram_update(session,_update()).id==first.id
        assert len(list(session.scalars(select(Communication))))==1
        unmatched=telegram.process_telegram_update(session,_update(9002,2002))
        assert unmatched.client_id is None and unmatched.communication_id is None
        target=Client(name="Link target"); session.add(target); session.commit()
        linked=telegram.link_telegram_message(session,external_message_id=unmatched.id,client_id=target.id,current_user=r.admin)
        assert linked.client_id==target.id and linked.communication_id and target.telegram_provider_user_id=="2002"
        assert telegram.link_telegram_message(session,external_message_id=unmatched.id,client_id=target.id,current_user=r.admin).id==unmatched.id
        assert len(list(session.scalars(select(Communication))))==2


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")
def test_outbound_confirmed_failure_and_unknown(isolated_database,monkeypatch):
    with isolated_database() as session:
        r=_records(session)
        monkeypatch.setattr(telegram,"get_telegram_settings",lambda:SimpleNamespace(telegram_bot_token=SimpleNamespace(get_secret_value=lambda:"fake")))
        monkeypatch.setattr(telegram,"send_telegram_message",lambda **_:TelegramSendResult(provider_message_id="provider",chat_id="1001"))
        pending, _=telegram.request_telegram_send(session,client_id=r.client.id,deal_id=None,content="outbound",idempotency_key="existing-test-request-key",current_user=r.admin)
        sent=telegram.execute_telegram_send(session,external_message_id=pending.id)
        assert sent.status is ExternalMessageStatus.SENT and sent.communication_id
        assert telegram.execute_telegram_send(session,external_message_id=pending.id).id==sent.id
        assert len(list(session.scalars(select(Communication))))==1


def _webhook_update():
    return {"update_id": 99001, "message": {"message_id": 81, "text": "synthetic direct message", "from": {"id": 70001}, "chat": {"id": 70001, "type": "private"}}}


def _post_webhook(headers=None):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/webhooks/telegram", json=_webhook_update(), headers=headers)
    return asyncio.run(send())


def _post_telegram_link(external_message_id, client_id):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post(f"/settings/integrations/telegram/messages/{external_message_id}/link", json={"client_id": str(client_id)})
    return asyncio.run(send())


def _post_telegram_send(payload, request_key="synthetic-default-request-key"):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/settings/integrations/telegram/messages", json=payload, headers={"Idempotency-Key": request_key})
    return asyncio.run(send())


def _write_counts(session):
    return tuple(session.scalar(select(func.count()).select_from(model)) for model in (ExternalMessage, Communication, Client))


def _synthetic_webhook_settings():
    return SimpleNamespace(telegram_webhook_secret=SecretStr("synthetic-correct-webhook-secret"))


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_webhook_missing_secret_rejects_before_any_crm_write(isolated_database, monkeypatch):
    with isolated_database() as session:
        dispatched = False
        def process(*_args):
            nonlocal dispatched
            dispatched = True
        monkeypatch.setattr(telegram_webhook_module, "get_telegram_settings", _synthetic_webhook_settings)
        monkeypatch.setattr(telegram_webhook_module, "process_telegram_update", process)
        app.dependency_overrides[get_db] = lambda: session
        try:
            response = _post_webhook()
        finally:
            app.dependency_overrides.clear()
        assert response.status_code == 401
        assert "synthetic-correct-webhook-secret" not in response.text
        assert dispatched is False
        assert _write_counts(session) == (0, 0, 0)


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_webhook_wrong_secret_rejects_before_any_crm_write(isolated_database, monkeypatch):
    with isolated_database() as session:
        dispatched = False
        def process(*_args):
            nonlocal dispatched
            dispatched = True
        monkeypatch.setattr(telegram_webhook_module, "get_telegram_settings", _synthetic_webhook_settings)
        monkeypatch.setattr(telegram_webhook_module, "process_telegram_update", process)
        app.dependency_overrides[get_db] = lambda: session
        try:
            response = _post_webhook({"X-Telegram-Bot-Api-Secret-Token": "synthetic-wrong-webhook-secret"})
        finally:
            app.dependency_overrides.clear()
        assert response.status_code == 401
        assert "synthetic-correct-webhook-secret" not in response.text
        assert dispatched is False
        assert _write_counts(session) == (0, 0, 0)


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_webhook_correct_synthetic_secret_reaches_inbound_dispatch_boundary(isolated_database, monkeypatch):
    with isolated_database() as session:
        dispatched = []
        def process(received_session, payload):
            dispatched.append((received_session, payload))
            return None
        monkeypatch.setattr(telegram_webhook_module, "get_telegram_settings", _synthetic_webhook_settings)
        monkeypatch.setattr(telegram_webhook_module, "process_telegram_update", process)
        app.dependency_overrides[get_db] = lambda: session
        try:
            response = _post_webhook({"X-Telegram-Bot-Api-Secret-Token": "synthetic-correct-webhook-secret"})
        finally:
            app.dependency_overrides.clear()
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert dispatched == [(session, _webhook_update())]
        assert _write_counts(session) == (0, 0, 0)


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_webhook_repeated_matched_provider_update_creates_one_message_and_communication(isolated_database, monkeypatch):
    with isolated_database() as session:
        records = _records(session)
        client = Client(name="Webhook idempotency client", telegram_provider_user_id="70001")
        session.add(client)
        session.commit()
        monkeypatch.setattr(telegram_webhook_module, "get_telegram_settings", _synthetic_webhook_settings)
        app.dependency_overrides[get_db] = lambda: session
        try:
            first_response = _post_webhook({"X-Telegram-Bot-Api-Secret-Token": "synthetic-correct-webhook-secret"})
            second_response = _post_webhook({"X-Telegram-Bot-Api-Secret-Token": "synthetic-correct-webhook-secret"})
        finally:
            app.dependency_overrides.clear()
        assert first_response.status_code == second_response.status_code == 200
        messages = list(session.scalars(select(ExternalMessage).where(ExternalMessage.integration_connection_id == records.connection.id, ExternalMessage.provider_message_id == "99001")))
        communications = list(session.scalars(select(Communication).where(Communication.client_id == client.id, Communication.channel == "TELEGRAM", Communication.direction == "INCOMING")))
        assert len(messages) == 1
        assert len(communications) == 1
        assert messages[0].communication_id == communications[0].id
        assert telegram.process_telegram_update(session, _webhook_update()).id == messages[0].id
        assert len(list(session.scalars(select(ExternalMessage).where(ExternalMessage.integration_connection_id == records.connection.id, ExternalMessage.provider_message_id == "99001")))) == 1
        assert len(list(session.scalars(select(Communication).where(Communication.client_id == client.id, Communication.channel == "TELEGRAM", Communication.direction == "INCOMING")))) == 1
        assert session.get(Client, client.id).telegram_provider_user_id == "70001"


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_inbound_matching_uses_only_stable_provider_user_id_without_deal_inference(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        session.add_all([
            Deal(name="Matching context deal", client_id=records.client.id, stage_id=records.stage.id, responsible_user_id=records.admin.id),
            Client(name="Username-only client", telegram="same-synthetic-username", telegram_provider_user_id="different-stable-id"),
        ])
        session.commit()
        initial_client_count = session.scalar(select(func.count()).select_from(Client))

        exact = telegram.process_telegram_update(session, _update(93001, 1001, "exact stable match", "same-synthetic-username"))
        zero_match = telegram.process_telegram_update(session, _update(93002, 2002, "zero match", "unmatched-username"))
        username_only = telegram.process_telegram_update(session, _update(93003, 3003, "username is ignored", "same-synthetic-username"))

        assert exact.status is ExternalMessageStatus.RECEIVED
        assert exact.client_id == records.client.id and exact.deal_id is None and exact.communication_id is not None
        assert session.get(Communication, exact.communication_id).client_id == records.client.id
        assert zero_match.status is ExternalMessageStatus.RECEIVED
        assert zero_match.client_id is None and zero_match.deal_id is None and zero_match.communication_id is None
        assert username_only.status is ExternalMessageStatus.RECEIVED
        assert username_only.client_id is None and username_only.deal_id is None and username_only.communication_id is None
        assert session.scalar(select(func.count()).select_from(Client)) == initial_client_count
        assert len(list(session.scalars(select(Communication).where(Communication.channel == "TELEGRAM", Communication.direction == "INCOMING")))) == 1

        session.add(Client(name="Duplicate stable identity", telegram_provider_user_id="1001"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_manual_unmatched_link_api_preserves_identity_and_history(isolated_database):
    with isolated_database() as session:
        records = _records(session)
        selected = Client(name="Selected link client")
        other = Client(name="Other link client")
        conflicting = Client(name="Conflicting link client", telegram_provider_user_id="different-provider-id")
        session.add_all([selected, other, conflicting])
        session.commit()
        initial_client_count = session.scalar(select(func.count()).select_from(Client))
        unmatched = telegram.process_telegram_update(session, _update(94001, 4001, "accepted unmatched content"))
        invalid_target = telegram.process_telegram_update(session, _update(94002, 4002, "invalid target content"))
        conflicting_target = telegram.process_telegram_update(session, _update(94003, 4003, "conflicting target content"))
        assert unmatched.status is ExternalMessageStatus.RECEIVED
        assert unmatched.client_id is None and unmatched.deal_id is None and unmatched.communication_id is None
        assert len(list(session.scalars(select(Communication)))) == 0

        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: records.admin
        try:
            linked_response = _post_telegram_link(unmatched.id, selected.id)
            repeated_response = _post_telegram_link(unmatched.id, selected.id)
            relink_response = _post_telegram_link(unmatched.id, other.id)
            invalid_response = _post_telegram_link(invalid_target.id, "00000000-0000-0000-0000-000000000000")
            conflict_response = _post_telegram_link(conflicting_target.id, conflicting.id)
        finally:
            app.dependency_overrides.clear()

        assert linked_response.status_code == repeated_response.status_code == relink_response.status_code == 200
        linked = session.get(ExternalMessage, unmatched.id)
        communication = session.get(Communication, linked.communication_id)
        assert linked.client_id == selected.id and linked.deal_id is None and linked.communication_id is not None
        assert communication.client_id == selected.id and communication.channel == "TELEGRAM" and communication.direction == "INCOMING"
        assert communication.content == "accepted unmatched content"
        assert session.get(Client, selected.id).telegram_provider_user_id == "4001"
        assert len(list(session.scalars(select(Communication).where(Communication.client_id == selected.id)))) == 1
        assert session.get(ExternalMessage, unmatched.id).client_id == selected.id

        assert invalid_response.status_code == conflict_response.status_code == 422
        assert session.get(ExternalMessage, invalid_target.id).client_id is None and session.get(ExternalMessage, invalid_target.id).communication_id is None
        assert session.get(ExternalMessage, conflicting_target.id).client_id is None and session.get(ExternalMessage, conflicting_target.id).communication_id is None
        assert session.get(Client, conflicting.id).telegram_provider_user_id == "different-provider-id"
        assert session.scalar(select(func.count()).select_from(Client)) == initial_client_count

        app.dependency_overrides[get_db] = lambda: session
        try:
            unauthenticated_response = _post_telegram_link(invalid_target.id, selected.id)
        finally:
            app.dependency_overrides.clear()
        assert unauthenticated_response.status_code == 401
        assert session.get(ExternalMessage, invalid_target.id).client_id is None and session.get(ExternalMessage, invalid_target.id).communication_id is None


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_outbound_send_api_authorizes_and_validates_before_provider_execution(isolated_database, monkeypatch):
    with isolated_database() as session:
        records = _records(session)
        manager = User(email="d53-manager@example.test", password_hash="x", display_name="Manager", role=UserRole.MANAGER, is_active=True)
        no_recipient = Client(name="No Telegram recipient")
        other_client = Client(name="Other Telegram client", telegram_provider_user_id="other-provider-id")
        session.add_all([manager, no_recipient, other_client])
        session.flush()
        owned_deal = Deal(name="Owned Telegram deal", client_id=records.client.id, stage_id=records.stage.id, responsible_user_id=manager.id)
        foreign_deal = Deal(name="Foreign Telegram deal", client_id=other_client.id, stage_id=records.stage.id, responsible_user_id=records.admin.id)
        session.add_all([owned_deal, foreign_deal])
        session.commit()
        dispatched = []
        monkeypatch.setattr(integrations_router, "send_telegram_external_message", SimpleNamespace(delay=lambda external_message_id: dispatched.append(external_message_id)))

        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: manager
        try:
            client_response = _post_telegram_send({"client_id": str(records.client.id), "content": "synthetic client-level send"}, "pre-provider-client-key")
            deal_response = _post_telegram_send({"client_id": str(records.client.id), "deal_id": str(owned_deal.id), "content": "synthetic deal-level send"}, "pre-provider-deal-key")
            foreign_response = _post_telegram_send({"client_id": str(other_client.id), "deal_id": str(foreign_deal.id), "content": "foreign deal send"}, "pre-provider-foreign-key")
            mismatch_response = _post_telegram_send({"client_id": str(records.client.id), "deal_id": str(foreign_deal.id), "content": "mismatched context send"}, "pre-provider-mismatch-key")
            recipient_response = _post_telegram_send({"client_id": str(no_recipient.id), "content": "missing recipient send"}, "pre-provider-recipient-key")
        finally:
            app.dependency_overrides.clear()

        assert client_response.status_code == deal_response.status_code == 202
        assert foreign_response.status_code == 403
        assert mismatch_response.status_code == recipient_response.status_code == 422
        messages = list(session.scalars(select(ExternalMessage).where(ExternalMessage.direction == "OUTGOING")))
        assert len(messages) == len(dispatched) == 2
        assert {message.status for message in messages} == {ExternalMessageStatus.PENDING}
        assert {(message.client_id, message.deal_id) for message in messages} == {(records.client.id, None), (records.client.id, owned_deal.id)}
        assert len(list(session.scalars(select(Communication).where(Communication.channel == "TELEGRAM", Communication.direction == "OUTGOING")))) == 0

        records.connection.status = IntegrationConnectionStatus.DISCONNECTED
        session.commit()
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: manager
        try:
            unavailable_response = _post_telegram_send({"client_id": str(records.client.id), "content": "unavailable integration send"}, "pre-provider-unavailable-key")
            invalid_payload_response = _post_telegram_send({"client_id": str(records.client.id), "content": "   "}, "pre-provider-invalid-key")
        finally:
            app.dependency_overrides.clear()
        assert unavailable_response.status_code == invalid_payload_response.status_code == 422
        assert len(dispatched) == 2
        assert len(list(session.scalars(select(ExternalMessage).where(ExternalMessage.direction == "OUTGOING")))) == 2

        app.dependency_overrides[get_db] = lambda: session
        try:
            unauthenticated_response = _post_telegram_send({"client_id": str(records.client.id), "content": "unauthenticated send"}, "pre-provider-unauthenticated-key")
        finally:
            app.dependency_overrides.clear()
        assert unauthenticated_response.status_code == 401
        assert len(dispatched) == 2
        assert len(list(session.scalars(select(Communication).where(Communication.channel == "TELEGRAM", Communication.direction == "OUTGOING")))) == 0


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_outbound_send_api_idempotency_key_is_persisted_and_authorization_safe(isolated_database, monkeypatch):
    with isolated_database() as session:
        records = _records(session)
        manager = User(email="idempotency-manager@example.test", password_hash="x", display_name="Manager", role=UserRole.MANAGER, is_active=True)
        session.add(manager)
        session.flush()
        admin_deal = Deal(name="Admin idempotency deal", client_id=records.client.id, stage_id=records.stage.id, responsible_user_id=records.admin.id)
        session.add(admin_deal)
        session.commit()
        dispatched = []
        monkeypatch.setattr(integrations_router, "send_telegram_external_message", SimpleNamespace(delay=lambda external_message_id: dispatched.append(external_message_id)))
        payload = {"client_id": str(records.client.id), "deal_id": str(admin_deal.id), "content": "synthetic idempotent send"}
        key = "synthetic-idempotency-key-k"

        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: records.admin
        try:
            first_response = _post_telegram_send(payload, key)
            repeated_response = _post_telegram_send(payload, key)
            conflict_response = _post_telegram_send({**payload, "content": "changed synthetic content"}, key)
            second_response = _post_telegram_send(payload, "synthetic-idempotency-key-k2")
        finally:
            app.dependency_overrides.clear()

        assert first_response.status_code == repeated_response.status_code == second_response.status_code == 202
        assert conflict_response.status_code == 409
        assert first_response.json()["external_message_id"] == repeated_response.json()["external_message_id"]
        messages = list(session.scalars(select(ExternalMessage).where(ExternalMessage.direction == "OUTGOING")))
        assert len(messages) == len(dispatched) == 2
        assert {message.status for message in messages} == {ExternalMessageStatus.PENDING}
        assert {message.idempotency_key for message in messages} == {key, "synthetic-idempotency-key-k2"}
        assert len(list(session.scalars(select(Communication).where(Communication.channel == "TELEGRAM", Communication.direction == "OUTGOING")))) == 0

        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: manager
        try:
            foreign_reuse_response = _post_telegram_send(payload, key)
        finally:
            app.dependency_overrides.clear()
        assert foreign_reuse_response.status_code == 403
        assert len(dispatched) == 2
        assert len(list(session.scalars(select(ExternalMessage).where(ExternalMessage.direction == "OUTGOING")))) == 2


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_outbound_provider_finalization_success_failed_unknown_and_no_blind_resend(isolated_database, monkeypatch):
    with isolated_database() as session:
        records = _records(session)
        deal = Deal(name="Telegram finalization deal", client_id=records.client.id, stage_id=records.stage.id, responsible_user_id=records.admin.id)
        session.add(deal)
        session.commit()
        monkeypatch.setattr(telegram, "get_telegram_settings", lambda: SimpleNamespace(telegram_bot_token=SimpleNamespace(get_secret_value=lambda: "synthetic-token")))
        calls = []

        success_pending, _ = telegram.request_telegram_send(session, client_id=records.client.id, deal_id=deal.id, content="actual synthetic success content", idempotency_key="finalization-success-key", current_user=records.admin)
        assert len(list(session.scalars(select(Communication).where(Communication.direction == "OUTGOING")))) == 0
        monkeypatch.setattr(telegram, "send_telegram_message", lambda **kwargs: calls.append(kwargs) or TelegramSendResult(provider_message_id="synthetic-provider-message", chat_id="1001"))
        sent = telegram.execute_telegram_send(session, external_message_id=success_pending.id)
        assert sent.status is ExternalMessageStatus.SENT and sent.provider_message_id == "synthetic-provider-message" and sent.provider_thread_id == "1001"
        sent_communication = session.get(Communication, sent.communication_id)
        assert sent_communication.client_id == records.client.id and sent_communication.deal_id == deal.id
        assert sent_communication.channel == "TELEGRAM" and sent_communication.direction == "OUTGOING" and sent_communication.content == "actual synthetic success content"
        assert telegram.execute_telegram_send(session, external_message_id=success_pending.id).id == sent.id
        assert len(calls) == 1
        assert len(list(session.scalars(select(Communication).where(Communication.direction == "OUTGOING")))) == 1

        failed_pending, _ = telegram.request_telegram_send(session, client_id=records.client.id, deal_id=None, content="permanent failure content", idempotency_key="finalization-failed-key", current_user=records.admin)
        monkeypatch.setattr(telegram, "send_telegram_message", lambda **kwargs: calls.append(kwargs) or (_ for _ in ()).throw(GmailAdapterError(ProviderErrorCode.PERMISSION_DENIED, RetryClass.NO_RETRY)))
        failed = telegram.execute_telegram_send(session, external_message_id=failed_pending.id)
        assert failed.status is ExternalMessageStatus.FAILED and failed.last_error_code == ProviderErrorCode.PERMISSION_DENIED.value and failed.communication_id is None
        assert telegram.execute_telegram_send(session, external_message_id=failed_pending.id).id == failed.id
        assert len(calls) == 2

        unknown_pending, _ = telegram.request_telegram_send(session, client_id=records.client.id, deal_id=None, content="uncertain outcome content", idempotency_key="finalization-unknown-key", current_user=records.admin)
        monkeypatch.setattr(telegram, "send_telegram_message", lambda **kwargs: calls.append(kwargs) or (_ for _ in ()).throw(GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE, RetryClass.UNCERTAIN)))
        unknown = telegram.execute_telegram_send(session, external_message_id=unknown_pending.id)
        assert unknown.status is ExternalMessageStatus.UNKNOWN and unknown.last_error_code == ProviderErrorCode.PROVIDER_UNAVAILABLE.value and unknown.communication_id is None
        assert telegram.execute_telegram_send(session, external_message_id=unknown_pending.id).id == unknown.id
        assert len(calls) == 3
        assert len(list(session.scalars(select(Communication).where(Communication.channel == "TELEGRAM", Communication.direction == "OUTGOING")))) == 1
