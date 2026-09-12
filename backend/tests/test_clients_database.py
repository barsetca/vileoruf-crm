import asyncio
import os
from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.core.security import create_access_token, hash_password
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Client, ClientStatus, Deal, PipelineStage, User, UserRole


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)


@pytest.fixture
def isolated_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[sessionmaker[Session]]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_clients_api_test_{uuid4().hex}"
    maintenance_engine = create_engine(
        source_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    isolated_url = source_url.set(database=database_name)
    isolated_engine = None
    database_created = False

    try:
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
        database_created = True
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("DATABASE_URL", isolated_url.render_as_string(False))
        get_settings.cache_clear()
        command.upgrade(Config("backend/alembic.ini"), "head")
        isolated_engine = create_engine(isolated_url, pool_pre_ping=True)
        session_factory = sessionmaker(
            bind=isolated_engine,
            autoflush=False,
            expire_on_commit=False,
        )

        def override_db():
            with session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        yield session_factory
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        if isolated_engine is not None:
            isolated_engine.dispose()
        if database_created:
            with maintenance_engine.connect() as connection:
                connection.exec_driver_sql(
                    f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'
                )
        maintenance_engine.dispose()


def test_clients_api_end_to_end_on_postgresql(
    isolated_session_factory: sessionmaker[Session],
) -> None:
    admin_id = uuid4()
    manager_id = uuid4()
    with isolated_session_factory() as session:
        session.add_all(
            [
                User(
                    id=admin_id,
                    email="clients-api-admin@example.test",
                    password_hash=hash_password("synthetic clients admin password"),
                    display_name="Synthetic Clients Admin",
                    role=UserRole.ADMIN,
                    is_active=True,
                ),
                User(
                    id=manager_id,
                    email="clients-api-manager@example.test",
                    password_hash=hash_password("synthetic clients manager password"),
                    display_name="Synthetic Clients Manager",
                    role=UserRole.MANAGER,
                    is_active=True,
                ),
            ]
        )
        session.commit()

    admin_headers = {"Authorization": f"Bearer {create_access_token(admin_id)}"}
    manager_headers = {
        "Authorization": f"Bearer {create_access_token(manager_id)}"
    }

    async def flow() -> tuple[UUID, UUID]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            empty = await client.get("/clients", headers=admin_headers)
            assert empty.status_code == 200
            assert empty.json() == []

            admin_created = await client.post(
                "/clients",
                headers=admin_headers,
                json={
                    "name": "  First Synthetic Client  ",
                    "contact_person": "First Contact",
                    "email": "shared-client@example.test",
                    "phone": "+10000000001",
                    "telegram": "first_synthetic",
                    "whatsapp": "+10000000001",
                    "company": "Synthetic Company One",
                    "lead_source": "Synthetic Referral",
                    "notes": "Initial technical note",
                },
            )
            assert admin_created.status_code == 201
            first = admin_created.json()
            assert first["name"] == "First Synthetic Client"
            assert first["status"] == "CUSTOMER"
            assert "deals" not in first

            manager_created = await client.post(
                "/clients",
                headers=manager_headers,
                json={
                    "name": "Second Synthetic Client",
                    "email": "shared-client@example.test",
                },
            )
            assert manager_created.status_code == 409

            for payload in (
                {"name": "Lifecycle Bypass", "status": "CLIENT"},
                {"name": "Managed ID", "id": str(uuid4())},
                {
                    "name": "Managed Timestamp",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            ):
                assert (
                    await client.post("/clients", headers=admin_headers, json=payload)
                ).status_code == 422

            manager_get = await client.get(
                f"/clients/{first['id']}", headers=manager_headers
            )
            assert manager_get.status_code == 200

            listing = await client.get("/clients", headers=manager_headers)
            assert listing.status_code == 200
            assert [item["id"] for item in listing.json()] == [first["id"]]
            assert (await client.get("/clients?limit=1", headers=admin_headers)).json()[0]["id"] == first["id"]

            for query in ("limit=0", "limit=101", "offset=-1"):
                assert (
                    await client.get(f"/clients?{query}", headers=admin_headers)
                ).status_code == 422

            manager_patch = await client.patch(
                f"/clients/{first['id']}",
                headers=manager_headers,
                json={"contact_person": "Updated Contact"},
            )
            assert manager_patch.status_code == 200
            updated = manager_patch.json()
            assert updated["contact_person"] == "Updated Contact"
            assert updated["name"] == first["name"]
            assert updated["email"] == first["email"]
            assert updated["status"] == "CUSTOMER"
            assert updated["created_at"] == first["created_at"]

            for payload in (
                {},
                {"status": "CLIENT"},
                {"id": str(uuid4())},
                {"updated_at": datetime.now(timezone.utc).isoformat()},
                {"name": None},
            ):
                assert (
                    await client.patch(
                        f"/clients/{first['id']}",
                        headers=admin_headers,
                        json=payload,
                    )
                ).status_code == 422

            unknown_id = uuid4()
            assert (
                await client.get(f"/clients/{unknown_id}", headers=admin_headers)
            ).status_code == 404
            assert (
                await client.patch(
                    f"/clients/{unknown_id}",
                    headers=manager_headers,
                    json={"name": "Missing"},
                )
            ).status_code == 404
            assert (
                await client.get("/clients/not-a-uuid", headers=admin_headers)
            ).status_code == 422
            assert (
                await client.delete(
                    f"/clients/{first['id']}", headers=admin_headers
                )
            ).status_code == 405

            return UUID(first["id"]), UUID(first["id"])

    first_id, second_id = asyncio.run(flow())

    with isolated_session_factory() as session:
        first = session.get(Client, first_id)
        second = session.get(Client, second_id)
        assert first is not None and second is not None
        assert first.status is ClientStatus.CUSTOMER
        assert second.status is ClientStatus.CUSTOMER
        assert first.contact_person == "Updated Contact"
        assert session.scalar(select(func.count()).select_from(Client)) == 1
        assert session.scalar(select(func.count()).select_from(Deal)) == 0
        assert session.scalar(select(func.count()).select_from(PipelineStage)) == 0
