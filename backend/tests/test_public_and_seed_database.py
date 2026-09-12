import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Client, ClientStatus, Deal, PipelineStage, PublicRequest
from backend.app.models.pipeline_stage import SYSTEM_PIPELINE
from backend.app.services.public_requests import (
    PERSONAL_DATA_CONSENT_VERSION,
    PRIVACY_POLICY_VERSION,
    PublicRequestError,
    create_public_request,
)
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
    payload = {"name": "Public Synthetic", "deal_name": "Public Synthetic Deal", "company": "Fictional Studio", "service_id": str(GENERAL_SERVICE_ID), "personal_data_consent": True}
    response = request("/public/requests", payload)
    assert response.status_code == 201
    with isolated_session_factory() as session:
        client = session.scalar(select(Client).where(Client.name == "Public Synthetic"))
        assert client is not None and client.status is ClientStatus.CUSTOMER and client.lead_source == "Website"
        assert client.personal_data_consent is True and client.personal_data_consent_at is not None
        assert client.personal_data_consent_version == PERSONAL_DATA_CONSENT_VERSION
        assert client.privacy_policy_version == PRIVACY_POLICY_VERSION
        deal = session.scalar(select(Deal).where(Deal.name == "Public Synthetic Deal"))
        assert deal is not None and deal.client_id == client.id and deal.responsible_user_id is None
        assert deal.stage.name == "New Lead"
        snapshot = session.scalar(select(PublicRequest).where(PublicRequest.deal_id == deal.id))
        assert snapshot is not None and snapshot.client_id == client.id and snapshot.deal_id == deal.id
        assert snapshot.name == "Public Synthetic" and snapshot.company == "Fictional Studio"
        assert snapshot.deal_name == "Public Synthetic Deal" and snapshot.service_id == deal.service_id
        assert snapshot.personal_data_consent is True and snapshot.personal_data_consent_at is not None
        assert snapshot.personal_data_consent_version == PERSONAL_DATA_CONSENT_VERSION
        assert snapshot.privacy_policy_version == PRIVACY_POLICY_VERSION
        baseline = (
            session.scalar(select(func.count()).select_from(Client)),
            session.scalar(select(func.count()).select_from(Deal)),
            session.scalar(select(func.count()).select_from(PublicRequest)),
        )
    for field in ("status", "stage_id", "responsible_user_id", "probability"):
        invalid = {**payload, field: "CLIENT" if field == "status" else str(uuid4())}
        assert request("/public/requests", invalid).status_code == 422
    assert request("/clients", {}).status_code == 401
    assert request("/deals", {}).status_code == 401
    with isolated_session_factory() as session:
        assert (
            session.scalar(select(func.count()).select_from(Client)),
            session.scalar(select(func.count()).select_from(Deal)),
            session.scalar(select(func.count()).select_from(PublicRequest)),
        ) == baseline


def test_public_invalid_request_does_not_create_partial_records(isolated_session_factory):
    with isolated_session_factory() as session:
        session.add_all([PipelineStage(name=name, position=position) for name, position in SYSTEM_PIPELINE])
        session.commit()
    payload = {"name": "Consent Synthetic", "deal_name": "Consent Synthetic Deal", "service_id": str(GENERAL_SERVICE_ID)}
    assert request("/public/requests", payload).status_code == 422
    assert request("/public/requests", {**payload, "personal_data_consent": False}).status_code == 422
    assert request("/public/requests", {**payload, "personal_data_consent": True, "personal_data_consent_version": "client-value"}).status_code == 422
    assert request("/public/requests", {"name": "  ", "deal_name": "Invalid", "personal_data_consent": True}).status_code == 422
    with isolated_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Client)) == 0
        assert session.scalar(select(func.count()).select_from(Deal)) == 0
        assert session.scalar(select(func.count()).select_from(PublicRequest)) == 0


