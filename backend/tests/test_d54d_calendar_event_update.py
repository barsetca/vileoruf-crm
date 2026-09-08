import asyncio
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select

from backend.app.models import CalendarEvent, CalendarEventStatus, Client, Communication, Deal, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, PipelineStage, Task, TaskStatus, User, UserRole
from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.schemas.calendar_events import CalendarEventUpdate
from backend.app.services import calendar_events
from backend.app.services.calendar_events import CalendarEventForbiddenError, CalendarEventIntegrityError, CalendarEventStateError, CalendarEventUnavailableError, CalendarEventValidationError, execute_calendar_event_update, get_calendar_event, list_calendar_events, request_calendar_event_update
from backend.app.services import integrations_adapters
import backend.app.api.calendar_events as calendar_events_router
from backend.app.services.integrations_adapters import GmailAdapterError, GoogleCalendarUpdateResult, ProviderErrorCode, RetryClass
from backend.tests.test_d52a_google_oauth import isolated_database


def records(session):
    admin=User(email="update-admin@test",password_hash="x",display_name="a",role=UserRole.ADMIN,is_active=True)
    manager=User(email="update-manager@test",password_hash="x",display_name="m",role=UserRole.MANAGER,is_active=True)
    foreign=User(email="update-foreign@test",password_hash="x",display_name="f",role=UserRole.MANAGER,is_active=True)
    client=Client(name="update-client")
    stage=PipelineStage(name="update-stage",position=96)
    session.add_all([admin,manager,foreign,client,stage]); session.flush()
    deal=Deal(name="update-deal",client_id=client.id,stage_id=stage.id,responsible_user_id=manager.id)
    foreign_deal=Deal(name="foreign-update-deal",client_id=client.id,stage_id=stage.id,responsible_user_id=foreign.id)
    task=Task(title="update-task",due_at=datetime.now(timezone.utc)+timedelta(days=1),status=TaskStatus.OPEN,responsible_user_id=manager.id,client_id=client.id,deal_id=deal.id)
    foreign_task=Task(title="foreign-update-task",due_at=datetime.now(timezone.utc)+timedelta(days=1),status=TaskStatus.OPEN,responsible_user_id=foreign.id,client_id=client.id,deal_id=foreign_deal.id)
    connection=IntegrationConnection(provider=IntegrationProvider.GOOGLE_CALENDAR,status=IntegrationConnectionStatus.CONNECTED,display_name="Google Calendar")
    session.add_all([deal,foreign_deal,task,foreign_task,connection]); session.commit()
    return SimpleNamespace(admin=admin,manager=manager,foreign=foreign,client=client,deal=deal,foreign_deal=foreign_deal,task=task,foreign_task=foreign_task,connection=connection)


def synced_event(records, **changes):
    values=dict(integration_connection_id=records.connection.id,client_id=records.client.id,deal_id=records.deal.id,task_id=records.task.id,provider_event_id="existing-provider-event",external_url="https://calendar.test/original",title="Original",description="Original description",start_at=datetime(2030,1,1,10,tzinfo=timezone.utc),end_at=datetime(2030,1,1,11,tzinfo=timezone.utc),timezone="UTC",status=CalendarEventStatus.SYNCED,created_by_user_id=records.admin.id)
    values.update(changes)
    return CalendarEvent(**values)


