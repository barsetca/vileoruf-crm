import os
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from backend.app.models import CalendarEvent, CalendarEventStatus, Client, Deal, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, PipelineStage, Task, TaskStatus, User, UserRole
from backend.app.schemas.calendar_events import CalendarEventCreate
from backend.app.services import calendar_events
from backend.app.services.calendar_events import CalendarEventForbiddenError, CalendarEventUnavailableError, CalendarEventValidationError, execute_calendar_event_create, request_calendar_event_create
from backend.app.services import integrations_adapters
from backend.app.services.integrations_adapters import GmailAdapterError, GoogleCalendarCreateResult, ProviderErrorCode, RetryClass
from backend.tests.test_d52a_google_oauth import isolated_database

def records(s):
    admin=User(email="c-admin@test",password_hash="x",display_name="a",role=UserRole.ADMIN,is_active=True); manager=User(email="c-manager@test",password_hash="x",display_name="m",role=UserRole.MANAGER,is_active=True); foreign=User(email="c-foreign@test",password_hash="x",display_name="f",role=UserRole.MANAGER,is_active=True); client=Client(name="c"); other=Client(name="o"); stage=PipelineStage(name="c stage",position=98); s.add_all([admin,manager,foreign,client,other,stage]);s.flush(); deal=Deal(name="d",client_id=client.id,stage_id=stage.id,responsible_user_id=manager.id); task=Task(title="t",due_at=datetime.now(timezone.utc),status=TaskStatus.OPEN,responsible_user_id=manager.id,client_id=client.id,deal_id=deal.id); connection=IntegrationConnection(provider=IntegrationProvider.GOOGLE_CALENDAR,status=IntegrationConnectionStatus.CONNECTED,display_name="Google Calendar");s.add_all([deal,task,connection]);s.commit();return SimpleNamespace(admin=admin,manager=manager,foreign=foreign,client=client,other=other,deal=deal,task=task,connection=connection)
def values(r,**x):
    v=dict(title="Synthetic event",description="body",start_at=datetime(2030,1,1,10,tzinfo=timezone.utc),end_at=datetime(2030,1,1,11,tzinfo=timezone.utc),timezone="UTC",client_id=r.client.id,deal_id=r.deal.id,task_id=r.task.id);v.update(x);return v
@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")
def test_pending_success_failure_and_idempotency(isolated_database,monkeypatch):
 with isolated_database() as s:
  r=records(s); monkeypatch.setattr(calendar_events,"synchronize_google_calendar_connection",lambda _:r.connection); event,created=request_calendar_event_create(s,values=values(r),idempotency_key="key",current_user=r.manager); assert created and event.status is CalendarEventStatus.PENDING
  same,created=request_calendar_event_create(s,values=values(r),idempotency_key="key",current_user=r.manager); assert not created and same.id==event.id and len(list(s.scalars(select(CalendarEvent))))==1
  monkeypatch.setattr(calendar_events,"get_google_calendar_access_token",lambda _:"synthetic"); monkeypatch.setattr(calendar_events,"create_google_calendar_event",lambda **_:GoogleCalendarCreateResult("provider-event","https://calendar.test/event")); synced=execute_calendar_event_create(s,event_id=event.id); assert synced.status is CalendarEventStatus.SYNCED and synced.provider_event_id and synced.external_url
  failed,_=request_calendar_event_create(s,values=values(r,title="failure"),idempotency_key="key-2",current_user=r.admin); monkeypatch.setattr(calendar_events,"create_google_calendar_event",lambda **_:(_ for _ in ()).throw(GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE,RetryClass.UNCERTAIN))); assert execute_calendar_event_create(s,event_id=failed.id).status is CalendarEventStatus.ERROR and s.get(Task,r.task.id).status is TaskStatus.OPEN
@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")
def test_context_authorization_and_unavailable(isolated_database,monkeypatch):
 with isolated_database() as s:
  r=records(s); monkeypatch.setattr(calendar_events,"synchronize_google_calendar_connection",lambda _:r.connection)
  with pytest.raises(CalendarEventForbiddenError): request_calendar_event_create(s,values=values(r),idempotency_key="foreign",current_user=r.foreign)
  with pytest.raises(CalendarEventValidationError): request_calendar_event_create(s,values=values(r,client_id=r.other.id),idempotency_key="bad",current_user=r.admin)
  r.connection.status=IntegrationConnectionStatus.DISCONNECTED
  with pytest.raises(CalendarEventUnavailableError): request_calendar_event_create(s,values=values(r),idempotency_key="off",current_user=r.admin)


@pytest.mark.parametrize(
    ("start_at", "end_at", "timezone_name", "expected_start", "expected_end"),
    [
        (datetime(2026, 9, 10, 10, tzinfo=timezone.utc), datetime(2026, 9, 10, 11, tzinfo=timezone.utc), "Europe/Madrid", "2026-09-10T12:00:00+02:00", "2026-09-10T13:00:00+02:00"),
        (datetime(2026, 1, 10, 11, tzinfo=timezone.utc), datetime(2026, 1, 10, 12, tzinfo=timezone.utc), "Europe/Madrid", "2026-01-10T12:00:00+01:00", "2026-01-10T13:00:00+01:00"),
        (datetime(2026, 9, 10, 12, tzinfo=timezone.utc), datetime(2026, 9, 10, 13, tzinfo=timezone.utc), "UTC", "2026-09-10T12:00:00+00:00", "2026-09-10T13:00:00+00:00"),
    ],
)
def test_google_calendar_create_payload_normalizes_stored_instants_to_event_timezone(monkeypatch, start_at, end_at, timezone_name, expected_start, expected_end):
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"id": "synthetic-provider-event"}

    monkeypatch.setattr(integrations_adapters.httpx, "post", lambda url, **kwargs: captured.update(url=url, **kwargs) or Response())
    integrations_adapters.create_google_calendar_event(
        access_token="synthetic",
        title="Synthetic event",
        description=None,
        start_at=start_at,
        end_at=end_at,
        timezone_name=timezone_name,
    )

    assert captured["json"]["start"] == {"dateTime": expected_start, "timeZone": timezone_name}
    assert captured["json"]["end"] == {"dateTime": expected_end, "timeZone": timezone_name}


def test_calendar_create_api_contract_keeps_utc_storage_and_existing_timezone_range_validation():
    payload = CalendarEventCreate(
        title="Synthetic event",
        start_at=datetime(2026, 9, 10, 10, tzinfo=timezone.utc),
        end_at=datetime(2026, 9, 10, 11, tzinfo=timezone.utc),
        timezone="Europe/Madrid",
    )

    assert payload.start_at == datetime(2026, 9, 10, 10, tzinfo=timezone.utc)
    assert payload.end_at == datetime(2026, 9, 10, 11, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        CalendarEventCreate(title="Invalid timezone", start_at=payload.start_at, end_at=payload.end_at, timezone="Not/AZone")
    with pytest.raises(ValueError):
        CalendarEventCreate(title="Invalid range", start_at=payload.start_at, end_at=payload.start_at, timezone="Europe/Madrid")
