import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, aliased

from backend.app.models import AIAnalysis, AIAnalysisStatus, AIFunctionType, AIResultLanguage, Client, ClientStatus, Deal, PipelineStage, Service, User, UserRole
from backend.app.models.user import utc_now
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


def list_deals(session: Session, *, limit: int, offset: int, archived: bool = False) -> list[dict[str, Any]]:
    visibility = (
        or_(Deal.archived_at.is_not(None), Client.archived_at.is_not(None))
        if archived
        else and_(Deal.archived_at.is_(None), Client.archived_at.is_(None))
    )
    lead = aliased(AIAnalysis)
    prediction = aliased(AIAnalysis)
    latest_lead_id = _latest_success_analysis_id(AIFunctionType.LEAD_SCORING)
    latest_prediction_id = _latest_success_analysis_id(AIFunctionType.DEAL_PREDICTION)
    statement = (
        select(Deal, lead.result_payload, lead.is_outdated, prediction.result_payload, prediction.is_outdated)
        .join(Client)
        .outerjoin(lead, lead.id == latest_lead_id)
        .outerjoin(prediction, prediction.id == latest_prediction_id)
        .where(visibility)
        .order_by(Deal.created_at.desc(), Deal.id.desc())
        .limit(limit)
        .offset(offset)
    )
    try:
        return [
            {
                **_deal_response_values(deal),
                "latest_lead_scoring_score": (lead_payload or {}).get("overall_score"),
                "latest_lead_scoring_is_outdated": lead_outdated,
                "latest_deal_prediction_probability": (prediction_payload or {}).get("probability_won"),
                "latest_deal_prediction_is_outdated": prediction_outdated,
            }
            for deal, lead_payload, lead_outdated, prediction_payload, prediction_outdated in session.execute(statement)
        ]
    except SQLAlchemyError as error:
        session.rollback()
        raise DealPersistenceError from error


def _latest_success_analysis_id(function_type: AIFunctionType):
    return (
        select(AIAnalysis.id)
        .where(
            AIAnalysis.deal_id == Deal.id,
            AIAnalysis.function_type == function_type,
            AIAnalysis.status == AIAnalysisStatus.SUCCESS,
        )
        .order_by(AIAnalysis.created_at.desc(), AIAnalysis.id.desc())
        .limit(1)
        .correlate(Deal)
        .scalar_subquery()
    )


def _deal_response_values(deal: Deal) -> dict[str, Any]:
    return {
        "id": deal.id,
        "client_id": deal.client_id,
        "stage_id": deal.stage_id,
        "responsible_user_id": deal.responsible_user_id,
        "service_id": deal.service_id,
        "name": deal.name,
        "description": deal.description,
        "estimated_budget": deal.estimated_budget,
        "deadline": deal.deadline,
        "probability": deal.probability,
        "manager_effort_estimate": deal.manager_effort_estimate,
        "created_at": deal.created_at,
        "first_won_at": deal.first_won_at,
        "updated_at": deal.updated_at,
        "archived_at": deal.archived_at,
    }


def get_deal(session: Session, *, deal_id: UUID) -> Deal:
    try:
        deal = session.get(Deal, deal_id)
    except SQLAlchemyError as error:
        session.rollback()
        raise DealPersistenceError from error
    if deal is None:
        raise DealNotFoundError
    return deal


def archive_deal(session: Session, *, deal_id: UUID) -> Deal:
    deal = get_deal(session, deal_id=deal_id)
    if deal.archived_at is None:
        deal.archived_at = utc_now(); _commit_deal(session, deal)
    return deal


def restore_deal(session: Session, *, deal_id: UUID) -> Deal:
    deal = get_deal(session, deal_id=deal_id)
    if deal.archived_at is not None:
        deal.archived_at = None; _commit_deal(session, deal)
    return deal


def _commit_deal(session: Session, deal: Deal) -> None:
    try:
        session.commit(); session.refresh(deal)
    except SQLAlchemyError as error:
        session.rollback(); raise DealPersistenceError from error


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
        client = session.get(Client, values["client_id"])
        if client is None or client.archived_at is not None:
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
            if deal.first_won_at is None:
                deal.first_won_at = datetime.now(timezone.utc)
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