def changes(**values):
    base=dict(title="Updated title",description="Updated description",start_at=datetime(2030,1,2,12,tzinfo=timezone.utc),end_at=datetime(2030,1,2,14,tzinfo=timezone.utc),timezone="Europe/Madrid")
    base.update(values)
    return base


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")
def test_synced_update_changes_same_row_and_preserves_context_lifecycle(isolated_database,monkeypatch):
    with isolated_database() as session:
        records_=records(session); event=synced_event(records_); session.add(event); session.commit(); original_id=event.id; original_provider_id=event.provider_event_id; task_before=(records_.task.status,records_.task.due_at,records_.task.responsible_user_id,records_.task.client_id,records_.task.deal_id)
        monkeypatch.setattr(calendar_events,"synchronize_google_calendar_connection",lambda _:records_.connection)
        updated=request_calendar_event_update(session,event_id=event.id,changes=changes(),current_user=records_.admin)
        assert updated.id==original_id and updated.status is CalendarEventStatus.PENDING and updated.provider_event_id==original_provider_id
        assert (updated.title,updated.description,updated.start_at,updated.end_at,updated.timezone)==tuple(changes().values())
        assert (updated.client_id,updated.deal_id,updated.task_id)==(records_.client.id,records_.deal.id,records_.task.id)
        assert session.scalar(select(func.count()).select_from(CalendarEvent))==1
        assert session.scalar(select(func.count()).select_from(Communication))==0
        assert (records_.task.status,records_.task.due_at,records_.task.responsible_user_id,records_.task.client_id,records_.task.deal_id)==task_before
        with pytest.raises(CalendarEventStateError): request_calendar_event_update(session,event_id=event.id,changes={"title":"second"},current_user=records_.admin)


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")
def test_update_state_integrity_and_authorization_guards(isolated_database,monkeypatch):
    with isolated_database() as session:
        records_=records(session); monkeypatch.setattr(calendar_events,"synchronize_google_calendar_connection",lambda _:records_.connection)
        for state in (CalendarEventStatus.PENDING,CalendarEventStatus.ERROR,CalendarEventStatus.CANCELLED):
            event=synced_event(records_,status=state); session.add(event); session.commit()
            with pytest.raises(CalendarEventStateError): request_calendar_event_update(session,event_id=event.id,changes={"title":"no"},current_user=records_.admin)
        missing=synced_event(records_,provider_event_id=None); session.add(missing); session.commit()
        with pytest.raises(CalendarEventIntegrityError): request_calendar_event_update(session,event_id=missing.id,changes={"title":"no"},current_user=records_.admin)
        allowed=synced_event(records_); session.add(allowed); session.commit()
        assert request_calendar_event_update(session,event_id=allowed.id,changes={"title":"manager"},current_user=records_.manager).status is CalendarEventStatus.PENDING
        client_only=synced_event(records_,deal_id=None,task_id=None); session.add(client_only); session.commit()
        assert request_calendar_event_update(session,event_id=client_only.id,changes={"title":"client-only"},current_user=records_.manager).status is CalendarEventStatus.PENDING
        foreign=synced_event(records_,deal_id=records_.foreign_deal.id,task_id=records_.foreign_task.id); session.add(foreign); session.commit()
        with pytest.raises(CalendarEventForbiddenError): request_calendar_event_update(session,event_id=foreign.id,changes={"title":"forbidden"},current_user=records_.manager)
        mixed=synced_event(records_,deal_id=records_.foreign_deal.id,task_id=records_.task.id); session.add(mixed); session.commit()
        with pytest.raises(CalendarEventForbiddenError): request_calendar_event_update(session,event_id=mixed.id,changes={"title":"mixed"},current_user=records_.manager)


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")
def test_update_provider_terminal_lifecycle_is_same_row_and_no_blind_resend(isolated_database,monkeypatch):
    with isolated_database() as session:
        records_=records(session); event=synced_event(records_); session.add(event); session.commit(); monkeypatch.setattr(calendar_events,"synchronize_google_calendar_connection",lambda _:records_.connection)
        pending=request_calendar_event_update(session,event_id=event.id,changes={"description":None},current_user=records_.admin)
        monkeypatch.setattr(calendar_events,"get_google_calendar_access_token",lambda _:"synthetic")
        captured={}
        def provider(**kwargs): captured.update(kwargs); return GoogleCalendarUpdateResult("https://calendar.test/updated")
        monkeypatch.setattr(calendar_events,"update_google_calendar_event",provider)
        synced=execute_calendar_event_update(session,event_id=pending.id)
        assert synced.id==event.id and synced.status is CalendarEventStatus.SYNCED and synced.provider_event_id=="existing-provider-event" and synced.external_url=="https://calendar.test/updated"
        assert captured["provider_event_id"]=="existing-provider-event" and captured["description"] is None
        failed=synced_event(records_,title="Failure"); session.add(failed); session.commit(); pending=request_calendar_event_update(session,event_id=failed.id,changes={"title":"Failure desired"},current_user=records_.admin)
        monkeypatch.setattr(calendar_events,"update_google_calendar_event",lambda **_:(_ for _ in ()).throw(GmailAdapterError(ProviderErrorCode.PERMISSION_DENIED,RetryClass.NO_RETRY)))
        assert execute_calendar_event_update(session,event_id=pending.id).status is CalendarEventStatus.ERROR
        uncertain=synced_event(records_,title="Uncertain"); session.add(uncertain); session.commit(); pending=request_calendar_event_update(session,event_id=uncertain.id,changes={"title":"Uncertain desired"},current_user=records_.admin)
        calls=[]
        monkeypatch.setattr(calendar_events,"update_google_calendar_event",lambda **_: calls.append(1) or (_ for _ in ()).throw(GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE,RetryClass.UNCERTAIN)))
        errored=execute_calendar_event_update(session,event_id=pending.id)
        assert errored.status is CalendarEventStatus.ERROR and errored.last_error_code==ProviderErrorCode.PROVIDER_UNAVAILABLE.value and len(calls)==1
        assert execute_calendar_event_update(session,event_id=pending.id).status is CalendarEventStatus.ERROR and len(calls)==1


