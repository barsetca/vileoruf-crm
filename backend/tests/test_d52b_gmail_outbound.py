from types import SimpleNamespace

import pytest
from sqlalchemy import select

from backend.app.models import (
    AIResultLanguage,
    Client,
    Communication,
    EmailDraft,
    EmailDraftState,
    ExternalMessage,
    ExternalMessageStatus,
    IntegrationConnection,
    IntegrationConnectionStatus,
    IntegrationProvider,
    PipelineStage,
    Deal,
    User,
    UserRole,
)
from backend.app.services.gmail_outbound import (
    GmailOutboundForbiddenError,
    GmailOutboundValidationError,
    execute_gmail_send,
    request_gmail_send,
)
from backend.app.services.email_drafts import SentEmailDraftImmutableError, delete_email_draft, update_email_draft
from backend.app.services.integrations_adapters import GmailAdapterError, GmailSendResult, ProviderErrorCode, RetryClass
import backend.app.services.gmail_outbound as gmail_outbound
from backend.tests.test_d52a_google_oauth import isolated_database


def _records(session, *, email="recipient@example.test"):
    admin = User(email="d52b-admin@example.test", password_hash="synthetic", display_name="Admin", role=UserRole.ADMIN, is_active=True)
    manager = User(email="d52b-manager@example.test", password_hash="synthetic", display_name="Manager", role=UserRole.MANAGER, is_active=True)
    foreign_manager = User(email="d52b-foreign@example.test", password_hash="synthetic", display_name="Foreign", role=UserRole.MANAGER, is_active=True)
    client = Client(name="Synthetic client", email=email)
    stage = PipelineStage(name="D52b stage", position=91)
    session.add_all([admin, manager, foreign_manager, client, stage])
    session.flush()
    deal = Deal(name="Synthetic deal", client_id=client.id, stage_id=stage.id, responsible_user_id=manager.id)
    session.add(deal)
    session.flush()
    draft = EmailDraft(deal_id=deal.id, subject="Synthetic subject", body="Synthetic body", purpose="Synthetic purpose", language=AIResultLanguage.EN, creator_user_id=manager.id)
    connection = IntegrationConnection(provider=IntegrationProvider.GMAIL, status=IntegrationConnectionStatus.CONNECTED, display_name="Gmail", encrypted_token_payload="ciphertext")
    session.add_all([draft, connection])
    session.commit()
    return SimpleNamespace(admin=admin, manager=manager, foreign_manager=foreign_manager, client=client, deal=deal, draft=draft, connection=connection)


@pytest.mark.skipif(__import__("os").getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_gmail_outbound_success_finalizes_once_and_sent_draft_is_immutable(isolated_database, monkeypatch):
    with isolated_database() as session:
        records = _records(session)
        monkeypatch.setattr(gmail_outbound, "get_google_access_token", lambda session, connection: "synthetic-access")
        calls = []
        def send(**values):
            calls.append(values)
            return GmailSendResult(provider_message_id="provider-message", provider_thread_id="provider-thread")
        monkeypatch.setattr(gmail_outbound, "send_gmail_message", send)
        pending = request_gmail_send(session, deal_id=records.deal.id, draft_id=records.draft.id, current_user=records.manager)
        assert pending.status is ExternalMessageStatus.PENDING
        assert request_gmail_send(session, deal_id=records.deal.id, draft_id=records.draft.id, current_user=records.manager).id == pending.id
        sent = execute_gmail_send(session, external_message_id=pending.id)
        assert sent.status is ExternalMessageStatus.SENT
        assert sent.communication_id is not None
        assert len(calls) == 1
        communication = session.get(Communication, sent.communication_id)
        assert communication.content == "Subject: Synthetic subject\n\nSynthetic body"
        assert session.get(EmailDraft, records.draft.id).state is EmailDraftState.SENT
        with pytest.raises(SentEmailDraftImmutableError):
            update_email_draft(session, deal_id=records.deal.id, draft_id=records.draft.id, changes={"subject": "must remain unchanged"}, current_user=records.manager)
        with pytest.raises(SentEmailDraftImmutableError):
            delete_email_draft(session, deal_id=records.deal.id, draft_id=records.draft.id, current_user=records.manager)
        persisted_draft = session.get(EmailDraft, records.draft.id)
        assert persisted_draft.subject == "Synthetic subject" and persisted_draft.body == "Synthetic body"
        assert execute_gmail_send(session, external_message_id=pending.id).id == pending.id
        assert session.scalars(select(Communication)).all() == [communication]
        assert session.scalars(select(ExternalMessage)).all() == [sent]


@pytest.mark.skipif(__import__("os").getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_gmail_outbound_validation_authorization_failure_and_unknown_have_no_communication(isolated_database, monkeypatch):
    with isolated_database() as session:
        records = _records(session, email=None)
        with pytest.raises(GmailOutboundValidationError) as invalid:
            request_gmail_send(session, deal_id=records.deal.id, draft_id=records.draft.id, current_user=records.manager)
        assert invalid.value.code is ProviderErrorCode.INVALID_RECIPIENT
        assert session.scalars(select(ExternalMessage)).all() == []
        records.client.email = "recipient@example.test"
        session.commit()
        with pytest.raises(GmailOutboundForbiddenError):
            request_gmail_send(session, deal_id=records.deal.id, draft_id=records.draft.id, current_user=records.foreign_manager)
        assert session.scalars(select(ExternalMessage)).all() == []
        pending = request_gmail_send(session, deal_id=records.deal.id, draft_id=records.draft.id, current_user=records.manager)
        monkeypatch.setattr(gmail_outbound, "get_google_access_token", lambda session, connection: "synthetic-access")
        monkeypatch.setattr(gmail_outbound, "send_gmail_message", lambda **values: (_ for _ in ()).throw(GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE, RetryClass.UNCERTAIN)))
        unknown = execute_gmail_send(session, external_message_id=pending.id)
        assert unknown.status is ExternalMessageStatus.UNKNOWN
        assert session.scalars(select(Communication)).all() == []
        assert session.get(EmailDraft, records.draft.id).state is EmailDraftState.DRAFT
