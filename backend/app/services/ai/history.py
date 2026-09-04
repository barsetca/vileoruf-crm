from datetime import timedelta
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, aliased, joinedload

from backend.app.models import AIAnalysis, AIAnalysisStatus, AIFunctionType, AIResultLanguage, Deal, PipelineStage, User, UserRole
from backend.app.schemas.ai import DealPredictionAIResult, EmailDraftAIResult, LeadScoringResult, NextBestActionAIResult
from backend.app.schemas.ai_history import AIHistoryItem, AIHistoryPage, SafeProviderUsage
from backend.app.services.ai.email_draft import render_client_name
from backend.app.services.ai.runtime_settings import get_ai_runtime_settings
from backend.app.models.user import utc_now


class AIHistoryDealNotFoundError(ValueError):
    pass


class AIHistoryForbiddenError(ValueError):
    pass


RESULT_MODELS = {
    AIFunctionType.LEAD_SCORING: LeadScoringResult,
    AIFunctionType.DEAL_PREDICTION: DealPredictionAIResult,
    AIFunctionType.NEXT_BEST_ACTION: NextBestActionAIResult,
    AIFunctionType.EMAIL_DRAFT: EmailDraftAIResult,
}


def list_ai_history(
    session: Session,
    *,
    current_user: User,
    function_type: AIFunctionType | None = None,
    status: AIAnalysisStatus | None = None,
    deal_id: UUID | None = None,
    is_outdated: bool | None = None,
    current_only: bool = False,
    language: AIResultLanguage | None = None,
    limit: int = 20,
    offset: int = 0,
) -> AIHistoryPage:
    _apply_history_time_freshness(session, current_user=current_user, deal_id=deal_id)
    newer = aliased(AIAnalysis)
    statement = select(AIAnalysis).join(Deal).options(joinedload(AIAnalysis.deal).joinedload(Deal.client))
    if current_user.role is UserRole.MANAGER:
        statement = statement.where(Deal.responsible_user_id == current_user.id)
    if function_type is not None:
        statement = statement.where(AIAnalysis.function_type == function_type)
    if status is not None:
        statement = statement.where(AIAnalysis.status == status)
    if deal_id is not None:
        statement = statement.where(AIAnalysis.deal_id == deal_id)
    if is_outdated is not None:
        statement = statement.where(AIAnalysis.is_outdated.is_(is_outdated))
    if language is not None:
        statement = statement.where(AIAnalysis.language == language)
    if current_only:
        statement = statement.where(
            AIAnalysis.status == AIAnalysisStatus.SUCCESS,
            ~select(newer.id).where(
                newer.deal_id == AIAnalysis.deal_id,
                newer.function_type == AIAnalysis.function_type,
                newer.status == AIAnalysisStatus.SUCCESS,
                (newer.created_at > AIAnalysis.created_at) | ((newer.created_at == AIAnalysis.created_at) & (newer.id > AIAnalysis.id)),
            ).exists(),
        )
    total = session.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    analyses = list(session.scalars(statement.order_by(AIAnalysis.created_at.desc(), AIAnalysis.id.desc()).limit(limit).offset(offset)))
    current_ids = _current_ids(session, analyses)
    return AIHistoryPage(items=[_item(analysis, analysis.id in current_ids) for analysis in analyses], total=total, limit=limit, offset=offset)


