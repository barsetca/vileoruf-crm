import logging
from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, aliased

from backend.app.models import AIAnalysis, AIAnalysisStatus, AIFunctionType, Category, Deal, LeadScoringSettings, PipelineStage, Service, User
from backend.app.schemas.business import LeadScoringSettingsPayload
from backend.app.services.commercial_value import DEFAULT_COMMERCIAL_VALUE_SCALE
from backend.app.services.ai.deal_prediction import invalidate_latest_deal_prediction


logger = logging.getLogger(__name__)
TERMINAL_STAGES = ("Won", "Lost")


class BusinessConfigurationError(ValueError): pass
class BusinessRecordNotFoundError(BusinessConfigurationError): pass
class BusinessRecordConflictError(BusinessConfigurationError): pass
class InactiveCategoryError(BusinessConfigurationError): pass
class BusinessPersistenceError(BusinessConfigurationError): pass


def list_categories(session: Session, *, active_only: bool = False) -> list[Category]:
    statement = select(Category).order_by(Category.name_ru, Category.id)
    if active_only:
        statement = statement.where(Category.is_active.is_(True))
    return _scalars(session, statement)


def create_category(session: Session, *, values: dict, actor: User) -> Category:
    category = Category(**values)
    session.add(category)
    _commit(session, conflict=True)
    session.refresh(category)
    logger.info("business_setting_changed actor=%s entity=category id=%s action=create", actor.id, category.id)
    return category


def update_category(session: Session, *, category_id: UUID, changes: dict, actor: User) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise BusinessRecordNotFoundError
    financial_changed = any(field in changes and getattr(category, field) != changes[field] for field in ("target_hourly_rate", "target_effort"))
    old = {field: str(getattr(category, field)) for field in changes}
    for field, value in changes.items():
        setattr(category, field, value)
    if financial_changed:
        invalidate_latest_lead_scoring(session, category_id=category.id)
        invalidate_latest_next_best_action_for_category(session, category.id)
    _commit(session, conflict=True)
    session.refresh(category)
    logger.info("business_setting_changed actor=%s entity=category id=%s old=%s new=%s", actor.id, category.id, old, {field: str(getattr(category, field)) for field in changes})
    return category


def list_services(session: Session, *, active_only: bool = False) -> list[Service]:
    statement = select(Service).order_by(Service.name_ru, Service.id)
    if active_only:
        statement = statement.join(Category).where(Service.is_active.is_(True), Category.is_active.is_(True))
    return _scalars(session, statement)


def create_service(session: Session, *, values: dict, actor: User) -> Service:
    _require_active_category(session, values["category_id"])
    service = Service(**values)
    session.add(service)
    _commit(session, conflict=True)
    session.refresh(service)
    logger.info("business_setting_changed actor=%s entity=service id=%s action=create", actor.id, service.id)
    return service


def update_service(session: Session, *, service_id: UUID, changes: dict, actor: User) -> Service:
    service = session.get(Service, service_id)
    if service is None:
        raise BusinessRecordNotFoundError
    category_changed = "category_id" in changes and changes["category_id"] != service.category_id
    if "category_id" in changes:
        _require_active_category(session, changes["category_id"])
    old = {field: str(getattr(service, field)) for field in changes}
    for field, value in changes.items():
        setattr(service, field, value)
    if category_changed:
        invalidate_latest_lead_scoring(session, service_id=service.id)
        invalidate_latest_deal_prediction_for_service(session, service.id)
        invalidate_latest_next_best_action_for_service(session, service.id)
    _commit(session, conflict=True)
    session.refresh(service)
    logger.info("business_setting_changed actor=%s entity=service id=%s old=%s new=%s", actor.id, service.id, old, {field: str(getattr(service, field)) for field in changes})
    return service


def get_lead_scoring_settings(session: Session) -> LeadScoringSettings:
    settings = session.get(LeadScoringSettings, 1)
    if settings is None:
        settings = LeadScoringSettings(id=1, commercial_value_scale=[point.model_dump(mode="json") for point in DEFAULT_COMMERCIAL_VALUE_SCALE])
        session.add(settings)
        _commit(session)
        session.refresh(settings)
    return settings


