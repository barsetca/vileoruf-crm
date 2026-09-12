from decimal import Decimal
from uuid import uuid4

from sqlalchemy import CheckConstraint, Enum as SqlEnum, Numeric, SmallInteger

from backend.app.models import Client, ClientStatus, Deal, PipelineStage, User, UserRole


def test_client_model_has_approved_status_and_contact_fields() -> None:
    columns = Client.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "name",
        "contact_person",
        "email",
        "phone",
        "telegram",
        "telegram_provider_user_id",
        "whatsapp",
        "company",
        "lead_source",
        "notes",
        "status",
        "preferred_communication_language",
        "created_at",
        "updated_at",
    }
    assert columns["name"].nullable is False
    assert isinstance(columns["status"].type, SqlEnum)
    assert set(columns["status"].type.enums) == {"CUSTOMER", "CLIENT"}
    assert columns["status"].default.arg is ClientStatus.CUSTOMER
    assert columns["status"].nullable is False
    assert columns["email"].unique is not True
    assert columns["phone"].unique is not True
    assert columns["telegram_provider_user_id"].unique is True


def test_pipeline_stage_is_database_ordered_data() -> None:
    columns = PipelineStage.__table__.columns

    assert set(columns.keys()) == {"id", "name", "position"}
    assert columns["name"].nullable is False
    assert columns["name"].unique
    assert columns["position"].nullable is False
    assert columns["position"].unique


def test_deal_model_has_required_foreign_keys_and_constraints() -> None:
    columns = Deal.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "name",
        "description",
        "estimated_budget",
        "first_won_at",
        "deadline",
        "stage_id",
        "probability",
        "client_id",
        "responsible_user_id",
        "service_id",
        "manager_effort_estimate",
        "created_at",
        "updated_at",
    }
    assert isinstance(columns["estimated_budget"].type, Numeric)
    assert columns["estimated_budget"].type.precision == 14
    assert columns["estimated_budget"].type.scale == 2
    assert isinstance(columns["probability"].type, SmallInteger)
    assert columns["client_id"].nullable is False
    assert columns["stage_id"].nullable is False
    assert columns["responsible_user_id"].nullable is True
    assert {fk.target_fullname for fk in columns["client_id"].foreign_keys} == {
        "clients.id"
    }
    assert {fk.target_fullname for fk in columns["stage_id"].foreign_keys} == {
        "pipeline_stages.id"
    }
    assert {
        fk.target_fullname for fk in columns["responsible_user_id"].foreign_keys
    } == {"users.id"}
    assert any(
        isinstance(constraint, CheckConstraint)
        and constraint.name == "ck_deals_probability_range"
        for constraint in Deal.__table__.constraints
    )


def test_deal_relationships_support_assigned_and_unassigned_ownership() -> None:
    client = Client(name="Synthetic Client", status=ClientStatus.CUSTOMER)
    stage = PipelineStage(name="Synthetic Stage", position=1)
    unassigned = Deal(
        name="Unassigned Deal",
        estimated_budget=Decimal("1000.00"),
        client=client,
        stage=stage,
        probability=25,
    )

    assert unassigned.client is client
    assert unassigned.stage is stage
    assert unassigned.responsible_user is None
    assert unassigned in client.deals
    assert unassigned in stage.deals

    manager = User(
        id=uuid4(),
        email="crm-model-manager@example.test",
        password_hash="$argon2id$synthetic-hash",
        display_name="Synthetic Manager",
        role=UserRole.MANAGER,
    )
    unassigned.responsible_user = manager

    assert unassigned.responsible_user is manager
    assert unassigned in manager.responsible_deals
