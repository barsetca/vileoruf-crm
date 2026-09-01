from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import Client, ClientStatus, Deal, PipelineStage, User, UserRole
from backend.app.models.pipeline_stage import WON_STAGE_NAME


class DealServiceError(ValueError):
    pass


class DealNotFoundError(DealServiceError):
    pass


class DealClientNotFoundError(DealServiceError):
    pass


class DealStageNotFoundError(DealServiceError):
    pass


class ResponsibleUserNotFoundError(DealServiceError):
    pass


class InvalidResponsibleUserError(DealServiceError):
    pass


class DealEditForbiddenError(DealServiceError):
    pass


class ResponsibleAssignmentForbiddenError(DealServiceError):
    pass


class DealPersistenceError(DealServiceError):
    pass


def list_deals(session: Session, *, limit: int, offset: int) -> list[Deal]:
    statement = (
        select(Deal)
        .order_by(Deal.created_at.desc(), Deal.id.desc())
        .limit(limit)
        .offset(offset)
    )
    try:
        return list(session.scalars(statement))
    except SQLAlchemyError as error:
        session.rollback()
        raise DealPersistenceError from error


def get_deal(session: Session, *, deal_id: UUID) -> Deal:
    try:
        deal = session.get(Deal, deal_id)
    except SQLAlchemyError as error:
        session.rollback()
        raise DealPersistenceError from error
    if deal is None:
        raise DealNotFoundError
    return deal


def create_deal(
    session: Session,
    *,
    values: dict,
    current_user: User,
    responsible_was_supplied: bool,
) -> Deal:
    if current_user.role is UserRole.MANAGER:
        if responsible_was_supplied:
            raise ResponsibleAssignmentForbiddenError
        values["responsible_user_id"] = current_user.id
    else:
        responsible_user_id = values.get("responsible_user_id")
        if responsible_user_id is not None:
            _validate_responsible_user(session, responsible_user_id)

    try:
        if session.get(Client, values["client_id"]) is None:
            raise DealClientNotFoundError
        if session.get(PipelineStage, values["stage_id"]) is None:
            raise DealStageNotFoundError

        deal = Deal(**values)
        session.add(deal)
        session.commit()
        session.refresh(deal)
    except DealServiceError:
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise DealPersistenceError from error
    return deal


def update_deal(
    session: Session,
    *,
    deal_id: UUID,
    changes: dict,
    current_user: User,
) -> Deal:
    deal = get_deal(session, deal_id=deal_id)
    _ensure_deal_edit_allowed(deal, current_user)

    if "responsible_user_id" in changes:
        if current_user.role is not UserRole.ADMIN:
            raise ResponsibleAssignmentForbiddenError
        responsible_user_id = changes["responsible_user_id"]
        if responsible_user_id is not None:
            _validate_responsible_user(session, responsible_user_id)

    for field, value in changes.items():
        setattr(deal, field, value)

    try:
        session.commit()
        session.refresh(deal)
    except SQLAlchemyError as error:
        session.rollback()
        raise DealPersistenceError from error
    return deal


def transition_deal(
    session: Session,
    *,
    deal_id: UUID,
    stage_id: UUID,
    current_user: User,
) -> Deal:
    try:
        deal = session.scalar(
            select(Deal).where(Deal.id == deal_id).with_for_update()
        )
        if deal is None:
            raise DealNotFoundError
        _ensure_deal_edit_allowed(deal, current_user)

        target_stage = session.get(PipelineStage, stage_id)
        if target_stage is None:
            raise DealStageNotFoundError
        if deal.stage_id == target_stage.id:
            return deal

        deal.stage_id = target_stage.id
        if target_stage.name == WON_STAGE_NAME:
            client = session.get(Client, deal.client_id, with_for_update=True)
            if client is None:
                raise DealPersistenceError
            if client.status is ClientStatus.CUSTOMER:
                client.status = ClientStatus.CLIENT

        session.commit()
        session.refresh(deal)
        return deal
    except DealServiceError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise DealPersistenceError from error


def _ensure_deal_edit_allowed(deal: Deal, current_user: User) -> None:
    if (
        current_user.role is UserRole.MANAGER
        and deal.responsible_user_id != current_user.id
    ):
        raise DealEditForbiddenError


def _validate_responsible_user(session: Session, user_id: UUID) -> User:
    try:
        user = session.get(User, user_id)
    except SQLAlchemyError as error:
        session.rollback()
        raise DealPersistenceError from error
    if user is None:
        raise ResponsibleUserNotFoundError
    if user.role not in (UserRole.ADMIN, UserRole.MANAGER) or not user.is_active:
        raise InvalidResponsibleUserError
    return user