def update_lead_scoring_settings(session: Session, *, payload: LeadScoringSettingsPayload, actor: User) -> LeadScoringSettings:
    settings = get_lead_scoring_settings(session)
    old = _settings_dict(settings)
    new = payload.model_dump(mode="json")
    for field, value in new.items():
        setattr(settings, field, value)
    if old != new:
        invalidate_latest_lead_scoring(session)
        from backend.app.services.ai.next_best_action import invalidate_latest_next_best_action

        invalidate_latest_next_best_action(session)
    _commit(session)
    session.refresh(settings)
    logger.info("business_setting_changed actor=%s entity=lead_scoring_settings old=%s new=%s", actor.id, old, _settings_dict(settings))
    return settings


def invalidate_latest_lead_scoring(session: Session, *, category_id: UUID | None = None, service_id: UUID | None = None, deal_id: UUID | None = None) -> None:
    active_deals = select(Deal.id).join(PipelineStage).where(PipelineStage.name.not_in(TERMINAL_STAGES))
    if category_id is not None:
        active_deals = active_deals.join(Service).where(Service.category_id == category_id)
    if service_id is not None:
        active_deals = active_deals.where(Deal.service_id == service_id)
    if deal_id is not None:
        active_deals = active_deals.where(Deal.id == deal_id)
    outer = aliased(AIAnalysis)
    inner = aliased(AIAnalysis)
    latest_success_id = select(inner.id).where(
        inner.deal_id == outer.deal_id,
        inner.function_type == AIFunctionType.LEAD_SCORING,
        inner.status == AIAnalysisStatus.SUCCESS,
    ).order_by(inner.created_at.desc(), inner.id.desc()).limit(1).correlate(outer).scalar_subquery()
    latest_ids = select(outer.id).where(
        outer.deal_id.in_(active_deals),
        outer.function_type == AIFunctionType.LEAD_SCORING,
        outer.status == AIAnalysisStatus.SUCCESS,
        outer.id == latest_success_id,
    )
    session.execute(update(AIAnalysis).where(AIAnalysis.id.in_(latest_ids)).values(is_outdated=True))


def invalidate_latest_deal_prediction_for_category(session: Session, category_id: UUID) -> None:
    for deal_id in session.scalars(select(Deal.id).join(Service).where(Service.category_id == category_id)):
        invalidate_latest_deal_prediction(session, deal_id=deal_id)


def invalidate_latest_deal_prediction_for_service(session: Session, service_id: UUID) -> None:
    for deal_id in session.scalars(select(Deal.id).where(Deal.service_id == service_id)):
        invalidate_latest_deal_prediction(session, deal_id=deal_id)


def invalidate_latest_next_best_action_for_category(session: Session, category_id: UUID) -> None:
    from backend.app.services.ai.next_best_action import invalidate_latest_next_best_action

    for deal_id in session.scalars(select(Deal.id).join(Service).where(Service.category_id == category_id)):
        invalidate_latest_next_best_action(session, deal_id=deal_id)


def invalidate_latest_next_best_action_for_service(session: Session, service_id: UUID) -> None:
    from backend.app.services.ai.next_best_action import invalidate_latest_next_best_action

    for deal_id in session.scalars(select(Deal.id).where(Deal.service_id == service_id)):
        invalidate_latest_next_best_action(session, deal_id=deal_id)


def _require_active_category(session: Session, category_id: UUID) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise BusinessRecordNotFoundError
    if not category.is_active:
        raise InactiveCategoryError
    return category


def _scalars(session: Session, statement: Select) -> list:
    try:
        return list(session.scalars(statement))
    except SQLAlchemyError as error:
        session.rollback()
        raise BusinessPersistenceError from error


def _commit(session: Session, *, conflict: bool = False) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if conflict:
            raise BusinessRecordConflictError from error
        raise BusinessPersistenceError from error
    except SQLAlchemyError as error:
        session.rollback()
        raise BusinessPersistenceError from error


def _settings_dict(settings: LeadScoringSettings) -> dict:
    return {"service_fit_weight": settings.service_fit_weight, "commercial_value_weight": settings.commercial_value_weight, "lead_quality_weight": settings.lead_quality_weight, "feasibility_weight": settings.feasibility_weight, "commercial_value_scale": settings.commercial_value_scale}
