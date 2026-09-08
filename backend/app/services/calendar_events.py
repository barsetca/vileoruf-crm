from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from backend.app.models import CalendarEvent, CalendarEventStatus, Client, Deal, IntegrationConnectionStatus, Task, User, UserRole
from backend.app.models.user import utc_now
from backend.app.services.google_calendar import GoogleCalendarError, get_google_calendar_access_token, synchronize_google_calendar_connection
from backend.app.services.integrations_adapters import GmailAdapterError, ProviderErrorCode, cancel_google_calendar_event, create_google_calendar_event, update_google_calendar_event

class CalendarEventError(ValueError): pass
class CalendarEventNotFoundError(CalendarEventError): pass
class CalendarEventForbiddenError(CalendarEventError): pass
class CalendarEventValidationError(CalendarEventError): pass
class CalendarEventUnavailableError(CalendarEventError): pass
class CalendarEventIdempotencyConflictError(CalendarEventError): pass
class CalendarEventStateError(CalendarEventError): pass
class CalendarEventIntegrityError(CalendarEventError): pass

def request_calendar_event_create(session: Session, *, values: dict, idempotency_key: str, current_user: User) -> tuple[CalendarEvent,bool]:
    connection=synchronize_google_calendar_connection(session)
    if connection.status is not IntegrationConnectionStatus.CONNECTED: raise CalendarEventUnavailableError
    _validate_event_values(values)
    client,deal,task=_validate_context(session,values)
    _authorize(current_user,deal,task)
    existing=session.scalar(select(CalendarEvent).where(CalendarEvent.integration_connection_id==connection.id,CalendarEvent.idempotency_key==idempotency_key))
    if existing:
        if not _same_request(existing,values,current_user): raise CalendarEventIdempotencyConflictError
        _authorize_event(current_user,existing,session)
        return existing,False
    event=CalendarEvent(integration_connection_id=connection.id,idempotency_key=idempotency_key,created_by_user_id=current_user.id,status=CalendarEventStatus.PENDING,**values)
    session.add(event)
    try: session.commit(); session.refresh(event); return event,True
    except IntegrityError:
        session.rollback(); existing=session.scalar(select(CalendarEvent).where(CalendarEvent.integration_connection_id==connection.id,CalendarEvent.idempotency_key==idempotency_key))
        if existing and _same_request(existing,values,current_user): return existing,False
        raise CalendarEventIdempotencyConflictError from None
    except SQLAlchemyError as error: session.rollback(); raise CalendarEventError from error

def get_calendar_event(session: Session, *, event_id: UUID, current_user: User) -> CalendarEvent:
    event=session.get(CalendarEvent,event_id)
    if not event: raise CalendarEventNotFoundError
    _authorize_event(current_user,event,session); return event

def request_calendar_event_update(session: Session, *, event_id: UUID, changes: dict, current_user: User) -> CalendarEvent:
    connection=synchronize_google_calendar_connection(session)
    if connection.status is not IntegrationConnectionStatus.CONNECTED: raise CalendarEventUnavailableError
    try:
        event=session.scalar(select(CalendarEvent).where(CalendarEvent.id==event_id).with_for_update())
        if not event: raise CalendarEventNotFoundError
        _authorize_event(current_user,event,session)
        if event.status is not CalendarEventStatus.SYNCED: raise CalendarEventStateError
        if not event.provider_event_id or event.integration_connection_id != connection.id: raise CalendarEventIntegrityError
        if not changes: raise CalendarEventValidationError
        values={field:getattr(event,field) for field in ("title","description","start_at","end_at","timezone")}
        values.update(changes)
        _validate_event_values(values)
        for field,value in values.items(): setattr(event,field,value)
        event.status=CalendarEventStatus.PENDING
        event.last_error_code=None
        session.commit(); session.refresh(event); return event
    except CalendarEventError:
        session.rollback(); raise
    except SQLAlchemyError as error:
        session.rollback(); raise CalendarEventError from error

def request_calendar_event_cancel(session: Session, *, event_id: UUID, current_user: User) -> CalendarEvent:
    connection=synchronize_google_calendar_connection(session)
    if connection.status is not IntegrationConnectionStatus.CONNECTED: raise CalendarEventUnavailableError
    event=session.get(CalendarEvent,event_id)
    if not event: raise CalendarEventNotFoundError
    _authorize_event(current_user,event,session)
    if event.status is not CalendarEventStatus.SYNCED: raise CalendarEventStateError
    if not event.provider_event_id or event.integration_connection_id != connection.id: raise CalendarEventIntegrityError
    provider_event_id=event.provider_event_id
    try:
        token=get_google_calendar_access_token(session)
        cancel_google_calendar_event(access_token=token,provider_event_id=provider_event_id)
    except GoogleCalendarError as error: raise CalendarEventUnavailableError from error
    except GmailAdapterError as error: raise CalendarEventUnavailableError from error
    try:
        event=session.scalar(select(CalendarEvent).where(CalendarEvent.id==event_id).with_for_update())
        if not event: raise CalendarEventNotFoundError
        if event.status is not CalendarEventStatus.SYNCED or event.provider_event_id != provider_event_id: raise CalendarEventStateError
        event.status=CalendarEventStatus.CANCELLED
        event.last_synced_at=utc_now()
        event.last_error_code=None
        session.commit(); session.refresh(event); return event
    except CalendarEventError:
        session.rollback(); raise
    except SQLAlchemyError as error:
        session.rollback(); raise CalendarEventError from error

