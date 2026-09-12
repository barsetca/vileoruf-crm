import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import select

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Client, ClientStatus, Deal, PipelineStage, User, UserRole
from backend.app.services.analytics import get_analytics_summary
from backend.app.services.deals import transition_deal
from backend.app.schemas.deals import DealCreate, DealUpdate
from backend.tests.test_d52a_google_oauth import isolated_database


def _records(session):
    admin = User(email="d61-admin@test", password_hash="x", display_name="Admin", role=UserRole.ADMIN, is_active=True)
    manager = User(email="d61-manager@test", password_hash="x", display_name="Manager", role=UserRole.MANAGER, is_active=True)
    customer = Client(name="Customer", status=ClientStatus.CUSTOMER)
    client = Client(name="Client", status=ClientStatus.CLIENT)
    stages = [PipelineStage(name=name, position=index) for index, name in enumerate(("New Lead", "Contact", "Won", "Lost"), 1)]
    session.add_all([admin, manager, customer, client, *stages]); session.flush()
    by_name = {stage.name: stage for stage in stages}
    deals = [
        Deal(name="Active", client_id=customer.id, stage_id=by_name["New Lead"].id, responsible_user_id=manager.id, estimated_budget=Decimal("100"), created_at=datetime(2025, 1, 10, tzinfo=timezone.utc)),
        Deal(name="No budget", client_id=customer.id, stage_id=by_name["Contact"].id, responsible_user_id=manager.id, estimated_budget=None, created_at=datetime(2025, 3, 10, tzinfo=timezone.utc)),
        Deal(name="Won", client_id=client.id, stage_id=by_name["Won"].id, responsible_user_id=manager.id, estimated_budget=Decimal("300"), created_at=datetime(2025, 3, 15, tzinfo=timezone.utc), first_won_at=datetime(2025, 5, 2, tzinfo=timezone.utc)),
        Deal(name="Reopened", client_id=client.id, stage_id=by_name["Contact"].id, responsible_user_id=manager.id, estimated_budget=Decimal("50"), created_at=datetime(2024, 12, 20, tzinfo=timezone.utc), first_won_at=datetime(2025, 5, 4, tzinfo=timezone.utc)),
        Deal(name="Historical Won", client_id=client.id, stage_id=by_name["Won"].id, responsible_user_id=manager.id, estimated_budget=None, created_at=datetime(2025, 2, 1, tzinfo=timezone.utc), first_won_at=None),
        Deal(name="Lost", client_id=customer.id, stage_id=by_name["Lost"].id, responsible_user_id=manager.id, estimated_budget=Decimal("80"), created_at=datetime(2025, 2, 5, tzinfo=timezone.utc)),
    ]
    session.add_all(deals); session.commit()
    return admin, manager, customer, by_name, deals


@pytest.mark.skipif(__import__("os").getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_first_won_lifecycle_is_immutable_and_preserves_customer_promotion(isolated_database):
    with isolated_database() as session:
        admin, manager, customer, stages, _ = _records(session)
        deal = Deal(name="Transition", client_id=customer.id, stage_id=stages["New Lead"].id, responsible_user_id=manager.id)
        session.add(deal); session.commit()
        assert deal.first_won_at is None
        won = transition_deal(session, deal_id=deal.id, stage_id=stages["Won"].id, current_user=manager)
        first = won.first_won_at
        assert first is not None and first.tzinfo is not None
        assert session.get(Client, customer.id).status is ClientStatus.CLIENT
        transition_deal(session, deal_id=deal.id, stage_id=stages["Contact"].id, current_user=manager)
        assert session.get(Deal, deal.id).first_won_at == first
        transition_deal(session, deal_id=deal.id, stage_id=stages["Won"].id, current_user=manager)
        assert session.get(Deal, deal.id).first_won_at == first


@pytest.mark.skipif(__import__("os").getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_summary_aggregates_crm_wide_data_and_months(isolated_database):
    with isolated_database() as session:
        _records(session)
        summary = get_analytics_summary(session)
        assert summary.clients.model_dump() == {"total": 2, "customer": 1, "client": 1}
        assert summary.deals.model_dump() == {"total": 6, "active": 3, "won": 2, "lost": 1}
        assert summary.active_pipeline_estimated_value == Decimal("150")
        assert summary.won_deals_estimated_value == Decimal("300")
        assert summary.closed_deal_conversion_percent == Decimal("66.67")
        assert [item.stage_name for item in summary.pipeline_stages] == ["New Lead", "Contact", "Won", "Lost"]
        assert [(item.stage_name, item.deal_count, item.estimated_value) for item in summary.pipeline_stages] == [("New Lead", 1, Decimal("100")), ("Contact", 2, Decimal("50")), ("Won", 2, Decimal("300")), ("Lost", 1, Decimal("80"))]
        created = {item.month_start.strftime("%Y-%m"): item.deal_count for item in summary.created_deals_by_month}
        assert created["2024-12"] == 1 and created["2025-01"] == 1 and created["2025-02"] == 2 and created["2025-03"] == 2
        won = {item.month_start.strftime("%Y-%m"): item.deal_count for item in summary.first_won_deals_by_month}
        assert won["2025-05"] == 2


@pytest.mark.skipif(__import__("os").getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_summary_api_allows_both_roles_and_rejects_unauthenticated(isolated_database):
    with isolated_database() as session:
        admin, manager, _, _, _ = _records(session)
        async def request(user=None):
            app.dependency_overrides[get_db] = lambda: session
            if user is not None: app.dependency_overrides[get_current_user] = lambda: user
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                    return await client.get("/analytics/summary")
            finally:
                app.dependency_overrides.clear()
        assert asyncio.run(request()).status_code == 401
        admin_response = asyncio.run(request(admin)); manager_response = asyncio.run(request(manager))
        assert admin_response.status_code == manager_response.status_code == 200
        assert admin_response.json() == manager_response.json()


@pytest.mark.skipif(__import__("os").getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL required")
def test_summary_has_safe_null_conversion_without_terminal_deals(isolated_database):
    with isolated_database() as session:
        admin = User(email="d61-zero@test", password_hash="x", display_name="Admin", role=UserRole.ADMIN, is_active=True)
        client = Client(name="Only active")
        stage = PipelineStage(name="New Lead", position=1)
        session.add_all([admin, client, stage]); session.flush(); session.add(Deal(name="Open", client_id=client.id, stage_id=stage.id, responsible_user_id=admin.id)); session.commit()
        assert get_analytics_summary(session).closed_deal_conversion_percent is None


def test_first_won_at_is_not_accepted_by_create_or_patch_dtos():
    with pytest.raises(ValidationError):
        DealUpdate.model_validate({"first_won_at": "2025-01-01T00:00:00Z"})
    with pytest.raises(ValidationError):
        DealCreate.model_validate({"client_id": "00000000-0000-0000-0000-000000000000", "stage_id": "00000000-0000-0000-0000-000000000000", "name": "Synthetic", "first_won_at": "2025-01-01T00:00:00Z"})