def test_update_schema_is_strict_and_validates_partial_ranges():
    assert CalendarEventUpdate(title="Updated").model_dump(exclude_unset=True)=={"title":"Updated"}
    assert CalendarEventUpdate(description=None).model_dump(exclude_unset=True)=={"description":None}
    with pytest.raises(ValueError): CalendarEventUpdate(client_id="00000000-0000-0000-0000-000000000000")
    with pytest.raises(ValueError): CalendarEventUpdate(title=None)
    with pytest.raises(ValueError): CalendarEventUpdate(timezone="Not/AZone")
    with pytest.raises(ValueError): CalendarEventUpdate(start_at=datetime(2030,1,1,10,tzinfo=timezone.utc),end_at=datetime(2030,1,1,10,tzinfo=timezone.utc))


def test_google_adapter_updates_existing_provider_event_with_patch(monkeypatch):
    captured={}
    class Response:
        status_code=200
        def json(self): return {"id":"provider/event", "htmlLink":"https://calendar.test/updated"}
    def patch(url, **kwargs):
        captured["url"]=url; captured.update(kwargs); return Response()
    monkeypatch.setattr(integrations_adapters.httpx,"patch",patch)
    result=integrations_adapters.update_google_calendar_event(access_token="synthetic",provider_event_id="provider/event",title="Updated",description="body",start_at=datetime(2030,1,1,10,tzinfo=timezone.utc),end_at=datetime(2030,1,1,11,tzinfo=timezone.utc),timezone_name="UTC")
    assert captured["url"].endswith("/events/provider%2Fevent") and captured["json"]["summary"]=="Updated"
    assert result.external_url=="https://calendar.test/updated"


