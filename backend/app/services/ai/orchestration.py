import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import (
    AIAnalysis,
    AIAnalysisStatus,
    AIErrorCategory,
    AIFunctionType,
    AIResultLanguage,
    Deal,
    InitialAIAnalysisPipeline,
    PipelineStage,
)
from backend.app.services.ai.deal_prediction import (
    DealPredictionConfigurationError,
    PROMPT_VERSION as DP_PROMPT_VERSION,
    SNAPSHOT_FIELDS as DP_SNAPSHOT_FIELDS,
    _serialize_prepared as serialize_prediction,
    prepare_deal_prediction,
)
from backend.app.services.ai.inputs import deterministic_input_fingerprint
from backend.app.services.ai.lead_scoring import (
    LeadScoringConfigurationError,
    PROMPT_VERSION as LS_PROMPT_VERSION,
    SNAPSHOT_FIELDS as LS_SNAPSHOT_FIELDS,
    _serialize_prepared as serialize_lead_scoring,
    prepare_lead_scoring,
)
from backend.app.services.ai.next_best_action import (
    NextBestActionConfigurationError,
    create_next_best_action_analysis,
    prepare_next_best_action,
    serialize_prepared as serialize_next_best_action,
)
from backend.app.services.ai.operations import (
    DuplicateInFlightOperationError,
    create_queued_analysis,
    mark_queued_analysis_dispatch_failed,
    utc_now,
)
from backend.app.services.ai.runtime_settings import get_ai_runtime_settings


logger = logging.getLogger(__name__)
TERMINAL_STAGES = {"Won", "Lost"}


@dataclass(frozen=True)
class InitialPipelineLaunch:
    pipeline: InitialAIAnalysisPipeline
    lead_scoring_payload: dict[str, Any] | None
    deal_prediction_payload: dict[str, Any] | None


def start_initial_ai_pipeline(
    session: Session, *, deal_id: UUID, language: AIResultLanguage
) -> InitialAIAnalysisPipeline | None:
    settings = get_ai_runtime_settings(session)
    if not settings.ai_enabled or not settings.automatic_new_deal_analysis:
        return None
    stage_name = session.scalar(
        select(PipelineStage.name)
        .join(Deal, Deal.stage_id == PipelineStage.id)
        .where(Deal.id == deal_id)
    )
    if stage_name is None or stage_name in TERMINAL_STAGES:
        return None
    existing = session.scalar(
        select(InitialAIAnalysisPipeline).where(
            InitialAIAnalysisPipeline.deal_id == deal_id
        )
    )
    if existing is not None:
        return existing

    launch = _create_pipeline(session, deal_id=deal_id, language=language)
    _dispatch_initial_branches(session, launch)
    return launch.pipeline


def _create_pipeline(
    session: Session, *, deal_id: UUID, language: AIResultLanguage
) -> InitialPipelineLaunch:
    lead_payload: dict[str, Any] | None = None
    prediction_payload: dict[str, Any] | None = None
    try:
        prepared_lead = prepare_lead_scoring(
            session, deal_id=deal_id, language=language
        )
        lead = create_queued_analysis(
            session,
            deal_id=deal_id,
            function_type=AIFunctionType.LEAD_SCORING,
            language=language,
            prompt_version=LS_PROMPT_VERSION,
            significant_input=prepared_lead.significant_input,
            snapshot_source=prepared_lead.snapshot,
            snapshot_fields=LS_SNAPSHOT_FIELDS,
            commit=False,
        )
        lead_payload = serialize_lead_scoring(prepared_lead)
    except LeadScoringConfigurationError:
        lead = _configuration_failure(
            deal_id=deal_id,
            function_type=AIFunctionType.LEAD_SCORING,
            language=language,
            prompt_version=LS_PROMPT_VERSION,
        )
        session.add(lead)
        session.flush()

    try:
        prepared_prediction = prepare_deal_prediction(
            session, deal_id=deal_id, language=language
        )
        prediction = create_queued_analysis(
            session,
            deal_id=deal_id,
            function_type=AIFunctionType.DEAL_PREDICTION,
            language=language,
            prompt_version=DP_PROMPT_VERSION,
            significant_input=prepared_prediction.significant_input,
            snapshot_source=prepared_prediction.snapshot,
            snapshot_fields=DP_SNAPSHOT_FIELDS,
            commit=False,
        )
        prediction_payload = serialize_prediction(prepared_prediction)
    except DealPredictionConfigurationError:
        prediction = _configuration_failure(
            deal_id=deal_id,
            function_type=AIFunctionType.DEAL_PREDICTION,
            language=language,
            prompt_version=DP_PROMPT_VERSION,
        )
        session.add(prediction)
        session.flush()

    pipeline = InitialAIAnalysisPipeline(
        deal_id=deal_id,
        language=language,
        lead_scoring_analysis_id=lead.id,
        deal_prediction_analysis_id=prediction.id,
    )
    session.add(pipeline)
    try:
        session.commit()
        session.refresh(pipeline)
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(InitialAIAnalysisPipeline).where(
                InitialAIAnalysisPipeline.deal_id == deal_id
            )
        )
        if existing is not None:
            return InitialPipelineLaunch(existing, None, None)
        raise
    return InitialPipelineLaunch(pipeline, lead_payload, prediction_payload)


