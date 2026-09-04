from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import Client, Deal, Task, TaskStatus, User, UserRole
from backend.app.services.ai.deal_prediction import invalidate_latest_deal_prediction
from backend.app.services.ai.next_best_action import invalidate_latest_next_best_action


class TaskServiceError(ValueError):
    pass


class TaskNotFoundError(TaskServiceError):
    pass


class TaskResponsibleUserNotFoundError(TaskServiceError):
    pass


class TaskInvalidResponsibleUserError(TaskServiceError):
    pass


class TaskClientNotFoundError(TaskServiceError):
    pass


class TaskDealNotFoundError(TaskServiceError):
    pass


class TaskDealClientMismatchError(TaskServiceError):
    pass


class TaskCreateForbiddenError(TaskServiceError):
    pass


class TaskUpdateForbiddenError(TaskServiceError):
    pass


class TaskResponsibleAssignmentForbiddenError(TaskServiceError):
    pass


class TaskPersistenceError(TaskServiceError):
    pass


def list_tasks(
    session: Session,
    *,
    limit: int,
    offset: int,
    responsible_user_id: UUID | None,
    client_id: UUID | None,
    deal_id: UUID | None,
    status: TaskStatus | None,
) -> list[Task]:
    statement = select(Task)
    if responsible_user_id is not None:
        statement = statement.where(Task.responsible_user_id == responsible_user_id)
    if client_id is not None:
        statement = statement.where(Task.client_id == client_id)
    if deal_id is not None:
        statement = statement.where(Task.deal_id == deal_id)
    if status is not None:
        statement = statement.where(Task.status == status)
    statement = statement.order_by(Task.due_at.asc(), Task.id.asc()).limit(limit).offset(offset)
    try:
        return list(session.scalars(statement))
    except SQLAlchemyError as error:
        session.rollback()
        raise TaskPersistenceError from error


def get_task(session: Session, *, task_id: UUID) -> Task:
    try:
        task = session.get(Task, task_id)
    except SQLAlchemyError as error:
        session.rollback()
        raise TaskPersistenceError from error
    if task is None:
        raise TaskNotFoundError
    return task


def create_task(session: Session, *, values: dict, current_user: User) -> Task:
    try:
        if current_user.role is UserRole.MANAGER and values["responsible_user_id"] != current_user.id:
            raise TaskCreateForbiddenError
        _validate_responsible_user(session, values["responsible_user_id"])
        _validate_associations(session, values.get("client_id"), values.get("deal_id"))
        task = Task(**values, status=TaskStatus.OPEN)
        session.add(task)
        if task.deal_id is not None:
            invalidate_latest_deal_prediction(session, deal_id=task.deal_id)
            invalidate_latest_next_best_action(session, deal_id=task.deal_id)
        session.commit()
        session.refresh(task)
        return task
    except TaskServiceError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise TaskPersistenceError from error


def update_task(
    session: Session, *, task_id: UUID, changes: dict, current_user: User
) -> Task:
    try:
        task = get_task(session, task_id=task_id)
        previous_deal_id = task.deal_id
        _ensure_update_allowed(task, current_user)
        if "responsible_user_id" in changes:
            if current_user.role is not UserRole.ADMIN:
                raise TaskResponsibleAssignmentForbiddenError
            _validate_responsible_user(session, changes["responsible_user_id"])
        client_id = changes["client_id"] if "client_id" in changes else task.client_id
        deal_id = changes["deal_id"] if "deal_id" in changes else task.deal_id
        _validate_associations(session, client_id, deal_id)
        for field, value in changes.items():
            setattr(task, field, value)
        if previous_deal_id is not None:
            invalidate_latest_deal_prediction(session, deal_id=previous_deal_id)
            invalidate_latest_next_best_action(session, deal_id=previous_deal_id)
        if task.deal_id is not None:
            invalidate_latest_deal_prediction(session, deal_id=task.deal_id)
            invalidate_latest_next_best_action(session, deal_id=task.deal_id)
        session.commit()
        session.refresh(task)
        return task
    except TaskServiceError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise TaskPersistenceError from error


def complete_task(session: Session, *, task_id: UUID, current_user: User) -> Task:
    try:
        task = get_task(session, task_id=task_id)
        _ensure_update_allowed(task, current_user)
        task.status = TaskStatus.COMPLETED
        if task.deal_id is not None:
            invalidate_latest_deal_prediction(session, deal_id=task.deal_id)
            invalidate_latest_next_best_action(session, deal_id=task.deal_id)
        session.commit()
        session.refresh(task)
        return task
    except TaskServiceError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise TaskPersistenceError from error


def _ensure_update_allowed(task: Task, current_user: User) -> None:
    if current_user.role is UserRole.MANAGER and task.responsible_user_id != current_user.id:
        raise TaskUpdateForbiddenError


def _validate_responsible_user(session: Session, user_id: UUID) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise TaskResponsibleUserNotFoundError
    if not user.is_active or user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise TaskInvalidResponsibleUserError
    return user


def _validate_associations(
    session: Session, client_id: UUID | None, deal_id: UUID | None
) -> None:
    client = None
    if client_id is not None:
        client = session.get(Client, client_id)
        if client is None:
            raise TaskClientNotFoundError
    if deal_id is not None:
        deal = session.get(Deal, deal_id)
        if deal is None:
            raise TaskDealNotFoundError
        if client is not None and deal.client_id != client.id:
            raise TaskDealClientMismatchError
