import asyncio
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.schemas.clients import ClientCreate, ClientUpdate


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


def test_clients_endpoints_require_authentication() -> None:
    client_id = uuid4()
    requests = [
        ("POST", "/clients", {"name": "Synthetic Client"}),
        ("GET", "/clients", None),
        ("GET", f"/clients/{client_id}", None),
        ("PATCH", f"/clients/{client_id}", {"name": "Updated"}),
    ]

    for method, path, payload in requests:
        response = request(method, path, json=payload)
        assert response.status_code == 401
        assert response.json() == {"detail": "Authentication required"}
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("forbidden_field", ["status", "id", "created_at", "updated_at"])
def test_client_write_schemas_forbid_server_managed_fields(
    forbidden_field: str,
) -> None:
    value = "CLIENT" if forbidden_field == "status" else str(uuid4())

    with pytest.raises(ValidationError):
        ClientCreate(name="Synthetic Client", **{forbidden_field: value})
    with pytest.raises(ValidationError):
        ClientUpdate(**{forbidden_field: value})


def test_client_update_requires_a_change_and_non_null_name() -> None:
    with pytest.raises(ValidationError):
        ClientUpdate()
    with pytest.raises(ValidationError):
        ClientUpdate(name=None)


def test_openapi_contains_only_approved_client_operations() -> None:
    paths = app.openapi()["paths"]

    assert set(paths["/clients"]) == {"get", "post"}
    assert set(paths["/clients/{client_id}"]) == {"get", "patch"}
    assert "delete" not in paths["/clients/{client_id}"]
