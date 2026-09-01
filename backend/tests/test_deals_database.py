import asyncio
import os
from collections.abc import Iterator
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.core.security import create_access_token, hash_password
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Client, ClientStatus, Deal, PipelineStage, User, UserRole
from backend.app.models.pipeline_stage import SYSTEM_PIPELINE
from backend.app.services.deals import DealPersistenceError, transition_deal


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)


@pytest.fixture
def isolated_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[sessionmaker[Session]]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_deals_api_test_{uuid4().hex}"
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


def test_deals_api_and_ownership_on_postgresql(
    isolated_session_factory: sessionmaker[Session],
) -> None:
    (
        admin_id,
        admin_b_id,
        manager_a_id,
        manager_b_id,
        inactive_admin_id,
        inactive_manager_id,
    ) = [uuid4() for _ in range(6)]
    client_id, stage_id, other_stage_id = uuid4(), uuid4(), uuid4()
    with isolated_session_factory() as session:
        session.add_all(
            [
                User(id=admin_id, email="deals-admin@example.test", password_hash=hash_password("synthetic deals admin password"), display_name="Deals Admin", role=UserRole.ADMIN, is_active=True),
                User(id=admin_b_id, email="deals-admin-b@example.test", password_hash=hash_password("synthetic deals admin b password"), display_name="Deals Admin B", role=UserRole.ADMIN, is_active=True),
                User(id=manager_a_id, email="deals-manager-a@example.test", password_hash=hash_password("synthetic deals manager a password"), display_name="Manager A", role=UserRole.MANAGER, is_active=True),
                User(id=manager_b_id, email="deals-manager-b@example.test", password_hash=hash_password("synthetic deals manager b password"), display_name="Manager B", role=UserRole.MANAGER, is_active=True),
                User(id=inactive_admin_id, email="deals-inactive-admin@example.test", password_hash=hash_password("synthetic inactive admin password"), display_name="Inactive Admin", role=UserRole.ADMIN, is_active=False),
                User(id=inactive_manager_id, email="deals-inactive-manager@example.test", password_hash=hash_password("synthetic inactive manager password"), display_name="Inactive Manager", role=UserRole.MANAGER, is_active=False),
                Client(id=client_id, name="Synthetic Customer", status=ClientStatus.CUSTOMER),
                PipelineStage(id=stage_id, name="New Lead", position=1),
                PipelineStage(id=other_stage_id, name="Contact", position=2),
            ]
        )
        session.commit()

    headers = {
        "admin": {"Authorization": f"Bearer {create_access_token(admin_id)}"},
        "a": {"Authorization": f"Bearer {create_access_token(manager_a_id)}"},
        "b": {"Authorization": f"Bearer {create_access_token(manager_b_id)}"},
    }
    base = {"client_id": str(client_id), "stage_id": str(stage_id)}

    async def flow() -> dict[str, UUID]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            unassigned_response = await client.post(
                "/deals", headers=headers["admin"], json={**base, "name": "Unassigned", "estimated_budget": "123456789012.34", "probability": 0}
            )
            assert unassigned_response.status_code == 201
            unassigned = unassigned_response.json()
            assert unassigned["responsible_user_id"] is None
            assert unassigned["estimated_budget"] == "123456789012.34"
            assert unassigned["probability"] == 0

            assigned_a_response = await client.post(
                "/deals", headers=headers["admin"], json={**base, "name": "Assigned A", "responsible_user_id": str(manager_a_id), "description": None, "deadline": None, "probability": 100}
            )
            assert assigned_a_response.status_code == 201
            assigned_a = assigned_a_response.json()

            admin_self_response = await client.post(
                "/deals", headers=headers["admin"], json={**base, "name": "Admin Self", "responsible_user_id": str(admin_id)}
            )
            assert admin_self_response.status_code == 201
            admin_self = admin_self_response.json()
            assert admin_self["responsible_user_id"] == str(admin_id)

            admin_b_response = await client.post(
                "/deals", headers=headers["admin"], json={**base, "name": "Admin B", "responsible_user_id": str(admin_b_id)}
            )
            assert admin_b_response.status_code == 201
            admin_b_deal = admin_b_response.json()
            assert admin_b_deal["responsible_user_id"] == str(admin_b_id)

            manager_created_response = await client.post(
                "/deals", headers=headers["b"], json={**base, "name": "Manager B Deal", "estimated_budget": "19.99"}
            )
            assert manager_created_response.status_code == 201
            assigned_b = manager_created_response.json()
            assert assigned_b["responsible_user_id"] == str(manager_b_id)

            for forbidden_value in (None, str(manager_a_id), str(manager_b_id), str(admin_id)):
                response = await client.post(
                    "/deals", headers=headers["a"], json={**base, "name": "Forbidden assignment", "responsible_user_id": forbidden_value}
                )
                assert response.status_code == 403

            for responsible_id, expected in ((inactive_admin_id, 422), (inactive_manager_id, 422), (uuid4(), 404)):
                response = await client.post(
                    "/deals", headers=headers["admin"], json={**base, "name": "Invalid responsible", "responsible_user_id": str(responsible_id)}
                )
                assert response.status_code == expected

            assert (await client.post("/deals", headers=headers["admin"], json={**base, "client_id": str(uuid4()), "name": "Missing Client"})).status_code == 404
            assert (await client.post("/deals", headers=headers["admin"], json={**base, "stage_id": str(uuid4()), "name": "Missing Stage"})).status_code == 404

            expected_ids = {unassigned["id"], assigned_a["id"], assigned_b["id"], admin_self["id"], admin_b_deal["id"]}
            for actor in ("admin", "a", "b"):
                listing = await client.get("/deals", headers=headers[actor])
                assert listing.status_code == 200
                assert {item["id"] for item in listing.json()} == expected_ids
                for deal_id in expected_ids:
                    assert (await client.get(f"/deals/{deal_id}", headers=headers[actor])).status_code == 200

            page = await client.get("/deals?limit=1&offset=1", headers=headers["a"])
            assert page.status_code == 200 and len(page.json()) == 1
            for query in ("limit=0", "limit=101", "offset=-1"):
                assert (await client.get(f"/deals?{query}", headers=headers["admin"])).status_code == 422

            own_patch = await client.patch(
                f"/deals/{assigned_a['id']}", headers=headers["a"], json={"name": "Manager A Updated", "description": "Owned", "estimated_budget": None, "deadline": "2026-12-31", "probability": 100}
            )
            assert own_patch.status_code == 200
            assert own_patch.json()["name"] == "Manager A Updated"
            assert own_patch.json()["stage_id"] == str(stage_id)

            manager_b_patch = await client.patch(
                f"/deals/{assigned_b['id']}",
                headers=headers["b"],
                json={"description": "Manager B owned update"},
            )
            assert manager_b_patch.status_code == 200

            admin_unassigned_patch = await client.patch(
                f"/deals/{unassigned['id']}",
                headers=headers["admin"],
                json={"description": "Admin updated unassigned"},
            )
            assert admin_unassigned_patch.status_code == 200

            assert (await client.patch(f"/deals/{assigned_b['id']}", headers=headers["a"], json={"name": "Foreign"})).status_code == 403
            assert (await client.patch(f"/deals/{unassigned['id']}", headers=headers["a"], json={"name": "Unassigned"})).status_code == 403
            assert (await client.patch(f"/deals/{assigned_a['id']}", headers=headers["b"], json={"name": "Foreign"})).status_code == 403
            assert (await client.patch(f"/deals/{unassigned['id']}", headers=headers["b"], json={"name": "Unassigned"})).status_code == 403
            assert (await client.patch(f"/deals/{admin_self['id']}", headers=headers["a"], json={"name": "Admin Foreign"})).status_code == 403
            assert (await client.patch(f"/deals/{assigned_a['id']}", headers=headers["a"], json={"responsible_user_id": str(manager_a_id)})).status_code == 403

            reassigned = await client.patch(
                f"/deals/{assigned_a['id']}", headers=headers["admin"], json={"responsible_user_id": str(admin_id)}
            )
            assert reassigned.status_code == 200
            assert reassigned.json()["responsible_user_id"] == str(admin_id)
            admin_to_admin = await client.patch(
                f"/deals/{assigned_a['id']}", headers=headers["admin"], json={"responsible_user_id": str(admin_b_id)}
            )
            assert admin_to_admin.status_code == 200
            assert admin_to_admin.json()["responsible_user_id"] == str(admin_b_id)
            admin_to_manager = await client.patch(
                f"/deals/{assigned_a['id']}", headers=headers["admin"], json={"responsible_user_id": str(manager_b_id)}
            )
            assert admin_to_manager.status_code == 200
            assert admin_to_manager.json()["responsible_user_id"] == str(manager_b_id)
            cleared = await client.patch(
                f"/deals/{assigned_a['id']}", headers=headers["admin"], json={"responsible_user_id": None}
            )
            assert cleared.status_code == 200 and cleared.json()["responsible_user_id"] is None
            restored = await client.patch(
                f"/deals/{assigned_a['id']}", headers=headers["admin"], json={"responsible_user_id": str(admin_id)}
            )
            assert restored.status_code == 200
            assert restored.json()["responsible_user_id"] == str(admin_id)

            for responsible_id, expected in ((inactive_admin_id, 422), (inactive_manager_id, 422), (uuid4(), 404)):
                assert (await client.patch(f"/deals/{assigned_a['id']}", headers=headers["admin"], json={"responsible_user_id": str(responsible_id)})).status_code == expected

            for payload in ({"stage_id": str(other_stage_id)}, {"client_id": str(uuid4())}, {"id": str(uuid4())}, {"probability": -1}, {"probability": 101}, {}):
                assert (await client.patch(f"/deals/{assigned_a['id']}", headers=headers["admin"], json=payload)).status_code == 422
            assert (await client.get(f"/deals/{uuid4()}", headers=headers["admin"])).status_code == 404
            assert (await client.patch(f"/deals/{uuid4()}", headers=headers["admin"], json={"name": "Missing"})).status_code == 404
            assert (await client.delete(f"/deals/{assigned_a['id']}", headers=headers["admin"])).status_code == 405
            assert set(app.openapi()["paths"]["/deals/{deal_id}/transition"]) == {"post"}

            return {"unassigned": UUID(unassigned["id"]), "a": UUID(assigned_a["id"]), "b": UUID(assigned_b["id"]), "admin_self": UUID(admin_self["id"]), "admin_b": UUID(admin_b_deal["id"])}

    ids = asyncio.run(flow())

    with isolated_session_factory() as session:
        deals = {deal.id: deal for deal in session.scalars(select(Deal))}
        assert len(deals) == 5
        assert deals[ids["unassigned"]].responsible_user_id is None
        assert deals[ids["a"]].responsible_user_id == admin_id
        assert deals[ids["a"]].stage_id == stage_id
        assert deals[ids["a"]].client_id == client_id
        assert deals[ids["b"]].estimated_budget == Decimal("19.99")
        assert deals[ids["admin_self"]].responsible_user_id == admin_id
        assert deals[ids["admin_b"]].responsible_user_id == admin_b_id
        assert session.get(Client, client_id).status is ClientStatus.CUSTOMER
        assert session.scalar(select(func.count()).select_from(PipelineStage)) == 2