def test_public_request_snapshot_is_complete_immutable_and_duplicate_email_remains_deferred(isolated_session_factory):
    with isolated_session_factory() as session:
        session.add_all([PipelineStage(name=name, position=position) for name, position in SYSTEM_PIPELINE])
        session.commit(); bootstrap_business_catalog(session)

    payload = {
        "name": "Snapshot Synthetic", "contact_person": "Contact Synthetic",
        "email": "snapshot@example.test", "phone": "+34910000000",
        "telegram": "snapshot_user", "whatsapp": "+34910000001",
        "company": "Snapshot Studio", "deal_name": "Snapshot Deal",
        "service_id": str(GENERAL_SERVICE_ID), "description": "Original public request description",
        "estimated_budget": "1234.50", "deadline": "2026-12-31",
        "preferred_communication_language": "ES", "personal_data_consent": True,
    }
    assert request("/public/requests", payload).status_code == 201
    assert request("/public/requests", {**payload, "deal_name": "Second same-email Deal"}).status_code == 201

    with isolated_session_factory() as session:
        snapshots = list(session.scalars(select(PublicRequest).order_by(PublicRequest.created_at, PublicRequest.id)))
        clients = list(session.scalars(select(Client).where(Client.email == "snapshot@example.test")))
        assert len(snapshots) == 2 and len(clients) == 1
        snapshot = snapshots[0]
        deal = session.get(Deal, snapshot.deal_id)
        client = session.get(Client, snapshot.client_id)
        assert deal is not None and client is not None
        assert snapshot.name == payload["name"] and snapshot.contact_person == payload["contact_person"]
        assert snapshot.email == payload["email"] and snapshot.phone == payload["phone"]
        assert snapshot.telegram == payload["telegram"] and snapshot.whatsapp == payload["whatsapp"]
        assert snapshot.company == payload["company"] and snapshot.preferred_communication_language.value == "ES"
        assert snapshot.deal_name == payload["deal_name"] and snapshot.description == payload["description"]
        assert snapshot.service_id == GENERAL_SERVICE_ID
        assert snapshot.service_name_ru == "Общий запрос" and snapshot.service_name_en == "General request" and snapshot.service_name_es == "Solicitud general"
        assert snapshot.estimated_budget == Decimal("1234.50") and snapshot.deadline == date(2026, 12, 31)
        assert snapshot.personal_data_consent is True and snapshot.personal_data_consent_at is not None
        assert snapshot.personal_data_consent_version == PERSONAL_DATA_CONSENT_VERSION
        assert snapshot.privacy_policy_version == PRIVACY_POLICY_VERSION

        client.name = "Later Client Name"; client.company = "Later Company"
        deal.name = "Later Deal Name"; deal.description = "Later Deal Description"
        session.commit(); session.refresh(snapshot)
        assert snapshot.name == payload["name"] and snapshot.company == payload["company"]
        assert snapshot.deal_name == payload["deal_name"] and snapshot.description == payload["description"]


def test_public_request_snapshot_failure_rolls_back_client_deal_and_snapshot(isolated_session_factory):
    with isolated_session_factory() as session:
        session.add_all([PipelineStage(name=name, position=position) for name, position in SYSTEM_PIPELINE])
        session.commit(); bootstrap_business_catalog(session)

        def fail_public_request_snapshot(current_session, _flush_context, _instances):
            if any(isinstance(item, PublicRequest) for item in current_session.new):
                raise SQLAlchemyError("synthetic snapshot persistence failure")

        event.listen(Session, "before_flush", fail_public_request_snapshot)
        try:
            with pytest.raises(PublicRequestError):
                create_public_request(
                    session,
                    values={
                        "name": "Rollback Synthetic", "deal_name": "Rollback Deal",
                        "service_id": GENERAL_SERVICE_ID, "description": None,
                        "estimated_budget": None, "deadline": None,
                        "preferred_communication_language": "RU", "personal_data_consent": True,
                    },
                )
        finally:
            event.remove(Session, "before_flush", fail_public_request_snapshot)

        assert session.scalar(select(func.count()).select_from(Client)) == 0
        assert session.scalar(select(func.count()).select_from(Deal)) == 0
        assert session.scalar(select(func.count()).select_from(PublicRequest)) == 0


