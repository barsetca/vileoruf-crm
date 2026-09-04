from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.core.config import AIInfrastructureSettings
from backend.app.models import AIModelSettings
from backend.app.services.ai.provider import ProviderFailure
from backend.app.models import AIErrorCategory


@dataclass(frozen=True)
class ResolvedAIModels:
    analysis_model: str
    email_model: str


def resolve_ai_models(
    session: Session,
    settings: AIInfrastructureSettings,
) -> ResolvedAIModels:
    overrides = session.get(AIModelSettings, 1)
    analysis_model = (
        overrides.analysis_model_override
        if overrides and overrides.analysis_model_override
        else settings.ai_analysis_model
    )
    email_model = (
        overrides.email_model_override
        if overrides and overrides.email_model_override
        else settings.ai_email_model
    )
    if analysis_model not in settings.allowed_models or email_model not in settings.allowed_models:
        raise ProviderFailure(
            AIErrorCategory.CONFIGURATION_ERROR,
            retryable=False,
        )
    return ResolvedAIModels(
        analysis_model=analysis_model,
        email_model=email_model,
    )
