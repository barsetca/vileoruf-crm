import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from backend.app.models import CalendarEvent, CalendarEventStatus, Client, Deal, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, PipelineStage, Task, TaskStatus, User, UserRole
from backend.app.services.calendar_events import CalendarEventForbiddenError, CalendarEventNotFoundError, CalendarEventValidationError, list_calendar_events
from backend.tests.test_d52a_google_oauth import isolated_database

def data(s):
 a=User(email="l-a@test",password_hash="x",display_name="a",role=UserRole.ADMIN,is_active=True); m=User(email="l-m@test",password_hash="x",display_name="m",role=UserRole.MANAGER,is_active=True); f=User(email="l-f@test",password_hash="x",display_name="f",role=UserRole.MANAGER,is_active=True); c=Client(name="c"); st=PipelineStage(name="list-stage",position=97); s.add_all([a,m,f,c,st]);s.flush(); d=Deal(name="d",client_id=c.id,stage_id=st.id,responsible_user_id=m.id); t=Task(title="t",due_at=datetime.now(timezone.utc),status=TaskStatus.OPEN,responsible_user_id=m.id,client_id=c.id,deal_id=d.id); x=IntegrationConnection(provider=IntegrationProvider.GOOGLE_CALENDAR,status=IntegrationConnectionStatus.CONNECTED,display_name="Google Calendar");s.add_all([d,t,x]);s.flush(); now=datetime(2031,1,1,tzinfo=timezone.utc); es=[CalendarEvent(integration_connection_id=x.id,client_id=c.id,deal_id=d.id,task_id=t.id,title=str(i),start_at=now+timedelta(hours=i),end_at=now+timedelta(hours=i+1),timezone="UTC",status=CalendarEventStatus.SYNCED,created_by_user_id=a.id) for i in range(3)];s.add_all(es);s.commit();return SimpleNamespace(a=a,m=m,f=f,c=c,d=d,t=t,es=es)
@pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS")!="1",reason="PostgreSQL required")
def test_contextual_lists_authorization_and_pagination(isolated_database):
 with isolated_database() as s:
  r=data(s)
  assert [e.id for e in list_calendar_events(s,client_id=r.c.id,deal_id=None,task_id=None,limit=2,offset=0,current_user=r.m)]==[r.es[2].id,r.es[1].id]
  assert [e.id for e in list_calendar_events(s,client_id=None,deal_id=r.d.id,task_id=None,limit=2,offset=1,current_user=r.m)]==[r.es[1].id,r.es[0].id]
  assert len(list_calendar_events(s,client_id=None,deal_id=None,task_id=r.t.id,limit=10,offset=0,current_user=r.m))==3
  with pytest.raises(CalendarEventForbiddenError): list_calendar_events(s,client_id=None,deal_id=r.d.id,task_id=None,limit=10,offset=0,current_user=r.f)
  with pytest.raises(CalendarEventValidationError): list_calendar_events(s,client_id=None,deal_id=None,task_id=None,limit=10,offset=0,current_user=r.a)
  with pytest.raises(CalendarEventNotFoundError): list_calendar_events(s,client_id=None,deal_id=None,task_id=__import__('uuid').uuid4(),limit=10,offset=0,current_user=r.a)