def list_calendar_events(session: Session, *, client_id: UUID|None, deal_id: UUID|None, task_id: UUID|None, limit: int, offset: int, current_user: User) -> list[CalendarEvent]:
    if not any((client_id,deal_id,task_id)): raise CalendarEventValidationError
    _client, deal, task = _validate_context(session,{"client_id":client_id,"deal_id":deal_id,"task_id":task_id})
    _authorize(current_user,deal,task)
    statement=select(CalendarEvent)
    if client_id: statement=statement.where(CalendarEvent.client_id==client_id)
    if deal_id: statement=statement.where(CalendarEvent.deal_id==deal_id)
    if task_id: statement=statement.where(CalendarEvent.task_id==task_id)
    events=list(session.scalars(statement.order_by(CalendarEvent.start_at.desc(),CalendarEvent.id.desc()).limit(limit).offset(offset)))
    return events

def execute_calendar_event_create(session: Session, *, event_id: UUID) -> CalendarEvent:
    event=session.get(CalendarEvent,event_id)
    if not event: raise CalendarEventNotFoundError
    if event.status is not CalendarEventStatus.PENDING: return event
    try:
        token=get_google_calendar_access_token(session)
        result=create_google_calendar_event(access_token=token,title=event.title,description=event.description,start_at=event.start_at,end_at=event.end_at,timezone_name=event.timezone)
    except GoogleCalendarError as error: return _finish_error(session,event,error.code)
    except GmailAdapterError as error: return _finish_error(session,event,error.code)
    event.status=CalendarEventStatus.SYNCED; event.provider_event_id=result.provider_event_id; event.external_url=result.external_url; event.last_synced_at=utc_now(); event.last_error_code=None
    session.commit(); session.refresh(event); return event

def execute_calendar_event_update(session: Session, *, event_id: UUID) -> CalendarEvent:
    event=session.get(CalendarEvent,event_id)
    if not event: raise CalendarEventNotFoundError
    if event.status is not CalendarEventStatus.PENDING: return event
    if not event.provider_event_id: return _finish_error(session,event,ProviderErrorCode.PROVIDER_ERROR)
    try:
        token=get_google_calendar_access_token(session)
        result=update_google_calendar_event(access_token=token,provider_event_id=event.provider_event_id,title=event.title,description=event.description,start_at=event.start_at,end_at=event.end_at,timezone_name=event.timezone)
    except GoogleCalendarError as error: return _finish_error(session,event,error.code)
    except GmailAdapterError as error: return _finish_error(session,event,error.code)
    event.status=CalendarEventStatus.SYNCED
    if result.external_url is not None: event.external_url=result.external_url
    event.last_synced_at=utc_now(); event.last_error_code=None
    session.commit(); session.refresh(event); return event

def _finish_error(session,event,code):
    event.status=CalendarEventStatus.ERROR; event.last_error_code=code.value; session.commit(); session.refresh(event); return event
def _validate_context(session,v):
    client=session.get(Client,v.get("client_id")) if v.get("client_id") else None
    deal=session.get(Deal,v.get("deal_id")) if v.get("deal_id") else None
    task=session.get(Task,v.get("task_id")) if v.get("task_id") else None
    if v.get("client_id") and not client or v.get("deal_id") and not deal or v.get("task_id") and not task: raise CalendarEventNotFoundError
    if client and deal and deal.client_id!=client.id: raise CalendarEventValidationError
    if task:
        if task.client_id and client and task.client_id!=client.id: raise CalendarEventValidationError
        if task.deal_id and deal and task.deal_id!=deal.id: raise CalendarEventValidationError
        if task.deal_id and client and session.get(Deal,task.deal_id).client_id!=client.id: raise CalendarEventValidationError
        if task.client_id and deal and deal.client_id!=task.client_id: raise CalendarEventValidationError
    return client,deal,task
def _validate_event_values(values):
    title=values.get("title")
    if not isinstance(title,str) or not title.strip() or len(title.strip())>255: raise CalendarEventValidationError
    values["title"]=title.strip()
    timezone_name=values.get("timezone")
    if not isinstance(timezone_name,str) or not timezone_name.strip() or len(timezone_name.strip())>64: raise CalendarEventValidationError
    try: values["timezone"]=ZoneInfo(timezone_name).key
    except ZoneInfoNotFoundError as error: raise CalendarEventValidationError from error
    start_at,end_at=values.get("start_at"),values.get("end_at")
    if not isinstance(start_at,datetime) or not isinstance(end_at,datetime) or start_at.tzinfo is None or end_at.tzinfo is None or start_at.utcoffset() is None or end_at.utcoffset() is None or end_at<=start_at: raise CalendarEventValidationError
def _authorize(user,deal,task):
    if user.role is UserRole.MANAGER and ((deal and deal.responsible_user_id!=user.id) or (task and task.responsible_user_id!=user.id)): raise CalendarEventForbiddenError
def _authorize_event(user,event,session): _authorize(user,session.get(Deal,event.deal_id) if event.deal_id else None,session.get(Task,event.task_id) if event.task_id else None)
def _same_request(event,v,user): return event.created_by_user_id==user.id and all(getattr(event,k)==v.get(k) for k in ("title","description","start_at","end_at","timezone","client_id","deal_id","task_id"))
