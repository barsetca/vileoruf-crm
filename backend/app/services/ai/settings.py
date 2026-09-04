import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import AIInfrastructureSettings, get_ai_infrastructure_settings
from backend.app.models import AIModelSettings, User
from backend.app.schemas.ai_settings import AISettingsResponse, AISettingsUpdate
from backend.app.services.ai.model_settings import resolve_ai_models
from backend.app.services.ai.runtime_settings import DEFAULT_DEAL_PREDICTION_VALIDITY_DAYS, DEFAULT_NEXT_BEST_ACTION_VALIDITY_DAYS, get_ai_runtime_settings


logger = logging.getLogger(__name__)


class AISettingsPersistenceError(RuntimeError):
    pass


class AISettingsModelNotAllowedError(ValueError):
    pass


def get_ai_settings(session: Session, *, infrastructure: AIInfrastructureSettings | None = None) -> AISettingsResponse:
    infra = infrastructure or get_ai_infrastructure_settings()
    row = session.get(AIModelSettings, 1)
    runtime = get_ai_runtime_settings(session)
    models = resolve_ai_models(session, infra)
    return AISettingsResponse(
        ai_enabled=runtime.ai_enabled,
        automatic_new_deal_analysis=runtime.automatic_new_deal_analysis,
        analysis_model_override=row.analysis_model_override if row else None,
        effective_analysis_model=models.analysis_model,
        default_analysis_model=infra.ai_analysis_model,
        email_model_override=row.email_model_override if row else None,
        effective_email_model=models.email_model,
        default_email_model=infra.ai_email_model,
        allowed_models=list(infra.allowed_models),
        deal_prediction_validity_days=runtime.deal_prediction_validity_days,
        default_deal_prediction_validity_days=DEFAULT_DEAL_PREDICTION_VALIDITY_DAYS,
        next_best_action_validity_days=runtime.next_best_action_validity_days,
        default_next_best_action_validity_days=DEFAULT_NEXT_BEST_ACTION_VALIDITY_DAYS,
    )


def update_ai_settings(session: Session, *, payload: AISettingsUpdate, actor: User, infrastructure: AIInfrastructureSettings | None = None) -> AISettingsResponse:
    infra = infrastructure or get_ai_infrastructure_settings()
    changes = payload.model_dump(exclude_unset=True)
    for field in ("analysis_model_override", "email_model_override"):
        value = changes.get(field)
        if value is not None and value not in infra.allowed_models:
            raise AISettingsModelNotAllowedError

    try:
        row = session.scalar(select(AIModelSettings).where(AIModelSettings.id == 1).with_for_update())
        if row is None:
            row = AIModelSettings(id=1)
            session.add(row)
            session.flush()
        old = {field: getattr(row, field) for field in changes}
        for field, value in changes.items():
            setattr(row, field, value)
        session.commit()
    except (IntegrityError, SQLAlchemyError) as error:
        session.rollback()
        raise AISettingsPersistenceError from error
    for field, new_value in changes.items():
        old_value = old[field]
        if old_value != new_value:
            action = "reset" if field.endswith("_override") and new_value is None else "change"
            logger.info("ai_setting_changed actor=%s setting=%s action=%s old=%s new=%s", actor.id, field, action, old_value, new_value)
    return get_ai_settings(session, infrastructure=infra)
