from collections.abc import Iterator
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from pydantic import Field

from backend.app.models import (
    AIAnalysis,
    AIAnalysisStatus,
    AIErrorCategory,
    AIFunctionType,
    AIResultLanguage,
)
from backend.app.schemas.ai import StrictAIResult
from backend.app.services.ai.operations import RetryPolicy, execute_analysis
from backend.app.services.ai.provider import (
    ProviderFailure,
    ProviderResult,
    StructuredProviderRequest,
)


class SyntheticResult(StrictAIResult):
    score: int = Field(ge=0, le=100)


class _UnitSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _SequenceProvider:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = iter(outcomes)
        self.requests: list[StructuredProviderRequest] = []
        self.received_payloads: list[dict[str, Any]] = []

    def generate_structured(
        self,
        request: StructuredProviderRequest,
        response_model: type[SyntheticResult],
    ) -> ProviderResult[SyntheticResult]:
        self.requests.append(request)
        self.received_payloads.append(deepcopy(request.untrusted_business_data))
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            request.untrusted_business_data["mutated_by_provider"] = True
            raise outcome
        return outcome


def _queued_analysis() -> AIAnalysis:
    return AIAnalysis(
        id=uuid4(),
        deal_id=uuid4(),
        function_type=AIFunctionType.LEAD_SCORING,
        status=AIAnalysisStatus.QUEUED,
        language=AIResultLanguage.RU,
        prompt_version="foundation-test-v1",
        input_fingerprint="f" * 64,
        input_snapshot={"budget": "1200"},
        is_outdated=False,
        attempt_count=0,
    )


def _request() -> StructuredProviderRequest:
    return StructuredProviderRequest(
        model="gpt-5.4-mini",
        trusted_instructions="Return the required schema.",
        untrusted_business_data={"deal": {"budget": 1200}},
    )


def _clock() -> Iterator[datetime]:
    started = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
    yield started
    yield started + timedelta(milliseconds=125)


def test_valid_structured_result_is_the_only_success_path() -> None:
    analysis = _queued_analysis()
    session = _UnitSession()
    provider = _SequenceProvider(
        [
            ProviderResult(
                result={"score": 73},
                actual_model="gpt-5.4-mini-2026-08-01",
                usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            )
        ]
    )
    clock_values = _clock()

    result = execute_analysis(
        session,  # type: ignore[arg-type]
        analysis=analysis,
        provider=provider,
        request=_request(),
        response_model=SyntheticResult,
        retry_policy=RetryPolicy(),
        sleeper=lambda _: None,
        clock=lambda: next(clock_values),
    )

    assert result is analysis
    assert result.status is AIAnalysisStatus.SUCCESS
    assert result.result_payload == {"score": 73}
    assert result.error_category is None
    assert result.actual_model == "gpt-5.4-mini-2026-08-01"
    assert result.attempt_count == 1
    assert result.duration_ms == 125


def test_invalid_structured_result_becomes_failed_without_fake_result() -> None:
    analysis = _queued_analysis()
    clock_values = _clock()

    result = execute_analysis(
        _UnitSession(),  # type: ignore[arg-type]
        analysis=analysis,
        provider=_SequenceProvider(
            [
                ProviderResult(
                    result={"score": 101},
                    actual_model="gpt-5.4-mini",
                    usage={"total_tokens": 9},
                )
            ]
        ),
        request=_request(),
        response_model=SyntheticResult,
        retry_policy=RetryPolicy(),
        sleeper=lambda _: None,
        clock=lambda: next(clock_values),
    )

    assert result.status is AIAnalysisStatus.FAILED
    assert result.error_category is AIErrorCategory.INVALID_STRUCTURED_RESPONSE
    assert result.result_payload is None
    assert result.attempt_count == 1
    assert result.actual_model == "gpt-5.4-mini"
    assert result.provider_usage == {"total_tokens": 9}


def test_transient_failures_retry_twice_on_one_row_with_frozen_context() -> None:
    analysis = _queued_analysis()
    timeout = ProviderFailure(AIErrorCategory.PROVIDER_TIMEOUT, retryable=True)
    unavailable = ProviderFailure(
        AIErrorCategory.PROVIDER_UNAVAILABLE, retryable=True
    )
    provider = _SequenceProvider(
        [
            timeout,
            unavailable,
            ProviderResult(result={"score": 80}, actual_model="gpt-5.4-mini"),
        ]
    )
    delays: list[float] = []
    clock_values = _clock()

    result = execute_analysis(
        _UnitSession(),  # type: ignore[arg-type]
        analysis=analysis,
        provider=provider,
        request=_request(),
        response_model=SyntheticResult,
        retry_policy=RetryPolicy(max_retries=2, backoff_seconds=2),
        sleeper=delays.append,
        clock=lambda: next(clock_values),
    )

    assert result is analysis
    assert result.id == analysis.id
    assert result.status is AIAnalysisStatus.SUCCESS
    assert result.attempt_count == 3
    assert delays == [2, 4]
    assert len(provider.requests) == 3
    assert all(
        "mutated_by_provider" not in payload for payload in provider.received_payloads
    )


def test_configuration_failure_is_not_retried() -> None:
    analysis = _queued_analysis()
    provider = _SequenceProvider(
        [ProviderFailure(AIErrorCategory.CONFIGURATION_ERROR, retryable=False)]
    )
    clock_values = _clock()
    delays: list[float] = []

    result = execute_analysis(
        _UnitSession(),  # type: ignore[arg-type]
        analysis=analysis,
        provider=provider,
        request=_request(),
        response_model=SyntheticResult,
        retry_policy=RetryPolicy(),
        sleeper=delays.append,
        clock=lambda: next(clock_values),
    )

    assert result.status is AIAnalysisStatus.FAILED
    assert result.error_category is AIErrorCategory.CONFIGURATION_ERROR
    assert result.result_payload is None
    assert result.attempt_count == 1
    assert len(provider.requests) == 1
    assert delays == []


def test_exhausted_transient_retries_end_as_failed_on_the_same_row() -> None:
    analysis = _queued_analysis()
    provider = _SequenceProvider(
        [
            ProviderFailure(AIErrorCategory.PROVIDER_TIMEOUT, retryable=True),
            ProviderFailure(AIErrorCategory.PROVIDER_TIMEOUT, retryable=True),
            ProviderFailure(AIErrorCategory.PROVIDER_TIMEOUT, retryable=True),
        ]
    )
    clock_values = _clock()

    result = execute_analysis(
        _UnitSession(),  # type: ignore[arg-type]
        analysis=analysis,
        provider=provider,
        request=_request(),
        response_model=SyntheticResult,
        retry_policy=RetryPolicy(max_retries=2, backoff_seconds=1),
        sleeper=lambda _: None,
        clock=lambda: next(clock_values),
    )

    assert result is analysis
    assert result.status is AIAnalysisStatus.FAILED
    assert result.error_category is AIErrorCategory.PROVIDER_TIMEOUT
    assert result.result_payload is None
    assert result.attempt_count == 3
    assert len(provider.requests) == 3
