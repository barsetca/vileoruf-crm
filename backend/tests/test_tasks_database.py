import asyncio
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.core.security import create_access_token, hash_password
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Client, Deal, PipelineStage, User, UserRole


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)


@pytest.fixture
def isolated_session_factory(monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker[Session]]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_tasks_api_test_{uuid4().hex}"
    maintenance_engine = create_engine(source_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    isolated_url = source_url.set(database=database_name)
    isolated_engine = None
    created = False
    try:
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
        created = True
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("DATABASE_URL", isolated_url.render_as_string(False))
        get_settings.cache_clear()
        command.upgrade(Config("backend/alembic.ini"), "head")
        isolated_engine = create_engine(isolated_url, pool_pre_ping=True)
        factory = sessionmaker(bind=isolated_engine, autoflush=False, expire_on_commit=False)

        def override_db():
            with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        yield factory
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        if isolated_engine is not None:
            isolated_engine.dispose()
        if created:
            with maintenance_engine.connect() as connection:
                connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
        maintenance_engine.dispose()


def test_tasks_api_contract_on_postgresql(isolated_session_factory: sessionmaker[Session]) -> None:
    admin_id, admin_b_id, manager_a_id, manager_b_id, inactive_id = [uuid4() for _ in range(5)]
    client_a_id, client_b_id = uuid4(), uuid4()
    stage_id, deal_a_id, deal_b_id = uuid4(), uuid4(), uuid4()
    with isolated_session_factory() as session:
        session.add_all([
            User(id=admin_id, email="tasks-admin@example.test", password_hash=hash_password("synthetic tasks admin"), display_name="Tasks Admin", role=UserRole.ADMIN),
            User(id=admin_b_id, email="tasks-admin-b@example.test", password_hash=hash_password("synthetic tasks admin b"), display_name="Tasks Admin B", role=UserRole.ADMIN),
            User(id=manager_a_id, email="tasks-manager-a@example.test", password_hash=hash_password("synthetic tasks manager a"), display_name="Tasks Manager A", role=UserRole.MANAGER),
            User(id=manager_b_id, email="tasks-manager-b@example.test", password_hash=hash_password("synthetic tasks manager b"), display_name="Tasks Manager B", role=UserRole.MANAGER),
            User(id=inactive_id, email="tasks-inactive@example.test", password_hash=hash_password("synthetic inactive user"), display_name="Inactive", role=UserRole.MANAGER, is_active=False),
            Client(id=client_a_id, name="Tasks Client A"),
            Client(id=client_b_id, name="Tasks Client B"),
            PipelineStage(id=stage_id, name="Tasks Stage", position=1),
            Deal(id=deal_a_id, name="Tasks Deal A", client_id=client_a_id, stage_id=stage_id, responsible_user_id=manager_b_id),
            Deal(id=deal_b_id, name="Tasks Deal B", client_id=client_b_id, stage_id=stage_id),
        ])
        session.commit()

    headers = {
        "admin": {"Authorization": f"Bearer {create_access_token(admin_id)}"},
        "manager_a": {"Authorization": f"Bearer {create_access_token(manager_a_id)}"},
        "manager_b": {"Authorization": f"Bearer {create_access_token(manager_b_id)}"},
    }
    now = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)

    def payload(*, title: str = "Follow up", due_at: datetime = now, responsible_user_id: UUID = admin_id, client_id: UUID | None = None, deal_id: UUID | None = None) -> dict[str, str]:
        result = {"title": title, "description": "Task details", "due_at": due_at.isoformat(), "responsible_user_id": str(responsible_user_id)}
        if client_id is not None:
            result["client_id"] = str(client_id)
        if deal_id is not None:
            result["deal_id"] = str(deal_id)
        return result

    async def flow() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            assert (await client.post("/tasks", json=payload())).status_code == 401
            assert (await client.get("/tasks")).status_code == 401
            assert (await client.get(f"/tasks/{uuid4()}")).status_code == 401
            assert (await client.patch(f"/tasks/{uuid4()}", json={"title": "x"})).status_code == 401
            assert (await client.post(f"/tasks/{uuid4()}/complete")).status_code == 401

            general = await client.post("/tasks", headers=headers["admin"], json=payload(title="General", due_at=now + timedelta(hours=3)))
            assert general.status_code == 201
            general_id = general.json()["id"]
            assert general.json()["status"] == "OPEN"
            assert "is_overdue" not in general.json()

            client_only = await client.post("/tasks", headers=headers["admin"], json=payload(title="Client only", client_id=client_a_id, due_at=now + timedelta(hours=2)))
            deal_only = await client.post("/tasks", headers=headers["admin"], json=payload(title="Deal only", deal_id=deal_a_id, due_at=now + timedelta(hours=1)))
            both = await client.post("/tasks", headers=headers["admin"], json=payload(title="Both", client_id=client_a_id, deal_id=deal_a_id, due_at=now))
            assert [response.status_code for response in (client_only, deal_only, both)] == [201, 201, 201]
            both_id = both.json()["id"]

            assert (await client.post("/tasks", headers=headers["admin"], json=payload(client_id=client_b_id, deal_id=deal_a_id))).status_code == 422
            assert (await client.post("/tasks", headers=headers["admin"], json=payload(client_id=uuid4()))).status_code == 404
            assert (await client.post("/tasks", headers=headers["admin"], json=payload(deal_id=uuid4()))).status_code == 404
            assert (await client.post("/tasks", headers=headers["admin"], json=payload(responsible_user_id=uuid4()))).status_code == 404
            assert (await client.post("/tasks", headers=headers["admin"], json=payload(responsible_user_id=inactive_id))).status_code == 422

            admin_manager = await client.post("/tasks", headers=headers["admin"], json=payload(title="Admin assigned manager", responsible_user_id=manager_a_id))
            admin_admin = await client.post("/tasks", headers=headers["admin"], json=payload(title="Admin assigned admin", responsible_user_id=admin_b_id))
            assert admin_manager.status_code == admin_admin.status_code == 201

            manager_own_deal = await client.post("/tasks", headers=headers["manager_a"], json=payload(title="Manager own with other-owned deal", responsible_user_id=manager_a_id, deal_id=deal_a_id))
            assert manager_own_deal.status_code == 201
            manager_task_id = manager_own_deal.json()["id"]
            assert (await client.post("/tasks", headers=headers["manager_a"], json=payload(responsible_user_id=manager_b_id))).status_code == 403
            assert (await client.post("/tasks", headers=headers["manager_a"], json=payload(responsible_user_id=admin_id))).status_code == 403

            all_tasks = await client.get("/tasks?limit=100", headers=headers["manager_a"])
            assert all_tasks.status_code == 200
            assert general_id in {item["id"] for item in all_tasks.json()}
            assert manager_task_id in {item["id"] for item in all_tasks.json()}
            assert (await client.get(f"/tasks/{general_id}", headers=headers["manager_a"])).status_code == 200
            manager_filtered = await client.get("/tasks?responsible_user_id=" + str(manager_a_id), headers=headers["admin"])
            assert manager_task_id in {item["id"] for item in manager_filtered.json()}
            assert (await client.get("/tasks?client_id=" + str(client_a_id), headers=headers["admin"])).status_code == 200
            assert (await client.get("/tasks?deal_id=" + str(deal_a_id), headers=headers["admin"])).status_code == 200
            assert (await client.get("/tasks?status=OPEN", headers=headers["admin"])).status_code == 200
            paged = await client.get("/tasks?limit=2&offset=0", headers=headers["admin"])
            assert len(paged.json()) == 2
            assert [item["due_at"] for item in paged.json()] == sorted(item["due_at"] for item in paged.json())

            unchanged = await client.patch(f"/tasks/{both_id}", headers=headers["admin"], json={"title": "Renamed"})
            assert unchanged.status_code == 200 and unchanged.json()["client_id"] == str(client_a_id) and unchanged.json()["deal_id"] == str(deal_a_id)
            cleared = await client.patch(f"/tasks/{both_id}", headers=headers["admin"], json={"client_id": None})
            assert cleared.status_code == 200 and cleared.json()["client_id"] is None and cleared.json()["deal_id"] == str(deal_a_id)
            assert (await client.patch(f"/tasks/{both_id}", headers=headers["admin"], json={"client_id": str(client_b_id)})).status_code == 422
            reassigned = await client.patch(f"/tasks/{general_id}", headers=headers["admin"], json={"responsible_user_id": str(manager_b_id), "due_at": (now + timedelta(days=1)).isoformat()})
            assert reassigned.status_code == 200 and reassigned.json()["responsible_user_id"] == str(manager_b_id)

            assert (await client.patch(f"/tasks/{manager_task_id}", headers=headers["manager_a"], json={"title": "Manager update"})).status_code == 200
            assert (await client.patch(f"/tasks/{manager_task_id}", headers=headers["manager_a"], json={"responsible_user_id": str(manager_a_id)})).status_code == 403
            assert (await client.patch(f"/tasks/{general_id}", headers=headers["manager_a"], json={"title": "Forbidden"})).status_code == 403
            completed = await client.post(f"/tasks/{manager_task_id}/complete", headers=headers["manager_a"])
            assert completed.status_code == 200 and completed.json()["status"] == "COMPLETED"
            assert (await client.post(f"/tasks/{general_id}/complete", headers=headers["manager_a"])).status_code == 403
            assert (await client.post(f"/tasks/{general_id}/complete", headers=headers["admin"])).status_code == 200
            assert (await client.delete(f"/tasks/{general_id}", headers=headers["admin"])).status_code == 405

    asyncio.run(flow())
