import asyncio
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from redis.exceptions import ConnectionError

from backend.app.api.ai import dependencies as ai_dependencies
from backend.app.api.dependencies import get_current_user, require_admin
from backend.app.core.config import AIInfrastructureSettings
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import UserRole
from backend.app.schemas.ai_settings import AISettingsUpdate
from backend.app.services.ai.rate_limit import AIRateLimitExceeded, enforce_manual_ai_rate_limit
from backend.app.api.ai.dependencies import require_manual_ai_launch_quota
import backend.app.api.ai.router as lead_scoring_router
import backend.app.api.ai.deal_prediction_router as deal_prediction_router
import backend.app.api.ai.next_best_action_router as next_best_action_router
import backend.app.api.ai.email_draft_router as email_draft_router


@pytest.fixture(autouse=True)
def isolated_dependencies():
    async def db(): return object()
    async def reject(): raise HTTPException(status_code=401, detail="Authentication required")
    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_current_user] = reject
    yield
    app.dependency_overrides.clear()


def _request(path, method="GET", payload=None):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client: return await client.request(method, path, json=payload)
    return asyncio.run(send())


def test_settings_and_history_routes_are_typed_and_authenticated():
    assert _request("/settings/ai").status_code == 401
    assert _request("/ai-history").status_code == 401
    assert _request(f"/deals/{uuid4()}/ai-history").status_code == 401
    paths = app.openapi()["paths"]
    assert set(paths["/settings/ai"]) == {"get", "patch"}
    assert set(paths["/ai-history"]) == {"get"}
    assert set(paths["/deals/{deal_id}/ai-history"]) == {"get"}


def test_manager_cannot_read_or_mutate_ai_settings():
    manager = type("Manager", (), {"role":UserRole.MANAGER})()
    with pytest.raises(HTTPException) as error: require_admin(manager)
    assert error.value.status_code == 403


def test_manager_ai_settings_endpoints_return_403():
    async def manager(): return type("Manager", (), {"role":UserRole.MANAGER})()
    app.dependency_overrides[get_current_user] = manager
    assert _request("/settings/ai").status_code == 403
    assert _request("/settings/ai", "PATCH", {"ai_enabled":False}).status_code == 403


@pytest.mark.parametrize(
    "path,payload,module,launch_name",
    [
        ("/deals/{deal}/lead-scoring", {"language":"EN"}, lead_scoring_router, "launch_lead_scoring"),
        ("/deals/{deal}/deal-prediction", {"language":"EN"}, deal_prediction_router, "launch_deal_prediction"),
        ("/deals/{deal}/next-best-action", {"language":"EN"}, next_best_action_router, "launch_next_best_action"),
        ("/deals/{deal}/email-draft", {"purpose":"Follow up"}, email_draft_router, "launch_email_draft"),
    ],
)
def test_rate_limit_rejects_each_manual_endpoint_before_launch(path, payload, module, launch_name, monkeypatch):
    called = False
    async def user(): return type("User", (), {"id":uuid4()})()
    async def limited(): raise HTTPException(status_code=429, detail="Too many AI launch requests")
    def launch(*args, **kwargs):
        nonlocal called
        called = True
    app.dependency_overrides[get_current_user] = user
    app.dependency_overrides[require_manual_ai_launch_quota] = limited
    monkeypatch.setattr(module, launch_name, launch)
    response = _request(path.format(deal=uuid4()), "POST", payload)
    assert response.status_code == 429
    assert called is False


@pytest.mark.parametrize("payload", [{}, {"deal_prediction_validity_days":0}, {"next_best_action_validity_days":366}, {"ai_enabled":None}, {"analysis_model_override":" "}, {"unknown":True}])
def test_settings_schema_rejects_empty_invalid_or_excessive_updates(payload):
    with pytest.raises(ValidationError): AISettingsUpdate.model_validate(payload)


def test_model_override_null_is_an_explicit_reset():
    payload = AISettingsUpdate.model_validate({"analysis_model_override":None})
    assert payload.model_fields_set == {"analysis_model_override"}


class FakeRedis:
    def __init__(self): self.counts = {}; self.expires = {}; self.now = 0
    def eval(self, script, key_count, key, window):
        if self.expires.get(key, 0) <= self.now:
            self.counts.pop(key, None)
        self.counts[key] = self.counts.get(key, 0) + 1
        if self.counts[key] == 1: self.expires[key] = self.now + window
        return [self.counts[key], self.expires[key] - self.now]
    def advance(self, seconds): self.now += seconds


def _settings(requests=2):
    return AIInfrastructureSettings(celery_broker_url="redis://localhost:6379/0", celery_result_backend="redis://localhost:6379/1", ai_rate_limit_requests=requests, ai_rate_limit_window_seconds=60)


def test_rate_limit_boundary_shared_key_and_separate_identities():
    client = FakeRedis(); first = uuid4(); second = uuid4()
    enforce_manual_ai_rate_limit(first, infrastructure=_settings(), client=client)
    enforce_manual_ai_rate_limit(first, infrastructure=_settings(), client=client)
    with pytest.raises(AIRateLimitExceeded): enforce_manual_ai_rate_limit(first, infrastructure=_settings(), client=client)
    enforce_manual_ai_rate_limit(second, infrastructure=_settings(), client=client)
    assert len(client.counts) == 2 and all("@" not in key for key in client.counts)
    client.advance(60)
    enforce_manual_ai_rate_limit(first, infrastructure=_settings(), client=client)
    assert client.counts[next(key for key in client.counts if str(first) in key)] == 1


def test_rate_limiter_fails_open_and_http_dependency_maps_safe_429(caplog, monkeypatch):
    class BrokenRedis:
        def eval(self, *args): raise ConnectionError("secret redis details")
    enforce_manual_ai_rate_limit(uuid4(), infrastructure=_settings(), client=BrokenRedis())
    assert "secret redis details" not in caplog.text
    monkeypatch.setattr(ai_dependencies, "enforce_manual_ai_rate_limit", lambda user_id: (_ for _ in ()).throw(AIRateLimitExceeded(17)))
    with pytest.raises(HTTPException) as error: ai_dependencies.require_manual_ai_launch_quota(type("User", (), {"id":uuid4()})())
    assert error.value.status_code == 429 and error.value.headers == {"Retry-After":"17"}
    assert "Redis" not in error.value.detail