def _dispatch_initial_branches(
    session: Session, launch: InitialPipelineLaunch
) -> None:
    from backend.app.workers.ai_tasks import execute_deal_prediction, execute_lead_scoring

    branches = (
        (
            launch.pipeline.lead_scoring_analysis_id,
            launch.lead_scoring_payload,
            execute_lead_scoring,
        ),
        (
            launch.pipeline.deal_prediction_analysis_id,
            launch.deal_prediction_payload,
            execute_deal_prediction,
        ),
    )
    for analysis_id, payload, task in branches:
        if payload is None:
            continue
        try:
            task.delay(str(analysis_id), payload)
        except Exception:
            analysis = session.get(AIAnalysis, analysis_id)
            if analysis is not None:
                mark_queued_analysis_dispatch_failed(session, analysis)
            logger.error(
                "initial_ai_branch_dispatch_failed pipeline=%s function=%s",
                launch.pipeline.id,
                task.name,
            )
    advance_initial_ai_pipeline(session, pipeline_id=launch.pipeline.id)


def advance_initial_ai_pipeline(
    session: Session,
    *,
    analysis_id: UUID | None = None,
    pipeline_id: UUID | None = None,
    deal_id: UUID | None = None,
) -> AIAnalysis | None:
    statement = select(InitialAIAnalysisPipeline)
    if pipeline_id is not None:
        statement = statement.where(InitialAIAnalysisPipeline.id == pipeline_id)
    elif analysis_id is not None:
        statement = statement.where(
            or_(
                InitialAIAnalysisPipeline.lead_scoring_analysis_id == analysis_id,
                InitialAIAnalysisPipeline.deal_prediction_analysis_id == analysis_id,
            )
        )
    elif deal_id is not None:
        statement = statement.where(InitialAIAnalysisPipeline.deal_id == deal_id)
    else:
        return None
    pipeline = session.scalar(statement.with_for_update())
    if pipeline is None or pipeline.next_best_action_analysis_id is not None:
        return None
    branches = [
        session.get(AIAnalysis, pipeline.lead_scoring_analysis_id),
        session.get(AIAnalysis, pipeline.deal_prediction_analysis_id),
    ]
    if any(
        branch is None
        or branch.status not in (AIAnalysisStatus.SUCCESS, AIAnalysisStatus.FAILED)
        for branch in branches
    ):
        session.rollback()
        return None
    stage_name = session.scalar(
        select(PipelineStage.name)
        .join(Deal, Deal.stage_id == PipelineStage.id)
        .where(Deal.id == pipeline.deal_id)
    )
    if stage_name is None or stage_name in TERMINAL_STAGES:
        session.commit()
        return None

    prepared = None
    try:
        prepared = prepare_next_best_action(
            session,
            deal_id=pipeline.deal_id,
            language=pipeline.language,
            auxiliary_analysis_ids=(
                pipeline.lead_scoring_analysis_id,
                pipeline.deal_prediction_analysis_id,
            ),
        )
        analysis = create_next_best_action_analysis(
            session,
            deal_id=pipeline.deal_id,
            language=pipeline.language,
            prepared=prepared,
            commit=False,
        )
    except NextBestActionConfigurationError:
        analysis = _configuration_failure(
            deal_id=pipeline.deal_id,
            function_type=AIFunctionType.NEXT_BEST_ACTION,
            language=pipeline.language,
            prompt_version="next-best-action-v1",
        )
        session.add(analysis)
        session.flush()
    except DuplicateInFlightOperationError:
        session.rollback()
        return None

    pipeline.next_best_action_analysis_id = analysis.id
    session.commit()
    if prepared is not None:
        from backend.app.workers.ai_tasks import execute_next_best_action

        try:
            execute_next_best_action.delay(
                str(analysis.id), serialize_next_best_action(prepared)
            )
        except Exception:
            mark_queued_analysis_dispatch_failed(session, analysis)
            logger.error(
                "initial_ai_nba_dispatch_failed pipeline=%s", pipeline.id
            )
    return analysis


def _configuration_failure(
    *,
    deal_id: UUID,
    function_type: AIFunctionType,
    language: AIResultLanguage,
    prompt_version: str,
) -> AIAnalysis:
    finished_at = utc_now()
    return AIAnalysis(
        deal_id=deal_id,
        function_type=function_type,
        status=AIAnalysisStatus.FAILED,
        language=language,
        prompt_version=prompt_version,
        started_at=finished_at,
        finished_at=finished_at,
        duration_ms=0,
        input_fingerprint=deterministic_input_fingerprint(
            {"deal_id": deal_id, "function_type": function_type}
        ),
        input_snapshot={"configuration_available": False},
        error_category=AIErrorCategory.CONFIGURATION_ERROR,
        result_payload=None,
        is_outdated=False,
        attempt_count=0,
    )