def test_pipeline_transition_and_won_promotion_on_postgresql(
    isolated_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_a_id, admin_b_id, manager_a_id, manager_b_id = [uuid4() for _ in range(4)]
    customer_id, existing_client_id, initial_won_client_id, rollback_client_id = [
        uuid4() for _ in range(4)
    ]
    stage_ids = {name: uuid4() for name, _ in SYSTEM_PIPELINE}
    deal_ids = {
        "admin": uuid4(),
        "admin_b": uuid4(),
        "manager_a": uuid4(),
        "manager_b": uuid4(),
        "unassigned": uuid4(),
        "promotion": uuid4(),
        "second": uuid4(),
        "existing_client": uuid4(),
        "rollback": uuid4(),
    }

    with isolated_session_factory() as session:
        users = [
            User(id=admin_a_id, email="transition-admin-a@example.test", password_hash=hash_password("synthetic transition admin a"), display_name="Transition Admin A", role=UserRole.ADMIN, is_active=True),
            User(id=admin_b_id, email="transition-admin-b@example.test", password_hash=hash_password("synthetic transition admin b"), display_name="Transition Admin B", role=UserRole.ADMIN, is_active=True),
            User(id=manager_a_id, email="transition-manager-a@example.test", password_hash=hash_password("synthetic transition manager a"), display_name="Transition Manager A", role=UserRole.MANAGER, is_active=True),
            User(id=manager_b_id, email="transition-manager-b@example.test", password_hash=hash_password("synthetic transition manager b"), display_name="Transition Manager B", role=UserRole.MANAGER, is_active=True),
        ]
        clients = [
            Client(id=customer_id, name="Transition Customer", status=ClientStatus.CUSTOMER),
            Client(id=existing_client_id, name="Existing Client", status=ClientStatus.CLIENT),
            Client(id=initial_won_client_id, name="Initial Won Customer", status=ClientStatus.CUSTOMER),
            Client(id=rollback_client_id, name="Rollback Customer", status=ClientStatus.CUSTOMER),
        ]
        stages = [
            PipelineStage(id=stage_ids[name], name=name, position=position)
            for name, position in SYSTEM_PIPELINE
        ]
        deals = [
            Deal(id=deal_ids["admin"], client_id=customer_id, stage_id=stage_ids["New Lead"], responsible_user_id=admin_a_id, name="Admin Deal"),
            Deal(id=deal_ids["admin_b"], client_id=customer_id, stage_id=stage_ids["New Lead"], responsible_user_id=admin_b_id, name="Admin B Deal"),
            Deal(id=deal_ids["manager_a"], client_id=customer_id, stage_id=stage_ids["New Lead"], responsible_user_id=manager_a_id, name="Manager A Deal"),
            Deal(id=deal_ids["manager_b"], client_id=customer_id, stage_id=stage_ids["New Lead"], responsible_user_id=manager_b_id, name="Manager B Deal"),
            Deal(id=deal_ids["unassigned"], client_id=customer_id, stage_id=stage_ids["New Lead"], responsible_user_id=None, name="Unassigned Deal"),
            Deal(id=deal_ids["promotion"], client_id=customer_id, stage_id=stage_ids["Negotiation"], responsible_user_id=manager_a_id, name="Promotion Deal"),
            Deal(id=deal_ids["second"], client_id=customer_id, stage_id=stage_ids["Proposal"], responsible_user_id=manager_a_id, name="Second Deal"),
            Deal(id=deal_ids["existing_client"], client_id=existing_client_id, stage_id=stage_ids["Negotiation"], responsible_user_id=manager_a_id, name="Existing Client Deal"),
            Deal(id=deal_ids["rollback"], client_id=rollback_client_id, stage_id=stage_ids["Negotiation"], responsible_user_id=admin_a_id, name="Rollback Deal"),
        ]
        session.add_all([*users, *clients, *stages, *deals])
        session.commit()

    headers = {
        "admin": {"Authorization": f"Bearer {create_access_token(admin_a_id)}"},
        "manager_a": {"Authorization": f"Bearer {create_access_token(manager_a_id)}"},
        "manager_b": {"Authorization": f"Bearer {create_access_token(manager_b_id)}"},
    }

    async def flow() -> UUID:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            async def transition(deal_key: str, stage_name: str, actor: str = "admin") -> httpx.Response:
                return await client.post(
                    f"/deals/{deal_ids[deal_key]}/transition",
                    headers=headers[actor],
                    json={"stage_id": str(stage_ids[stage_name])},
                )

            basic = await transition("admin", "Contact")
            assert basic.status_code == 200
            assert basic.json()["stage_id"] == str(stage_ids["Contact"])
            assert (await client.get(f"/deals/{deal_ids['admin']}", headers=headers["manager_a"])).json()["stage_id"] == str(stage_ids["Contact"])
            assert (await transition("admin", "Contact")).status_code == 200

            for deal_key in ("manager_b", "admin_b", "unassigned"):
                assert (await transition(deal_key, "Qualification")).status_code == 200

            for stage_name in ("Qualification", "Contact", "Lost", "New Lead"):
                response = await transition("manager_a", stage_name, "manager_a")
                assert response.status_code == 200
                assert response.json()["stage_id"] == str(stage_ids[stage_name])

            for deal_key in ("manager_b", "admin_b", "unassigned"):
                assert (await transition(deal_key, "Contact", "manager_a")).status_code == 403
                assert (await client.get(f"/deals/{deal_ids[deal_key]}", headers=headers["manager_a"])).status_code == 200

            assert (await transition("promotion", "Won", "manager_a")).status_code == 200
            assert (await transition("promotion", "Won", "manager_a")).status_code == 200
            assert (await client.get(f"/clients/{customer_id}", headers=headers["manager_a"])).json()["status"] == "CLIENT"
            assert (await transition("promotion", "Negotiation", "manager_a")).status_code == 200
            assert (await transition("promotion", "Contact", "manager_a")).status_code == 200
            assert (await transition("second", "Lost", "manager_a")).status_code == 200
            assert (await client.get(f"/clients/{customer_id}", headers=headers["admin"])).json()["status"] == "CLIENT"

            assert (await transition("existing_client", "Won", "manager_a")).status_code == 200
            assert (await client.get(f"/clients/{existing_client_id}", headers=headers["admin"])).json()["status"] == "CLIENT"

            initial_won = await client.post(
                "/deals",
                headers=headers["admin"],
                json={"client_id": str(initial_won_client_id), "stage_id": str(stage_ids["Won"]), "name": "Initially Won"},
            )
            assert initial_won.status_code == 201
            assert (await client.get(f"/clients/{initial_won_client_id}", headers=headers["admin"])).json()["status"] == "CUSTOMER"
            same_initial_won = await client.post(
                f"/deals/{initial_won.json()['id']}/transition",
                headers=headers["admin"],
                json={"stage_id": str(stage_ids["Won"])},
            )
            assert same_initial_won.status_code == 200
            assert (await client.get(f"/clients/{initial_won_client_id}", headers=headers["admin"])).json()["status"] == "CUSTOMER"

            assert (await client.post(f"/deals/{uuid4()}/transition", headers=headers["admin"], json={"stage_id": str(stage_ids["Contact"])})).status_code == 404
            assert (await client.post(f"/deals/{deal_ids['admin']}/transition", headers=headers["admin"], json={"stage_id": str(uuid4())})).status_code == 404
            assert (await client.post(f"/deals/{deal_ids['admin']}/transition", headers=headers["admin"], json={"stage_id": "bad"})).status_code == 422
            assert (await client.patch(f"/deals/{deal_ids['admin']}", headers=headers["admin"], json={"stage_id": str(stage_ids["Won"])})).status_code == 422
            assert (await client.patch(f"/clients/{customer_id}", headers=headers["admin"], json={"status": "CUSTOMER"})).status_code == 422
            return UUID(initial_won.json()["id"])

    initial_won_deal_id = asyncio.run(flow())

    with isolated_session_factory() as session:
        assert session.get(Deal, deal_ids["admin"]).stage_id == stage_ids["Contact"]
        assert session.get(Deal, deal_ids["promotion"]).stage_id == stage_ids["Contact"]
        assert session.get(Deal, deal_ids["second"]).stage_id == stage_ids["Lost"]
        assert session.get(Client, customer_id).status is ClientStatus.CLIENT
        assert session.get(Client, existing_client_id).status is ClientStatus.CLIENT
        assert session.get(Client, initial_won_client_id).status is ClientStatus.CUSTOMER
        assert session.get(Deal, initial_won_deal_id).stage_id == stage_ids["Won"]

    with isolated_session_factory() as session:
        admin = session.get(User, admin_a_id)
        original_commit = session.commit

        def fail_after_flush() -> None:
            session.flush()
            raise SQLAlchemyError("synthetic commit failure")

        monkeypatch.setattr(session, "commit", fail_after_flush)
        with pytest.raises(DealPersistenceError):
            transition_deal(
                session,
                deal_id=deal_ids["rollback"],
                stage_id=stage_ids["Won"],
                current_user=admin,
            )
        monkeypatch.setattr(session, "commit", original_commit)
        session.expire_all()
        assert session.get(Deal, deal_ids["rollback"]).stage_id == stage_ids["Negotiation"]
        assert session.get(Client, rollback_client_id).status is ClientStatus.CUSTOMER
