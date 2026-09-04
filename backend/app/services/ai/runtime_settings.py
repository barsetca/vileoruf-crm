from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.models import AIModelSettings


DEFAULT_DEAL_PREDICTION_VALIDITY_DAYS = 7
DEFAULT_NEXT_BEST_ACTION_VALIDITY_DAYS = 7


class AIIsDisabledError(ValueError):
    pass


@dataclass(frozen=True)
class AIRuntimeSettings:
    ai_enabled: bool
    automatic_new_deal_analysis: bool
    deal_prediction_validity_days: int
    next_best_action_validity_days: int


def get_ai_runtime_settings(session: Session) -> AIRuntimeSettings:
    settings = session.get(AIModelSettings, 1)
    if settings is None:
        return AIRuntimeSettings(
            ai_enabled=True,
            automatic_new_deal_analysis=True,
            deal_prediction_validity_days=DEFAULT_DEAL_PREDICTION_VALIDITY_DAYS,
            next_best_action_validity_days=DEFAULT_NEXT_BEST_ACTION_VALIDITY_DAYS,
        )
    return AIRuntimeSettings(
        ai_enabled=settings.ai_enabled,
        automatic_new_deal_analysis=settings.automatic_new_deal_analysis,
        deal_prediction_validity_days=settings.deal_prediction_validity_days,
        next_best_action_validity_days=settings.next_best_action_validity_days,
    )


def require_ai_enabled(session: Session) -> None:
    if not get_ai_runtime_settings(session).ai_enabled:
        raise AIIsDisabledError("AI is disabled by an administrator")
