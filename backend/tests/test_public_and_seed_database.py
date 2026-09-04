import asyncio
import os
from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Client, ClientStatus, Deal, PipelineStage
from backend.app.models.pipeline_stage import SYSTEM_PIPELINE
from backend.app.scripts.seed_demo import DEMO_CLIENT_IDS, DEMO_DEAL_IDS, DemoSeedError, clean_demo, seed_demo
from backend.app.scripts.bootstrap_business_catalog import GENERAL_SERVICE_ID, bootstrap_business_catalog


pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="Set RUN_DATABASE_TESTS=1 against PostgreSQL")


@pytest.fixture
def isolated_session_factory(monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker[Session]]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_d29a_test_{uuid4().hex}"
    maintenance_engine = create_engine(source_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    isolated_url = source_url.set(database=database_name)
    isolated_engine = None
    try:
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
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
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
        maintenance_engine.dispose()


def request(path: str, payload: dict) -> httpx.Response:
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)
    return asyncio.run(send())


def test_public_request_creates_atomic_crm_records_and_rejects_internal_fields(isolated_session_factory):
    with isolated_session_factory() as session:
        session.add_all([PipelineStage(name=name, position=position) for name, position in SYSTEM_PIPELINE])
        session.commit(); bootstrap_business_catalog(session)
    payload = {"name": "Public Synthetic", "deal_name": "Public Synthetic Deal", "company": "Fictional Studio", "service_id": str(GENERAL_SERVICE_ID)}
    response = request("/public/requests", payload)
    assert response.status_code == 201
    with isolated_session_factory() as session:
        client = session.scalar(select(Client).where(Client.name == "Public Synthetic"))
        assert client is not None and client.status is ClientStatus.CUSTOMER and client.lead_source == "Website"
        deal = session.scalar(select(Deal).where(Deal.name == "Public Synthetic Deal"))
        assert deal is not None and deal.client_id == client.id and deal.responsible_user_id is None
        assert deal.stage.name == "New Lead"
        baseline = (session.scalar(select(func.count()).select_from(Client)), session.scalar(select(func.count()).select_from(Deal)))
    for field in ("status", "stage_id", "responsible_user_id", "probability"):
        invalid = {**payload, field: "CLIENT" if field == "status" else str(uuid4())}
        assert request("/public/requests", invalid).status_code == 422
    assert request("/clients", {}).status_code == 401
    assert request("/deals", {}).status_code == 401
    with isolated_session_factory() as session:
        assert (session.scalar(select(func.count()).select_from(Client)), session.scalar(select(func.count()).select_from(Deal))) == baseline


def test_public_invalid_request_does_not_create_partial_records(isolated_session_factory):
    with isolated_session_factory() as session:
        session.add_all([PipelineStage(name=name, position=position) for name, position in SYSTEM_PIPELINE])
        session.commit()
    assert request("/public/requests", {"name": "  ", "deal_name": "Invalid"}).status_code == 422
    with isolated_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Client)) == 0
        assert session.scalar(select(func.count()).select_from(Deal)) == 0


def test_seed_is_idempotent_safe_and_supports_clean(isolated_session_factory):
    with isolated_session_factory() as session:
        session.add_all([PipelineStage(name=name, position=position) for name, position in SYSTEM_PIPELINE])
        unrelated_client = Client(name="Unrelated")
        session.add(unrelated_client)
        session.flush()
        session.add(Deal(name="Unrelated Deal", client_id=unrelated_client.id, stage_id=session.scalar(select(PipelineStage.id).where(PipelineStage.name == "New Lead"))))
        session.commit()
        seed_demo(session, app_env="development")
        seed_demo(session, app_env="test")
        assert session.scalar(select(func.count()).select_from(Client).where(Client.id.in_(DEMO_CLIENT_IDS))) == 3
        assert session.scalar(select(func.count()).select_from(Deal).where(Deal.id.in_(DEMO_DEAL_IDS))) == 5
        won_client = session.get(Client, DEMO_CLIENT_IDS[1])
        assert won_client.status is ClientStatus.CLIENT
        clean_demo(session, app_env="development")
        assert session.scalar(select(func.count()).select_from(Client).where(Client.id.in_(DEMO_CLIENT_IDS))) == 0
        assert session.scalar(select(func.count()).select_from(Deal).where(Deal.id.in_(DEMO_DEAL_IDS))) == 0
        assert session.scalar(select(Client).where(Client.name == "Unrelated")) is not None
        assert session.scalar(select(Deal).where(Deal.name == "Unrelated Deal")) is not None
        seed_demo(session, app_env="development")
        with pytest.raises(DemoSeedError):
            seed_demo(session, app_env="production")