def _apply_history_time_freshness(session: Session, *, current_user: User, deal_id: UUID | None) -> None:
    """Apply DP/NBA age expiry before history filters without touching closed Deals."""
    runtime = get_ai_runtime_settings(session)
    authorized_deals = select(Deal.id).join(PipelineStage).where(PipelineStage.name.not_in(("Won", "Lost")))
    if current_user.role is UserRole.MANAGER:
        authorized_deals = authorized_deals.where(Deal.responsible_user_id == current_user.id)
    if deal_id is not None:
        authorized_deals = authorized_deals.where(Deal.id == deal_id)

    changed = False
    for function_type, validity_days in (
        (AIFunctionType.DEAL_PREDICTION, runtime.deal_prediction_validity_days),
        (AIFunctionType.NEXT_BEST_ACTION, runtime.next_best_action_validity_days),
    ):
        newer = aliased(AIAnalysis)
        latest_expired_ids = select(AIAnalysis.id).where(
            AIAnalysis.deal_id.in_(authorized_deals),
            AIAnalysis.function_type == function_type,
            AIAnalysis.status == AIAnalysisStatus.SUCCESS,
            AIAnalysis.is_outdated.is_(False),
            AIAnalysis.finished_at < utc_now() - timedelta(days=validity_days),
            ~select(newer.id).where(
                newer.deal_id == AIAnalysis.deal_id,
                newer.function_type == AIAnalysis.function_type,
                newer.status == AIAnalysisStatus.SUCCESS,
                (newer.created_at > AIAnalysis.created_at)
                | ((newer.created_at == AIAnalysis.created_at) & (newer.id > AIAnalysis.id)),
            ).exists(),
        )
        result = session.execute(
            update(AIAnalysis)
            .where(AIAnalysis.id.in_(latest_expired_ids))
            .values(is_outdated=True)
            .execution_options(synchronize_session=False)
        )
        changed = changed or bool(result.rowcount)
    if changed:
        session.commit()


def list_deal_ai_history(session: Session, *, deal_id: UUID, current_user: User, **filters) -> AIHistoryPage:
    deal = session.get(Deal, deal_id)
    if deal is None:
        raise AIHistoryDealNotFoundError
    if current_user.role is UserRole.MANAGER and deal.responsible_user_id != current_user.id:
        raise AIHistoryForbiddenError
    return list_ai_history(session, current_user=current_user, deal_id=deal_id, **filters)


def _current_ids(session: Session, analyses: list[AIAnalysis]) -> set[UUID]:
    pairs = {(item.deal_id, item.function_type) for item in analyses}
    result: set[UUID] = set()
    for deal_id, function_type in pairs:
        analysis_id = session.scalar(select(AIAnalysis.id).where(AIAnalysis.deal_id == deal_id, AIAnalysis.function_type == function_type, AIAnalysis.status == AIAnalysisStatus.SUCCESS).order_by(AIAnalysis.created_at.desc(), AIAnalysis.id.desc()).limit(1))
        if analysis_id is not None:
            result.add(analysis_id)
    return result


def _item(analysis: AIAnalysis, is_current: bool) -> AIHistoryItem:
    result_payload = None
    result_valid = None
    if analysis.status is AIAnalysisStatus.SUCCESS:
        try:
            result_payload = RESULT_MODELS[analysis.function_type].model_validate(analysis.result_payload)
            if analysis.function_type is AIFunctionType.EMAIL_DRAFT:
                result_payload = result_payload.model_copy(update={
                    "subject": render_client_name(result_payload.subject, analysis.deal.client.name),
                    "body": render_client_name(result_payload.body, analysis.deal.client.name),
                })
            result_valid = True
        except (ValidationError, KeyError, TypeError):
            result_payload = None
            result_valid = False
    usage = None
    if analysis.provider_usage:
        safe = {key: value for key, value in analysis.provider_usage.items() if key in {"input_tokens", "output_tokens", "total_tokens"} and isinstance(value, int) and value >= 0}
        usage = SafeProviderUsage(**safe) if safe else None
    return AIHistoryItem(
        id=analysis.id, deal_id=analysis.deal_id, deal_name=analysis.deal.name,
        function_type=analysis.function_type, status=analysis.status, language=analysis.language,
        actual_model=analysis.actual_model, error_category=analysis.error_category,
        result_payload=result_payload, result_valid=result_valid, is_outdated=analysis.is_outdated,
        is_current=is_current, attempt_count=analysis.attempt_count, provider_usage=usage,
        created_at=analysis.created_at, started_at=analysis.started_at, finished_at=analysis.finished_at,
        duration_ms=analysis.duration_ms,
    )
