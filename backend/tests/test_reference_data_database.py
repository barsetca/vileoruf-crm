import asyncio
import os
from collections.abc import Iterator
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
from backend.app.models import PipelineStage, User, UserRole
from backend.app.models.pipeline_stage import SYSTEM_PIPELINE


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)


@pytest.fixture
def isolated_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[sessionmaker[Session]]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_reference_data_test_{uuid4().hex}"
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


def test_reference_data_api_on_postgresql(
    isolated_session_factory: sessionmaker[Session],
) -> None:
    admin_id = uuid4()
    manager_id = uuid4()
    inactive_manager_id = uuid4()
    with isolated_session_factory() as session:
        session.add_all(
            [
                User(
                    id=admin_id,
                    email="reference-admin@example.test",
                    password_hash=hash_password("synthetic reference admin password"),
                    display_name="Reference Admin",
                    role=UserRole.ADMIN,
                    is_active=True,
                ),
                User(
                    id=manager_id,
                    email="reference-manager@example.test",
                    password_hash=hash_password("synthetic reference manager password"),
                    display_name="Reference Manager",
                    role=UserRole.MANAGER,
                    is_active=True,
                ),
                User(
                    id=inactive_manager_id,
                    email="reference-inactive@example.test",
                    password_hash=hash_password("synthetic inactive manager password"),
                    display_name="Reference Inactive Manager",
                    role=UserRole.MANAGER,
                    is_active=False,
                ),
            ]
        )
        session.add_all(
            [PipelineStage(name=name, position=position) for name, position in SYSTEM_PIPELINE]
        )
        session.commit()

    admin_headers = {"Authorization": f"Bearer {create_access_token(admin_id)}"}
    manager_headers = {
        "Authorization": f"Bearer {create_access_token(manager_id)}"
    }

    async def flow() -> tuple[list[dict], list[dict]]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            admin_stages = await client.get("/pipeline-stages", headers=admin_headers)
            manager_stages = await client.get(
                "/pipeline-stages", headers=manager_headers
            )
            admin_employees = await client.get(
                "/employees/reference", headers=admin_headers
            )
            manager_employees = await client.get(
                "/employees/reference", headers=manager_headers
            )
            manager_users = await client.get("/users", headers=manager_headers)

            assert admin_stages.status_code == 200
            assert manager_stages.status_code == 200
            assert admin_employees.status_code == 200
            assert manager_employees.status_code == 200
            assert manager_users.status_code == 403
            assert admin_stages.json() == manager_stages.json()
            assert admin_employees.json() == manager_employees.json()
            return admin_stages.json(), admin_employees.json()

    stages, employees = asyncio.run(flow())

    assert len(stages) == 7
    assert all(set(stage) == {"id", "name", "position"} for stage in stages)
    assert [stage["position"] for stage in stages] == list(range(1, 8))
    assert [(stage["name"], stage["position"]) for stage in stages] == list(
        SYSTEM_PIPELINE
    )

    assert all(
        set(employee) == {"id", "display_name", "role", "is_active"}
        for employee in employees
    )
    employees_by_id = {UUID(employee["id"]): employee for employee in employees}
    assert employees_by_id[admin_id]["is_active"] is True
    assert employees_by_id[admin_id]["role"] == "ADMIN"
    assert employees_by_id[manager_id]["is_active"] is True
    assert employees_by_id[manager_id]["role"] == "MANAGER"
    assert employees_by_id[inactive_manager_id]["is_active"] is False
