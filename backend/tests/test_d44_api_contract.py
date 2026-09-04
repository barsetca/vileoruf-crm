import asyncio
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.api.dependencies import get_current_user
from backend.app.api.ai import next_best_action_router
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.schemas.ai import NextBestActionAIResult, NextBestActionLaunch
from backend.app.schemas.deals import DealCreate
from backend.app.services.ai.next_best_action import (
    ClosedDealNextBestActionError,
    NextBestActionForbiddenError,
)
from backend.app.services.ai.operations import DuplicateInFlightOperationError
from backend.app.services.ai.runtime_settings import AIIsDisabledError


@pytest.fixture(autouse=True)
def isolated_dependencies():
    async def db():
        return object()

    async def reject():
        raise HTTPException(status_code=401, detail="Authentication required")

    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_current_user] = reject
    yield
    app.dependency_overrides.clear()


def _request(method: str, path: str, payload: dict | None = None):
    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.request(method, path, json=payload)

    return asyncio.run(send())


def _action(rank: int) -> dict:
    return {
        "rank": rank,
        "priority": "HIGH",
        "action": f"Action {rank}",
        "reason": "Supported by current CRM evidence.",
        "timing": "Today",
    }


@pytest.mark.parametrize("count", [1, 2, 3])
def test_next_best_action_accepts_one_to_three_ranked_actions(count):
    result = NextBestActionAIResult.model_validate(
        {
            "actions": [_action(rank) for rank in range(1, count + 1)],
            "summary": "Concise recommendation summary.",
            "security_warning": None,
        }
    )
    assert [item.rank for item in result.actions] == list(range(1, count + 1))


@pytest.mark.parametrize(
    "actions",
    [
        [],
        [_action(1), _action(2), _action(3), _action(3)],
        [_action(1), _action(1)],
        [_action(2)],
        [_action(1), _action(3)],
        [_action(2), _action(1)],
    ],
)
def test_next_best_action_rejects_invalid_action_counts_or_ranks(actions):
    with pytest.raises(ValidationError):
        NextBestActionAIResult.model_validate(
            {"actions": actions, "summary": "Invalid", "security_warning": None}
        )


def test_next_best_action_rejects_priority_extra_fields_and_oversized_text():
    for action in (
        {**_action(1), "priority": "CRITICAL"},
        {**_action(1), "executed": True},
        {**_action(1), "action": "x" * 501},
        {**_action(1), "reason": "x" * 1201},
        {**_action(1), "timing": "x" * 301},
    ):
        with pytest.raises(ValidationError):
            NextBestActionAIResult.model_validate(
                {"actions": [action], "summary": "Invalid"}
            )

    for payload in (
        {"actions": [_action(1)], "summary": "x" * 1201},
        {
            "actions": [_action(1)],
            "summary": "Valid",
            "security_warning": "x" * 1201,
        },
        {"actions": [_action(1)], "summary": "Valid", "executed": True},
    ):
        with pytest.raises(ValidationError):
            NextBestActionAIResult.model_validate(payload)


def test_next_best_action_security_warning_is_optional():
    result = NextBestActionAIResult.model_validate(
        {"actions": [_action(1)], "summary": "Valid without a warning."}
    )
    assert result.security_warning is None


def test_nba_endpoints_are_typed_and_authenticated():
    deal_id = uuid4()
    assert _request("GET", f"/deals/{deal_id}/next-best-action").status_code == 401
    assert _request(
        "POST", f"/deals/{deal_id}/next-best-action", {"language": "EN"}
    ).status_code == 401
    paths = app.openapi()["paths"]
    assert set(paths["/deals/{deal_id}/next-best-action"]) == {"get", "post"}
    assert "/ai/launch" not in paths


def test_employee_deal_creation_accepts_frozen_initial_analysis_language():
    payload = DealCreate(
        client_id=uuid4(),
        stage_id=uuid4(),
        name="New Deal",
        ai_analysis_language="ES",
    )
    assert payload.ai_analysis_language.value == "ES"


@pytest.mark.parametrize(
    "service_error,status_code",
    [
        (NextBestActionForbiddenError(), 403),
        (ClosedDealNextBestActionError(), 409),
        (AIIsDisabledError(), 409),
        (DuplicateInFlightOperationError(), 409),
    ],
)
def test_nba_launch_maps_authorization_and_conflict_errors(
    monkeypatch, service_error, status_code
):
    def fail(*args, **kwargs):
        raise service_error

    monkeypatch.setattr(next_best_action_router, "launch_next_best_action", fail)
    with pytest.raises(HTTPException) as error:
        next_best_action_router.post_next_best_action(
            uuid4(), NextBestActionLaunch(language="EN"), object(), object()
        )
    assert error.value.status_code == status_code
