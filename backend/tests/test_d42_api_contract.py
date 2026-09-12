import asyncio
from datetime import date, timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.api.dependencies import get_current_user, require_admin
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import User, UserRole
from backend.app.schemas.business import LeadScoringSettingsPayload
from backend.app.schemas.deals import DealCreate, DealUpdate
from backend.app.schemas.public_requests import PublicRequestCreate


@pytest.fixture(autouse=True)
def isolated_dependencies():
    async def db(): return object()
    async def reject(): raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate":"Bearer"})
    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_current_user] = reject
    yield
    app.dependency_overrides.clear()


def request(method, path, payload=None):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, json=payload)
    return asyncio.run(send())


def test_business_and_lead_scoring_endpoints_require_authentication():
    deal_id = uuid4()
    for method, path, payload in [
        ("GET", "/business/categories", None), ("POST", "/business/categories", {}),
        ("GET", "/business/services", None), ("POST", "/business/services", {}),
        ("GET", "/business/lead-scoring-settings", None), ("PUT", "/business/lead-scoring-settings", {}),
        ("GET", f"/deals/{deal_id}/lead-scoring", None), ("POST", f"/deals/{deal_id}/lead-scoring", {"language":"EN"}),
    ]:
        response = request(method, path, payload)
        assert response.status_code == 401


def test_manager_cannot_manage_business_settings_and_admin_dependency_allows_admin():
    manager = User(email="manager@example.test", password_hash="synthetic", display_name="Manager", role=UserRole.MANAGER, is_active=True)
    admin = User(email="admin@example.test", password_hash="synthetic", display_name="Admin", role=UserRole.ADMIN, is_active=True)
    protected = {
        ("/business/categories", "POST"),
        ("/business/categories/{category_id}", "PATCH"),
        ("/business/services", "POST"),
        ("/business/services/{service_id}", "PATCH"),
        ("/business/lead-scoring-settings", "GET"),
        ("/business/lead-scoring-settings", "PUT"),
    }
    wired = {
        (route.path, method)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if any(dependency.call is require_admin for dependency in getattr(getattr(route, "dependant", None), "dependencies", []))
    }
    assert protected.issubset(wired)
    assert require_admin(admin) is admin
    with pytest.raises(HTTPException) as error:
        require_admin(manager)
    assert error.value.status_code == 403


def test_d42_input_validation_and_past_date_rules():
    yesterday = date.today() - timedelta(days=1)
    with pytest.raises(ValidationError): DealCreate(client_id=uuid4(), stage_id=uuid4(), name="Deal", estimated_budget="-0.01")
    with pytest.raises(ValidationError): DealCreate(client_id=uuid4(), stage_id=uuid4(), name="Deal", deadline=yesterday)
    with pytest.raises(ValidationError): DealUpdate(deadline=yesterday)
    with pytest.raises(ValidationError): DealUpdate(manager_effort_estimate=0)
    with pytest.raises(ValidationError): PublicRequestCreate(name="Lead", deal_name="Deal", service_id=uuid4(), deadline=yesterday, personal_data_consent=True)
    with pytest.raises(ValidationError): PublicRequestCreate(name="Lead", deal_name="Deal", service_id=uuid4())
    with pytest.raises(ValidationError): PublicRequestCreate(name="Lead", deal_name="Deal", service_id=uuid4(), personal_data_consent=1)


def test_weight_and_scale_validation_is_backend_authoritative():
    base = {"service_fit_weight":30,"commercial_value_weight":30,"lead_quality_weight":15,"feasibility_weight":25,"commercial_value_scale":[{"ratio":"0.5","score":0},{"ratio":"1.5","score":100}]}
    assert LeadScoringSettingsPayload.model_validate(base).service_fit_weight == 30
    for bad in [
        {**base,"feasibility_weight":24},
        {**base,"feasibility_weight":26},
        {**base,"commercial_value_scale":[{"ratio":"1","score":0},{"ratio":"1","score":100}]},
        {**base,"commercial_value_scale":[{"ratio":"1","score":100},{"ratio":"2","score":0}]},
    ]:
        with pytest.raises(ValidationError): LeadScoringSettingsPayload.model_validate(bad)


def test_openapi_exposes_typed_d42_surface_without_generic_ai_api():
    paths = app.openapi()["paths"]
    assert set(paths["/business/categories"]) == {"get","post"}
    assert set(paths["/business/categories/{category_id}"]) == {"patch"}
    assert set(paths["/business/services"]) == {"get","post"}
    assert set(paths["/business/services/{service_id}"]) == {"patch"}
    assert set(paths["/business/lead-scoring-settings"]) == {"get","put"}
    assert set(paths["/deals/{deal_id}/lead-scoring"]) == {"get","post"}
    assert "/ai/launch" not in paths
