import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import AIResultLanguage, Client, ClientStatus, Deal, PipelineStage, Service, User, UserRole
from backend.app.services.business import invalidate_latest_lead_scoring
from backend.app.services.ai.deal_prediction import invalidate_latest_deal_prediction
from backend.app.services.ai.next_best_action import invalidate_latest_next_best_action
from backend.app.models.pipeline_stage import WON_STAGE_NAME


logger = logging.getLogger(__name__)


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


class DealServiceNotFoundError(DealServiceError): pass
class InactiveDealServiceError(DealServiceError): pass


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
    analysis_language: AIResultLanguage | None = None,
) -> Deal:
    if current_user.role is UserRole.MANAGER:
        if responsible_was_supplied:
            raise ResponsibleAssignmentForbiddenError
        values["responsible_user_id"] = current_user.id
    else:
        responsible_user_id = values.get("responsible_user_id")
        if responsible_user_id is not None:
            _validate_responsible_user(session, responsible_user_id)

    if values.get("service_id") is not None:
        _validate_service(session, values["service_id"])

    try:
        if session.get(Client, values["client_id"]) is None:
            raise DealClientNotFoundError
        if session.get(PipelineStage, values["stage_id"]) is None:
            raise DealStageNotFoundError

        deal = Deal(**values)
        session.add(deal)
        session.flush()
        invalidate_latest_deal_prediction(session, client_id=deal.client_id)
        invalidate_latest_next_best_action(session, client_id=deal.client_id)
        session.commit()
        session.refresh(deal)
    except DealServiceError:
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise DealPersistenceError from error
    if analysis_language is not None:
        try:
            from backend.app.services.ai.orchestration import start_initial_ai_pipeline

            start_initial_ai_pipeline(
                session, deal_id=deal.id, language=analysis_language
            )
        except Exception:
            session.rollback()
            logger.error("initial_ai_pipeline_start_failed deal=%s", deal.id)
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

    if "service_id" in changes and changes["service_id"] is not None:
        _validate_service(session, changes["service_id"])

    significant_fields = {"service_id", "description", "estimated_budget", "deadline", "manager_effort_estimate"}
    significant_changed = any(field in changes and getattr(deal, field) != changes[field] for field in significant_fields)

    for field, value in changes.items():
        setattr(deal, field, value)

    if significant_changed:
        invalidate_latest_lead_scoring(session, deal_id=deal.id)
        invalidate_latest_deal_prediction(session, client_id=deal.client_id)
        invalidate_latest_next_best_action(session, client_id=deal.client_id)

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
        invalidate_latest_deal_prediction(session, client_id=deal.client_id)
        invalidate_latest_next_best_action(session, client_id=deal.client_id)
        invalidate_latest_deal_prediction(
            session, deal_id=deal.id, include_closed=True
        )
        invalidate_latest_next_best_action(
            session, deal_id=deal.id, include_closed=True
        )
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


def _validate_service(session: Session, service_id: UUID) -> Service:
    service = session.get(Service, service_id)
    if service is None:
        raise DealServiceNotFoundError
    if not service.is_active or not service.category.is_active:
        raise InactiveDealServiceError
    return service