def test_update_api_is_accepted_and_rejects_context_mutation(monkeypatch):
    admin=User(id=uuid4(),email="api-update@test",password_hash="x",display_name="a",role=UserRole.ADMIN,is_active=True)
    now=datetime.now(timezone.utc)
    event=CalendarEvent(id=uuid4(),integration_connection_id=uuid4(),provider_event_id="provider-event",title="Updated",description=None,start_at=datetime(2030,1,1,10,tzinfo=timezone.utc),end_at=datetime(2030,1,1,11,tzinfo=timezone.utc),timezone="UTC",status=CalendarEventStatus.PENDING,created_by_user_id=admin.id,created_at=now,updated_at=now)
    dispatched=[]
    monkeypatch.setattr(calendar_events_router,"request_calendar_event_update",lambda session,**kwargs:event)
    monkeypatch.setattr(calendar_events_router,"update_google_calendar_event_task",SimpleNamespace(delay=lambda event_id: dispatched.append(event_id)))
    app.dependency_overrides[get_db]=lambda:object(); app.dependency_overrides[get_current_user]=lambda:admin
    async def request(payload):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
            return await client.patch(f"/calendar-events/{event.id}",json=payload)
    try:
        assert asyncio.run(request({"title":"Updated"})).status_code==202
        assert dispatched==[str(event.id)]
        assert asyncio.run(request({"client_id":str(uuid4())})).status_code==422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")
def test_cancel_preserves_same_historical_row_and_rejects_invalid_states(isolated_database,monkeypatch):
    with isolated_database() as session:
        records_=records(session); event=synced_event(records_); session.add(event); session.commit()
        original=(event.id,event.provider_event_id,event.title,event.description,event.start_at,event.end_at,event.timezone,event.client_id,event.deal_id,event.task_id)
        monkeypatch.setattr(calendar_events,"synchronize_google_calendar_connection",lambda _:records_.connection)
        monkeypatch.setattr(calendar_events,"get_google_calendar_access_token",lambda _:"synthetic")
        calls=[]; monkeypatch.setattr(calendar_events,"cancel_google_calendar_event",lambda **kwargs:calls.append(kwargs))
        cancelled=calendar_events.request_calendar_event_cancel(session,event_id=event.id,current_user=records_.admin)
        assert cancelled.status is CalendarEventStatus.CANCELLED and len(calls)==1
        assert (cancelled.id,cancelled.provider_event_id,cancelled.title,cancelled.description,cancelled.start_at,cancelled.end_at,cancelled.timezone,cancelled.client_id,cancelled.deal_id,cancelled.task_id)==original
        assert session.scalar(select(func.count()).select_from(CalendarEvent))==1
        with pytest.raises(CalendarEventStateError): calendar_events.request_calendar_event_cancel(session,event_id=event.id,current_user=records_.admin)
        assert len(calls)==1
        for state in (CalendarEventStatus.PENDING,CalendarEventStatus.ERROR):
            blocked=synced_event(records_,status=state); session.add(blocked); session.commit()
            with pytest.raises(CalendarEventStateError): calendar_events.request_calendar_event_cancel(session,event_id=blocked.id,current_user=records_.admin)
        missing=synced_event(records_,provider_event_id=None); session.add(missing); session.commit()
        with pytest.raises(CalendarEventIntegrityError): calendar_events.request_calendar_event_cancel(session,event_id=missing.id,current_user=records_.admin)


def test_google_adapter_cancels_existing_provider_event_with_delete(monkeypatch):
    captured={}
    class Response: status_code=204
    monkeypatch.setattr(integrations_adapters.httpx,"delete",lambda url,**kwargs:captured.update(url=url,**kwargs) or Response())
    integrations_adapters.cancel_google_calendar_event(access_token="synthetic",provider_event_id="provider/event")
    assert captured["url"].endswith("/events/provider%2Fevent")


