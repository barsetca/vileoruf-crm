from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import TaskStatus, User
from backend.app.schemas.tasks import TaskCreate, TaskResponse, TaskUpdate
from backend.app.services.tasks import (
    TaskClientNotFoundError,
    TaskCreateForbiddenError,
    TaskDealClientMismatchError,
    TaskDealNotFoundError,
    TaskInvalidResponsibleUserError,
    TaskNotFoundError,
    TaskPersistenceError,
    TaskResponsibleAssignmentForbiddenError,
    TaskResponsibleUserNotFoundError,
    TaskUpdateForbiddenError,
    complete_task,
    create_task,
    get_task,
    list_tasks,
    update_task,
)


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def post_task(payload: TaskCreate, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try:
        return create_task(session, values=payload.model_dump(), current_user=current_user)
    except Exception as error:
        raise _task_http_error(error) from error


@router.get("", response_model=list[TaskResponse])
async def get_tasks(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    responsible_user_id: UUID | None = None,
    client_id: UUID | None = None,
    deal_id: UUID | None = None,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
):
    try:
        return list_tasks(session, limit=limit, offset=offset, responsible_user_id=responsible_user_id, client_id=client_id, deal_id=deal_id, status=status_filter)
    except TaskPersistenceError as error:
        raise _persistence_error() from error


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(task_id: UUID, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try:
        return get_task(session, task_id=task_id)
    except Exception as error:
        raise _task_http_error(error) from error


@router.patch("/{task_id}", response_model=TaskResponse)
async def patch_task(task_id: UUID, payload: TaskUpdate, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try:
        return update_task(session, task_id=task_id, changes=payload.model_dump(exclude_unset=True), current_user=current_user)
    except Exception as error:
        raise _task_http_error(error) from error


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def post_task_completion(task_id: UUID, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try:
        return complete_task(session, task_id=task_id, current_user=current_user)
    except Exception as error:
        raise _task_http_error(error) from error


def _task_http_error(error: Exception) -> HTTPException:
    if isinstance(error, TaskNotFoundError):
        return HTTPException(status_code=404, detail="Task not found")
    if isinstance(error, TaskResponsibleUserNotFoundError):
        return HTTPException(status_code=404, detail="Responsible user not found")
    if isinstance(error, TaskClientNotFoundError):
        return HTTPException(status_code=404, detail="Client not found")
    if isinstance(error, TaskDealNotFoundError):
        return HTTPException(status_code=404, detail="Deal not found")
    if isinstance(error, (TaskInvalidResponsibleUserError, TaskDealClientMismatchError)):
        return HTTPException(status_code=422, detail="Invalid task relationship or responsible user")
    if isinstance(error, (TaskCreateForbiddenError, TaskUpdateForbiddenError, TaskResponsibleAssignmentForbiddenError)):
        return HTTPException(status_code=403, detail="Task action is not permitted")
    if isinstance(error, TaskPersistenceError):
        return _persistence_error()
    return _persistence_error()


def _persistence_error() -> HTTPException:
    return HTTPException(status_code=500, detail="Task operation failed")
