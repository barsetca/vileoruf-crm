import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.models import CalendarEvent, CalendarEventStatus, Client, Communication, CommunicationChannel, CommunicationDirection, EmailDraft, EmailDraftState, ExternalMessage, ExternalMessageStatus, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, PipelineStage, Task, TaskStatus, User, UserRole, Deal
from backend.app.services.email_drafts import SentEmailDraftImmutableError, update_email_draft

pytestmark=pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")

@pytest.fixture
def isolated_database() -> Iterator[sessionmaker[Session]]:
    source=make_url(get_settings().database_url); name=f"vileoruf_d51_{uuid4().hex}"; maintenance=create_engine(source.set(database="postgres"),isolation_level="AUTOCOMMIT"); url=source.set(database=name); engine=None
    with maintenance.connect() as c:c.exec_driver_sql(f'CREATE DATABASE "{name}"')
    old=os.environ.get("DATABASE_URL"); os.environ["DATABASE_URL"]=url.render_as_string(False); get_settings.cache_clear()
    try:
        command.upgrade(Config("backend/alembic.ini"),"head"); engine=create_engine(url); yield sessionmaker(bind=engine,expire_on_commit=False)
    finally:
        get_settings.cache_clear(); os.environ.pop("DATABASE_URL",None) if old is None else os.environ.__setitem__("DATABASE_URL",old)
        if engine:engine.dispose()
        with maintenance.connect() as c:c.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        maintenance.dispose()

def test_d51_postgresql_persistence_constraints_and_domain_separation(isolated_database):
    with isolated_database() as s:
        admin=User(email="d51-admin@example.test",password_hash="synthetic",display_name="Admin",role=UserRole.ADMIN,is_active=True); stage=PipelineStage(name="New Lead",position=1); client=Client(name="D51 client")
        s.add_all([admin,stage,client]);s.flush(); deal=Deal(name="D51 deal",client_id=client.id,stage_id=stage.id,responsible_user_id=admin.id); task=Task(title="D51 task",due_at=datetime.now(timezone.utc)+timedelta(days=1),responsible_user_id=admin.id,client_id=client.id,deal_id=deal.id); s.add_all([deal,task]);s.flush()
        connection=IntegrationConnection(provider=IntegrationProvider.GMAIL,status=IntegrationConnectionStatus.DISCONNECTED,display_name="Gmail");s.add(connection);s.commit()
        s.add(IntegrationConnection(provider=IntegrationProvider.GMAIL,status=IntegrationConnectionStatus.ERROR,display_name="duplicate"))
        with pytest.raises(IntegrityError):s.commit()
        s.rollback(); assert s.get(IntegrationConnection,connection.id).provider is IntegrationProvider.GMAIL
        communication=Communication(client_id=client.id,deal_id=deal.id,channel=CommunicationChannel.EMAIL,direction=CommunicationDirection.OUTGOING,content="recorded",occurred_at=datetime.now(timezone.utc),status="RECORDED");s.add(communication);s.flush(); before=s.scalar(select(Communication).count()) if False else 1
        message=ExternalMessage(integration_connection_id=connection.id,provider=IntegrationProvider.GMAIL,provider_message_id="synthetic-message",client_id=client.id,deal_id=deal.id,communication_id=communication.id,direction="OUTGOING",status=ExternalMessageStatus.SENT,sender_identifier="a",recipient_identifier="b",content="external");s.add(message);s.commit(); assert s.get(ExternalMessage,message.id).communication_id==communication.id
        s.add(ExternalMessage(integration_connection_id=connection.id,provider=IntegrationProvider.GMAIL,provider_message_id="synthetic-message",direction="OUTGOING",status=ExternalMessageStatus.PENDING,sender_identifier="a",recipient_identifier="b",content="duplicate"))
        with pytest.raises(IntegrityError):s.commit()
        s.rollback(); assert len(list(s.scalars(select(Communication))))==1
        event=CalendarEvent(integration_connection_id=connection.id,client_id=client.id,deal_id=deal.id,task_id=task.id,title="D51 event",start_at=datetime.now(timezone.utc),end_at=datetime.now(timezone.utc)+timedelta(hours=1),timezone="UTC",status=CalendarEventStatus.PENDING,created_by_user_id=admin.id);s.add(event);s.commit(); assert s.get(Task,task.id).status is TaskStatus.OPEN
        draft=EmailDraft(deal_id=deal.id,creator_user_id=admin.id,language="EN",subject="draft",body="body",purpose="test",state=EmailDraftState.DRAFT);s.add(draft);s.commit(); update_email_draft(s,deal_id=deal.id,draft_id=draft.id,changes={"body":"updated"},current_user=admin); draft.state=EmailDraftState.SENT;s.commit()
        with pytest.raises(SentEmailDraftImmutableError):update_email_draft(s,deal_id=deal.id,draft_id=draft.id,changes={"body":"blocked"},current_user=admin)
        assert s.get(EmailDraft,draft.id).body=="updated" and s.get(EmailDraft,draft.id).state is EmailDraftState.SENT