@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")
def test_cancel_failure_authorization_and_historical_reads(isolated_database,monkeypatch):
    with isolated_database() as session:
        records_=records(session)
        monkeypatch.setattr(calendar_events,"synchronize_google_calendar_connection",lambda _:records_.connection)
        monkeypatch.setattr(calendar_events,"get_google_calendar_access_token",lambda _:"synthetic")
        calls=[]
        def unavailable(**kwargs):
            calls.append(kwargs)
            raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE,RetryClass.UNCERTAIN)
        event=synced_event(records_); session.add(event); session.commit()
        monkeypatch.setattr(calendar_events,"cancel_google_calendar_event",unavailable)
        with pytest.raises(CalendarEventUnavailableError): calendar_events.request_calendar_event_cancel(session,event_id=event.id,current_user=records_.admin)
        session.refresh(event)
        assert event.status is CalendarEventStatus.SYNCED and len(calls)==1
        # A later explicit attempt is permitted, but this operation itself never retries.
        assert session.scalar(select(func.count()).select_from(CalendarEvent))==1
        monkeypatch.setattr(calendar_events,"cancel_google_calendar_event",lambda **kwargs:calls.append(kwargs))
        manager_event=synced_event(records_,title="manager"); session.add(manager_event); session.commit()
        assert calendar_events.request_calendar_event_cancel(session,event_id=manager_event.id,current_user=records_.manager).status is CalendarEventStatus.CANCELLED
        foreign=synced_event(records_,deal_id=records_.foreign_deal.id,task_id=records_.foreign_task.id); session.add(foreign); session.commit()
        mixed=synced_event(records_,deal_id=records_.foreign_deal.id,task_id=records_.task.id); session.add(mixed); session.commit()
        before=len(calls)
        with pytest.raises(CalendarEventForbiddenError): calendar_events.request_calendar_event_cancel(session,event_id=foreign.id,current_user=records_.manager)
        with pytest.raises(CalendarEventForbiddenError): calendar_events.request_calendar_event_cancel(session,event_id=mixed.id,current_user=records_.manager)
        assert len(calls)==before
        assert get_calendar_event(session,event_id=manager_event.id,current_user=records_.manager).status is CalendarEventStatus.CANCELLED
        assert manager_event.id in {item.id for item in list_calendar_events(session,client_id=records_.client.id,deal_id=records_.deal.id,task_id=records_.task.id,limit=25,offset=0,current_user=records_.manager)}


def test_google_adapter_cancel_normalizes_failures_without_retry(monkeypatch):
    class Response: status_code=503
    calls=[]
    monkeypatch.setattr(integrations_adapters.httpx,"delete",lambda *args,**kwargs:calls.append(1) or Response())
    with pytest.raises(GmailAdapterError) as error:
        integrations_adapters.cancel_google_calendar_event(access_token="synthetic",provider_event_id="provider-event")
    assert error.value.code is ProviderErrorCode.PROVIDER_UNAVAILABLE and error.value.retry_class is RetryClass.UNCERTAIN and calls==[1]


def test_cancel_api_dispatches_synchronously_without_a_celery_task(monkeypatch):
    admin=User(id=uuid4(),email="api-cancel@test",password_hash="x",display_name="a",role=UserRole.ADMIN,is_active=True)
    now=datetime.now(timezone.utc)
    event=CalendarEvent(id=uuid4(),integration_connection_id=uuid4(),provider_event_id="provider-event",title="Cancelled",description=None,start_at=datetime(2030,1,1,10,tzinfo=timezone.utc),end_at=datetime(2030,1,1,11,tzinfo=timezone.utc),timezone="UTC",status=CalendarEventStatus.CANCELLED,created_by_user_id=admin.id,created_at=now,updated_at=now)
    calls=[]
    monkeypatch.setattr(calendar_events_router,"request_calendar_event_cancel",lambda session,**kwargs:calls.append(kwargs) or event)
    app.dependency_overrides[get_db]=lambda:object(); app.dependency_overrides[get_current_user]=lambda:admin
    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
            return await client.post(f"/calendar-events/{event.id}/cancel")
    try:
        assert asyncio.run(request()).status_code==200 and len(calls)==1
    finally:
        app.dependency_overrides.clear()


def test_no_cancel_task_or_route_is_registered():
    from backend.app.workers.celery_app import celery_app
    from backend.app.workers import integration_tasks
    assert "integrations.google_calendar.cancel" not in celery_app.conf.task_routes
    assert not hasattr(integration_tasks,"cancel_google_calendar_event_task")