def test_public_request_reuses_and_reactivates_archived_client_without_profile_overwrite(isolated_session_factory):
    with isolated_session_factory() as session:
        session.add_all([PipelineStage(name=name, position=position) for name, position in SYSTEM_PIPELINE]); session.commit(); bootstrap_business_catalog(session)
        stage_id = session.scalar(select(PipelineStage.id).where(PipelineStage.name == "New Lead"))
        client = Client(name="Original Ivan", company="Company A", phone="Phone A", telegram="Username A", email="reactivate@example.test", archived_at=date.today())
        session.add(client); session.flush()
        old = Deal(name="Old archived", client_id=client.id, stage_id=stage_id, archived_at=date.today())
        session.add(old); session.commit(); client_id, old_id = client.id, old.id
    payload = {"name":"Submitted Petr", "company":"Company B", "phone":"Phone B", "telegram":"Username B", "email":" REACTIVATE@EXAMPLE.TEST ", "deal_name":"New active deal", "description":"Submitted description", "estimated_budget":"42.00", "deadline":"2026-12-31", "service_id":str(GENERAL_SERVICE_ID), "personal_data_consent":True}
    assert request("/public/requests", payload).json() == {"status":"accepted"}
    with isolated_session_factory() as session:
        client = session.get(Client, client_id); old = session.get(Deal, old_id)
        assert client.archived_at is None and (client.name, client.company, client.phone, client.telegram) == ("Original Ivan", "Company A", "Phone A", "Username A")
        assert session.scalar(select(func.count()).select_from(Client)) == 1 and old.archived_at is not None
        snapshot = session.scalar(select(PublicRequest).where(PublicRequest.client_id == client_id))
        new_deal = session.get(Deal, snapshot.deal_id)
        assert new_deal.archived_at is None and snapshot.deal_name == "New active deal"
        assert (snapshot.name, snapshot.company, snapshot.phone, snapshot.telegram) == ("Submitted Petr", "Company B", "Phone B", "Username B")


def test_concurrent_public_requests_recover_to_one_client_and_two_snapshots(isolated_session_factory):
    with isolated_session_factory() as session:
        session.add_all([PipelineStage(name=name, position=position) for name, position in SYSTEM_PIPELINE]); session.commit(); bootstrap_business_catalog(session)
    values = [
        {"name":"A", "email":"Concurrent@Test.Example", "deal_name":"Concurrent A", "description":"A", "estimated_budget":Decimal("1.00"), "deadline":date(2026,12,30), "service_id":GENERAL_SERVICE_ID, "preferred_communication_language":"RU", "personal_data_consent":True},
        {"name":"B", "email":" concurrent@test.example ", "deal_name":"Concurrent B", "description":"B", "estimated_budget":Decimal("2.00"), "deadline":date(2026,12,31), "service_id":GENERAL_SERVICE_ID, "preferred_communication_language":"RU", "personal_data_consent":True},
    ]
    def submit(item):
        with isolated_session_factory() as session:
            return create_public_request(session, values=item).id
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(submit, values))
    assert len(result) == 2
    with isolated_session_factory() as session:
        client = session.scalar(select(Client).where(Client.email == "concurrent@test.example"))
        deals = list(session.scalars(select(Deal).where(Deal.client_id == client.id)))
        snapshots = list(session.scalars(select(PublicRequest).where(PublicRequest.client_id == client.id)))
        assert len(deals) == 2 and len(snapshots) == 2
        assert {snapshot.deal_name for snapshot in snapshots} == {"Concurrent A", "Concurrent B"}


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
