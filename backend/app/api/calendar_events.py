from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.calendar_events import CalendarEventCreate, CalendarEventResponse, CalendarEventUpdate
from backend.app.services.calendar_events import CalendarEventForbiddenError, CalendarEventIdempotencyConflictError, CalendarEventIntegrityError, CalendarEventNotFoundError, CalendarEventStateError, CalendarEventUnavailableError, CalendarEventValidationError, get_calendar_event, list_calendar_events, request_calendar_event_cancel, request_calendar_event_create, request_calendar_event_update
from backend.app.workers.integration_tasks import create_google_calendar_event_task, update_google_calendar_event_task
router=APIRouter(prefix="/calendar-events",tags=["calendar-events"])
@router.get("",response_model=list[CalendarEventResponse])
def list_contextual(session:Annotated[Session,Depends(get_db)],current_user:Annotated[User,Depends(get_current_user)],client_id:UUID|None=None,deal_id:UUID|None=None,task_id:UUID|None=None,limit:Annotated[int,Query(ge=1,le=25)]=10,offset:Annotated[int,Query(ge=0)]=0):
    try: return list_calendar_events(session,client_id=client_id,deal_id=deal_id,task_id=task_id,limit=limit,offset=offset,current_user=current_user)
    except CalendarEventNotFoundError as error: raise HTTPException(404,"Calendar context not found") from error
    except CalendarEventForbiddenError as error: raise HTTPException(403,"Calendar events are not permitted") from error
    except CalendarEventValidationError as error: raise HTTPException(422,"Calendar context is required") from error
@router.post("",response_model=CalendarEventResponse,status_code=status.HTTP_202_ACCEPTED)
def create(payload: CalendarEventCreate,session:Annotated[Session,Depends(get_db)],current_user:Annotated[User,Depends(get_current_user)],idempotency_key:Annotated[str,Header(alias="Idempotency-Key",min_length=1,max_length=128)]):
    try:
        if not idempotency_key.strip(): raise CalendarEventValidationError
        event,created=request_calendar_event_create(session,values=payload.model_dump(),idempotency_key=idempotency_key.strip(),current_user=current_user)
        if created: create_google_calendar_event_task.delay(str(event.id))
        return event
    except CalendarEventNotFoundError as error: raise HTTPException(404,"Calendar context not found") from error
    except CalendarEventForbiddenError as error: raise HTTPException(403,"Calendar action is not permitted") from error
    except CalendarEventUnavailableError as error: raise HTTPException(422,"Google Calendar is unavailable") from error
    except (CalendarEventValidationError,CalendarEventIdempotencyConflictError) as error: raise HTTPException(422,"Invalid Calendar event request") from error
@router.patch("/{event_id}",response_model=CalendarEventResponse,status_code=status.HTTP_202_ACCEPTED)
def update(event_id:UUID,payload:CalendarEventUpdate,session:Annotated[Session,Depends(get_db)],current_user:Annotated[User,Depends(get_current_user)]):
    try:
        event=request_calendar_event_update(session,event_id=event_id,changes=payload.model_dump(exclude_unset=True),current_user=current_user)
        update_google_calendar_event_task.delay(str(event.id))
        return event
    except CalendarEventNotFoundError as error: raise HTTPException(404,"Calendar event not found") from error
    except CalendarEventForbiddenError as error: raise HTTPException(403,"Calendar event is not permitted") from error
    except CalendarEventUnavailableError as error: raise HTTPException(422,"Google Calendar is unavailable") from error
    except (CalendarEventStateError,CalendarEventIntegrityError) as error: raise HTTPException(409,"Calendar event cannot be updated") from error
    except CalendarEventValidationError as error: raise HTTPException(422,"Invalid Calendar event update") from error
@router.post("/{event_id}/cancel",response_model=CalendarEventResponse)
def cancel(event_id:UUID,session:Annotated[Session,Depends(get_db)],current_user:Annotated[User,Depends(get_current_user)]):
    try: return request_calendar_event_cancel(session,event_id=event_id,current_user=current_user)
    except CalendarEventNotFoundError as error: raise HTTPException(404,"Calendar event not found") from error
    except CalendarEventForbiddenError as error: raise HTTPException(403,"Calendar event is not permitted") from error
    except (CalendarEventStateError,CalendarEventIntegrityError) as error: raise HTTPException(409,"Calendar event cannot be cancelled") from error
    except CalendarEventUnavailableError as error: raise HTTPException(503,"Google Calendar cancellation could not be confirmed") from error
@router.get("/{event_id}",response_model=CalendarEventResponse)
def read(event_id:UUID,session:Annotated[Session,Depends(get_db)],current_user:Annotated[User,Depends(get_current_user)]):
    try: return get_calendar_event(session,event_id=event_id,current_user=current_user)
    except CalendarEventNotFoundError as error: raise HTTPException(404,"Calendar event not found") from error
    except CalendarEventForbiddenError as error: raise HTTPException(403,"Calendar event is not permitted") from error
