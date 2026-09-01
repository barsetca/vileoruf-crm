import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.schemas.deals import DealCreate, DealTransition, DealUpdate


@pytest.fixture(autouse=True)
def isolate_database_dependency():
    async def override_db():
        return object()

    async def reject_authentication():
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = reject_authentication
    yield
    app.dependency_overrides.clear()


def request(method: str, path: str, *, json: dict | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json)

    return asyncio.run(send())


def test_deals_endpoints_require_authentication() -> None:
    deal_id = uuid4()
    create_payload = {
        "client_id": str(uuid4()),
        "stage_id": str(uuid4()),
        "name": "Synthetic Deal",
    }
    requests = [
        ("POST", "/deals", create_payload),
        ("GET", "/deals", None),
        ("GET", f"/deals/{deal_id}", None),
        ("PATCH", f"/deals/{deal_id}", {"name": "Updated"}),
        ("POST", f"/deals/{deal_id}/transition", {"stage_id": str(uuid4())}),
    ]

    for method, path, payload in requests:
        response = request(method, path, json=payload)
        assert response.status_code == 401
        assert response.json() == {"detail": "Authentication required"}
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("forbidden_field", ["id", "created_at", "updated_at"])
def test_deal_create_forbids_server_managed_fields(forbidden_field: str) -> None:
    with pytest.raises(ValidationError):
        DealCreate(
            client_id=uuid4(),
            stage_id=uuid4(),
            name="Synthetic Deal",
            **{forbidden_field: str(uuid4())},
        )


@pytest.mark.parametrize(
    "forbidden_field",
    ["id", "created_at", "updated_at", "client_id", "stage_id"],
)
def test_deal_update_forbids_controlled_fields(forbidden_field: str) -> None:
    value = (
        datetime.now(timezone.utc).isoformat()
        if forbidden_field.endswith("_at")
        else str(uuid4())
    )
    with pytest.raises(ValidationError):
        DealUpdate(**{forbidden_field: value})


def test_deal_update_and_probability_validation() -> None:
    with pytest.raises(ValidationError):
        DealUpdate()
    with pytest.raises(ValidationError):
        DealUpdate(name=None)
    with pytest.raises(ValidationError):
        DealUpdate(probability=-1)
    with pytest.raises(ValidationError):
        DealUpdate(probability=101)
    assert DealUpdate(probability=0).probability == 0
    assert DealUpdate(probability=100).probability == 100


def test_deal_transition_schema_accepts_only_stage_uuid() -> None:
    stage_id = uuid4()
    assert DealTransition(stage_id=stage_id).stage_id == stage_id
    with pytest.raises(ValidationError):
        DealTransition(stage_id="not-a-uuid")
    with pytest.raises(ValidationError):
        DealTransition(stage_id=stage_id, name="Won")


def test_openapi_contains_only_approved_deal_operations() -> None:
    paths = app.openapi()["paths"]

    assert set(paths["/deals"]) == {"get", "post"}
    assert set(paths["/deals/{deal_id}"]) == {"get", "patch"}
    assert "delete" not in paths["/deals/{deal_id}"]
    assert set(paths["/deals/{deal_id}/transition"]) == {"post"}
