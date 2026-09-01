import asyncio

import httpx
import pytest
from fastapi import HTTPException

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app


@pytest.fixture(autouse=True)
def isolate_dependencies():
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


def request(path: str) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(path)

    return asyncio.run(send())


@pytest.mark.parametrize("path", ["/pipeline-stages", "/employees/reference"])
def test_reference_data_endpoints_require_authentication(path: str) -> None:
    response = request(path)

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_openapi_contains_only_read_only_reference_operations() -> None:
    paths = app.openapi()["paths"]

    assert set(paths["/pipeline-stages"]) == {"get"}
    assert set(paths["/employees/reference"]) == {"get"}
