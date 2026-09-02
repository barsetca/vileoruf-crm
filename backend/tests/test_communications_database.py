import asyncio
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.core.security import create_access_token, hash_password
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import (
    Client,
    Communication,
    CommunicationStatus,
    Deal,
    PipelineStage,
    User,
    UserRole,
)


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)


@pytest.fixture
def isolated_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[sessionmaker[Session]]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_communications_api_test_{uuid4().hex}"
    maintenance_engine = create_engine(
        source_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
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
            bind=isolated_engine, autoflush=False, expire_on_commit=False
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


def test_communications_api_contract_on_postgresql(
    isolated_session_factory: sessionmaker[Session],
) -> None:
    admin_id, manager_a_id, manager_b_id, admin_assignee_id = [
        uuid4() for _ in range(4)
    ]
    client_a_id, client_b_id = uuid4(), uuid4()
    own_deal_id, other_deal_id, unassigned_deal_id, admin_deal_id = [
        uuid4() for _ in range(4)
    ]
    stage_id = uuid4()
    with isolated_session_factory() as session:
        session.add_all(
            [
                User(
                    id=admin_id,
                    email="communications-admin@example.test",
                    password_hash=hash_password("synthetic communications admin"),
                    display_name="Communications Admin",
                    role=UserRole.ADMIN,
                ),
                User(
                    id=manager_a_id,
                    email="communications-manager-a@example.test",
                    password_hash=hash_password("synthetic communications manager a"),
                    display_name="Communications Manager A",
                    role=UserRole.MANAGER,
                ),
                User(
                    id=manager_b_id,
                    email="communications-manager-b@example.test",
                    password_hash=hash_password("synthetic communications manager b"),
                    display_name="Communications Manager B",
                    role=UserRole.MANAGER,
                ),
                User(
                    id=admin_assignee_id,
                    email="communications-admin-assignee@example.test",
                    password_hash=hash_password("synthetic communications assignee"),
                    display_name="Communications Admin Assignee",
                    role=UserRole.ADMIN,
                ),
                Client(id=client_a_id, name="Communications Client A"),
                Client(id=client_b_id, name="Communications Client B"),
                PipelineStage(id=stage_id, name="Communications Stage", position=1),
                Deal(
                    id=own_deal_id,
                    name="Manager A Deal",
                    client_id=client_a_id,
                    stage_id=stage_id,
                    responsible_user_id=manager_a_id,
                ),
                Deal(
                    id=other_deal_id,
                    name="Manager B Deal",
                    client_id=client_a_id,
                    stage_id=stage_id,
                    responsible_user_id=manager_b_id,
                ),
                Deal(
                    id=unassigned_deal_id,
                    name="Unassigned Deal",
                    client_id=client_a_id,
                    stage_id=stage_id,
                ),
                Deal(
                    id=admin_deal_id,
                    name="Admin Deal",
                    client_id=client_a_id,
                    stage_id=stage_id,
                    responsible_user_id=admin_assignee_id,
                ),
            ]
        )
        session.commit()

    headers = {
        "admin": {"Authorization": f"Bearer {create_access_token(admin_id)}"},
        "manager_a": {
            "Authorization": f"Bearer {create_access_token(manager_a_id)}"
        },
        "manager_b": {
            "Authorization": f"Bearer {create_access_token(manager_b_id)}"
        },
    }
    now = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)

    def payload(
        client_id: UUID,
        *,
        occurred_at: datetime,
        deal_id: UUID | None = None,
        content: str = "Recorded communication",
    ) -> dict[str, str]:
        values = {
            "client_id": str(client_id),
            "channel": "MANUAL",
            "direction": "OUTGOING",
            "content": content,
            "occurred_at": occurred_at.isoformat(),
        }
        if deal_id is not None:
            values["deal_id"] = str(deal_id)
        return values

    async def flow() -> list[UUID]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            anonymous_payload = payload(client_a_id, occurred_at=now)
            assert (await client.post("/communications", json=anonymous_payload)).status_code == 401
            assert (await client.get("/communications")).status_code == 401
            assert (await client.get(f"/communications/{uuid4()}")).status_code == 401

            admin_client = await client.post(
                "/communications",
                headers=headers["admin"],
                json=payload(client_a_id, occurred_at=now, content="Admin client history"),
            )
            assert admin_client.status_code == 201
            admin_client_data = admin_client.json()
            assert admin_client_data["deal_id"] is None
            assert admin_client_data["status"] == "RECORDED"

            admin_deal = await client.post(
                "/communications",
                headers=headers["admin"],
                json=payload(
                    client_a_id,
                    deal_id=other_deal_id,
                    occurred_at=now + timedelta(minutes=1),
                    content="Admin deal history",
                ),
            )
            assert admin_deal.status_code == 201

            manager_client = await client.post(
                "/communications",
                headers=headers["manager_a"],
                json=payload(
                    client_b_id,
                    occurred_at=now + timedelta(minutes=2),
                    content="Manager client history",
                ),
            )
            assert manager_client.status_code == 201

            manager_own = await client.post(
                "/communications",
                headers=headers["manager_a"],
                json=payload(
                    client_a_id,
                    deal_id=own_deal_id,
                    occurred_at=now + timedelta(minutes=3),
                    content="Manager own deal history",
                ),
            )
            assert manager_own.status_code == 201

            for forbidden_deal_id in (
                other_deal_id,
                unassigned_deal_id,
                admin_deal_id,
            ):
                response = await client.post(
                    "/communications",
                    headers=headers["manager_a"],
                    json=payload(
                        client_a_id,
                        deal_id=forbidden_deal_id,
                        occurred_at=now,
                    ),
                )
                assert response.status_code == 403

            mismatch = await client.post(
                "/communications",
                headers=headers["admin"],
                json=payload(client_b_id, deal_id=own_deal_id, occurred_at=now),
            )
            assert mismatch.status_code == 422
            assert (await client.post(
                "/communications",
                headers=headers["admin"],
                json=payload(uuid4(), occurred_at=now),
            )).status_code == 404
            assert (await client.post(
                "/communications",
                headers=headers["admin"],
                json=payload(client_a_id, deal_id=uuid4(), occurred_at=now),
            )).status_code == 404

            unsupported_status = await client.post(
                "/communications",
                headers=headers["admin"],
                json={**payload(client_a_id, occurred_at=now), "status": "FAILED"},
            )
            assert unsupported_status.status_code == 422

            created_ids = [
                UUID(admin_client_data["id"]),
                UUID(admin_deal.json()["id"]),
                UUID(manager_client.json()["id"]),
                UUID(manager_own.json()["id"]),
            ]
            for actor in ("admin", "manager_a", "manager_b"):
                listing = await client.get("/communications", headers=headers[actor])
                assert listing.status_code == 200
                assert [item["id"] for item in listing.json()] == [
                    str(created_ids[3]),
                    str(created_ids[2]),
                    str(created_ids[1]),
                    str(created_ids[0]),
                ]
                assert (await client.get(
                    f"/communications/{created_ids[1]}", headers=headers[actor]
                )).status_code == 200

            page = await client.get(
                "/communications?limit=2&offset=1", headers=headers["admin"]
            )
            assert page.status_code == 200
            assert [item["id"] for item in page.json()] == [
                str(created_ids[2]),
                str(created_ids[1]),
            ]
            for query in ("limit=0", "limit=101", "offset=-1"):
                assert (await client.get(
                    f"/communications?{query}", headers=headers["admin"]
                )).status_code == 422

            client_filter = await client.get(
                f"/communications?client_id={client_a_id}", headers=headers["admin"]
            )
            assert {item["id"] for item in client_filter.json()} == {
                str(created_ids[0]),
                str(created_ids[1]),
                str(created_ids[3]),
            }
            deal_filter = await client.get(
                f"/communications?deal_id={other_deal_id}", headers=headers["admin"]
            )
            assert [item["id"] for item in deal_filter.json()] == [
                str(created_ids[1])
            ]
            combined_filter = await client.get(
                f"/communications?client_id={client_a_id}&deal_id={own_deal_id}",
                headers=headers["admin"],
            )
            assert [item["id"] for item in combined_filter.json()] == [
                str(created_ids[3])
            ]

            assert (await client.patch(
                f"/communications/{created_ids[0]}", headers=headers["admin"], json={}
            )).status_code == 405
            assert (await client.delete(
                f"/communications/{created_ids[0]}", headers=headers["admin"]
            )).status_code == 405
            assert set(app.openapi()["paths"]["/communications/{communication_id}"]) == {
                "get"
            }
            return created_ids

    created_ids = asyncio.run(flow())
    with isolated_session_factory() as session:
        persisted = list(
            session.scalars(
                select(Communication).where(Communication.id.in_(created_ids))
            )
        )
        assert len(persisted) == 4
        assert {communication.status for communication in persisted} == {
            CommunicationStatus.RECORDED
        }
