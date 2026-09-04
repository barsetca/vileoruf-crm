import asyncio
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.api.ai import email_draft_router
from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.schemas.ai import EmailDraftAIResult, EmailDraftGenerationLaunch
from backend.app.services.ai.email_draft import EmailDraftGenerationForbiddenError, InvalidSelectedNBAError
from backend.app.services.ai.operations import DuplicateInFlightOperationError
from backend.app.services.ai.runtime_settings import AIIsDisabledError


@pytest.fixture(autouse=True)
def isolated_dependencies():
    async def db(): return object()
    async def reject(): raise HTTPException(status_code=401, detail="Authentication required")
    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_current_user] = reject
    yield
    app.dependency_overrides.clear()


def _request(method, path, payload=None):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, json=payload)
    return asyncio.run(send())


def test_email_result_is_strict_bounded_and_allows_only_client_placeholder():
    valid = EmailDraftAIResult.model_validate({"subject": "Hello {{client_name}}", "body": "A concise message."})
    assert valid.security_warning is None
    for payload in (
        {"subject": "", "body": "text"},
        {"subject": "subject", "body": ""},
        {"subject": "x" * 999, "body": "text"},
        {"subject": "subject", "body": "x" * 20_001},
        {"subject": "{{other}}", "body": "text"},
        {"subject": "subject", "body": "text", "sent": True},
    ):
        with pytest.raises(ValidationError): EmailDraftAIResult.model_validate(payload)


def test_email_launch_requires_purpose_and_complete_nba_reference():
    with pytest.raises(ValidationError): EmailDraftGenerationLaunch(purpose=" ")
    with pytest.raises(ValidationError): EmailDraftGenerationLaunch(purpose="Follow up", nba_analysis_id=uuid4())


def test_email_routes_are_typed_authenticated_and_have_no_send_path():
    deal_id = uuid4()
    for method, path, payload in (("GET", f"/deals/{deal_id}/email-draft", None), ("POST", f"/deals/{deal_id}/email-draft", {"purpose": "Follow up"}), ("GET", f"/deals/{deal_id}/email-drafts", None), ("POST", f"/deals/{deal_id}/email-drafts", {"subject": "s", "body": "b", "purpose": "p"})):
        assert _request(method, path, payload).status_code == 401
    paths = app.openapi()["paths"]
    assert set(paths["/deals/{deal_id}/email-draft"]) == {"get", "post"}
    assert set(paths["/deals/{deal_id}/email-drafts/{draft_id}"]) == {"get", "patch", "delete"}
    assert not any("send" in path.lower() for path in paths)


@pytest.mark.parametrize("service_error,status_code", [(EmailDraftGenerationForbiddenError(), 403), (AIIsDisabledError(), 409), (InvalidSelectedNBAError(), 422), (DuplicateInFlightOperationError(), 409)])
def test_email_launch_maps_authorization_and_conflicts(monkeypatch, service_error, status_code):
    monkeypatch.setattr(email_draft_router, "launch_email_draft", lambda *args, **kwargs: (_ for _ in ()).throw(service_error))
    with pytest.raises(HTTPException) as error:
        email_draft_router.post_email_generation(uuid4(), EmailDraftGenerationLaunch(purpose="Follow up"), object(), object())
    assert error.value.status_code == status_code
