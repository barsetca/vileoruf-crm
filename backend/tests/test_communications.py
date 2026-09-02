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
from backend.app.models import CommunicationChannel, CommunicationDirection
from backend.app.schemas.communications import CommunicationCreate


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
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.request(method, path, json=json)

    return asyncio.run(send())


def test_communications_endpoints_require_authentication() -> None:
    payload = {
        "client_id": str(uuid4()),
        "channel": "MANUAL",
        "direction": "OUTGOING",
        "content": "Synthetic history",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    for method, path, body in (
        ("POST", "/communications", payload),
        ("GET", "/communications", None),
        ("GET", f"/communications/{uuid4()}", None),
    ):
        response = request(method, path, json=body)
        assert response.status_code == 401
        assert response.json() == {"detail": "Authentication required"}
        assert response.headers["www-authenticate"] == "Bearer"


def test_communication_create_schema_allows_only_approved_business_fields() -> None:
    occurred_at = datetime.now(timezone.utc)
    payload = CommunicationCreate(
        client_id=uuid4(),
        channel=CommunicationChannel.MANUAL,
        direction=CommunicationDirection.OUTGOING,
        content="  Recorded history  ",
        occurred_at=occurred_at,
    )
    assert payload.deal_id is None
    assert payload.content == "Recorded history"
    assert payload.occurred_at == occurred_at

    for field, value in (
        ("id", str(uuid4())),
        ("status", "RECORDED"),
        ("created_at", occurred_at.isoformat()),
        ("provider_id", "external-id"),
    ):
        with pytest.raises(ValidationError):
            CommunicationCreate(
                client_id=uuid4(),
                channel="EMAIL",
                direction="INCOMING",
                content="History",
                occurred_at=occurred_at,
                **{field: value},
            )

    for occurred_at_value in (datetime.now(), "not-a-datetime"):
        with pytest.raises(ValidationError):
            CommunicationCreate(
                client_id=uuid4(),
                channel="EMAIL",
                direction="INCOMING",
                content="History",
                occurred_at=occurred_at_value,
            )


def test_openapi_exposes_append_only_communication_operations() -> None:
    paths = app.openapi()["paths"]

    assert set(paths["/communications"]) == {"get", "post"}
    assert set(paths["/communications/{communication_id}"]) == {"get"}
    assert "patch" not in paths["/communications/{communication_id}"]
    assert "delete" not in paths["/communications/{communication_id}"]
