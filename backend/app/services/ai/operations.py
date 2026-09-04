from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from time import sleep
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import (
    AIAnalysis,
    AIAnalysisStatus,
    AIErrorCategory,
    AIFunctionType,
    AIResultLanguage,
    Deal,
)
from backend.app.services.ai.inputs import (
    build_compact_snapshot,
    deterministic_input_fingerprint,
)
from backend.app.services.ai.provider import (
    AIProvider,
    ProviderFailure,
    StructuredProviderRequest,
)


class AIOperationError(RuntimeError):
    pass


class DealNotFoundError(AIOperationError):
    pass


class DuplicateInFlightOperationError(AIOperationError):
    pass


class InvalidAIOperationTransitionError(AIOperationError):
    pass


class AIOperationPersistenceError(AIOperationError):
    pass


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 2
    backoff_seconds: float = 2.0

    def __post_init__(self) -> None:
        if not 0 <= self.max_retries <= 2:
            raise ValueError("max_retries must be between 0 and 2")
        if self.backoff_seconds <= 0:
            raise ValueError("backoff_seconds must be positive")

    def delay_before_retry(self, failed_attempt_number: int) -> float:
        return self.backoff_seconds * (2 ** (failed_attempt_number - 1))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_queued_analysis(
    session: Session,
    *,
    deal_id: UUID,
    function_type: AIFunctionType,
    language: AIResultLanguage,
    prompt_version: str,
    significant_input: dict[str, Any],
    snapshot_source: dict[str, Any],
    snapshot_fields: tuple[str, ...],
    commit: bool = True,
) -> AIAnalysis:
    if session.get(Deal, deal_id) is None:
        raise DealNotFoundError
    analysis = AIAnalysis(
        deal_id=deal_id,
        function_type=function_type,
        status=AIAnalysisStatus.QUEUED,
        language=language,
        prompt_version=prompt_version,
        input_fingerprint=deterministic_input_fingerprint(significant_input),
        input_snapshot=build_compact_snapshot(
            snapshot_source,
            include_fields=snapshot_fields,
        ),
    )
    session.add(analysis)
    try:
        if commit:
            session.commit()
            session.refresh(analysis)
        else:
            session.flush()
    except IntegrityError as error:
        session.rollback()
        active = session.scalar(
            select(AIAnalysis.id).where(
                AIAnalysis.deal_id == deal_id,
                AIAnalysis.function_type == function_type,
                AIAnalysis.status.in_(
                    (AIAnalysisStatus.QUEUED, AIAnalysisStatus.RUNNING)
                ),
            )
        )
        if active is not None:
            raise DuplicateInFlightOperationError from error
        raise AIOperationPersistenceError from error
    except SQLAlchemyError as error:
        session.rollback()
        raise AIOperationPersistenceError from error
    return analysis


def mark_queued_analysis_dispatch_failed(
    session: Session, analysis: AIAnalysis, *, commit: bool = True
) -> AIAnalysis:
    if analysis.status is not AIAnalysisStatus.QUEUED:
        return analysis
    finished_at = utc_now()
    analysis.status = AIAnalysisStatus.FAILED
    analysis.started_at = finished_at
    analysis.finished_at = finished_at
    analysis.duration_ms = 0
    analysis.error_category = AIErrorCategory.PROVIDER_UNAVAILABLE
    if commit:
        _commit(session)
    else:
        session.flush()
    return analysis


def execute_analysis(
    session: Session,
    *,
    analysis: AIAnalysis,
    provider: AIProvider,
    request: StructuredProviderRequest,
    response_model: type[BaseModel],
    retry_policy: RetryPolicy,
    sleeper: Callable[[float], None] = sleep,
    clock: Callable[[], datetime] = utc_now,
    result_transform: Callable[[BaseModel], BaseModel] | None = None,
) -> AIAnalysis:
    if analysis.status is not AIAnalysisStatus.QUEUED:
        raise InvalidAIOperationTransitionError

    frozen_request = request.model_copy(deep=True)
    started_at = clock()
    analysis.status = AIAnalysisStatus.RUNNING
    analysis.started_at = started_at
    _commit(session)

    maximum_attempts = retry_policy.max_retries + 1
    for attempt_number in range(1, maximum_attempts + 1):
        analysis.attempt_count = attempt_number
        _commit(session)
        try:
            provider_result = provider.generate_structured(
                frozen_request.model_copy(deep=True),
                response_model,
            )
            analysis.actual_model = provider_result.actual_model
            analysis.provider_usage = provider_result.usage
            validated = response_model.model_validate(provider_result.result)
            persisted_result = result_transform(validated) if result_transform else validated
        except ValidationError:
            return _finish_failed(
                session,
                analysis=analysis,
                category=AIErrorCategory.INVALID_STRUCTURED_RESPONSE,
                finished_at=clock(),
            )
        except ProviderFailure as failure:
            if failure.retryable and attempt_number < maximum_attempts:
                sleeper(retry_policy.delay_before_retry(attempt_number))
                continue
            analysis.actual_model = failure.actual_model
            analysis.provider_usage = failure.usage
            return _finish_failed(
                session,
                analysis=analysis,
                category=failure.category,
                finished_at=clock(),
            )

        finished_at = clock()
        analysis.status = AIAnalysisStatus.SUCCESS
        analysis.result_payload = persisted_result.model_dump(mode="json")
        analysis.error_category = None
        analysis.finished_at = finished_at
        analysis.duration_ms = _duration_ms(started_at, finished_at)
        _commit(session)
        return analysis

    raise AssertionError("AI retry loop ended without a terminal result")


def _finish_failed(
    session: Session,
    *,
    analysis: AIAnalysis,
    category: AIErrorCategory,
    finished_at: datetime,
) -> AIAnalysis:
    if analysis.started_at is None:
        raise InvalidAIOperationTransitionError
    analysis.status = AIAnalysisStatus.FAILED
    analysis.result_payload = None
    analysis.error_category = category
    analysis.finished_at = finished_at
    analysis.duration_ms = _duration_ms(analysis.started_at, finished_at)
    analysis.is_outdated = False
    _commit(session)
    return analysis


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    return max(0, round((finished_at - started_at).total_seconds() * 1000))


def _commit(session: Session) -> None:
    try:
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        raise AIOperationPersistenceError from error
