from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, String, Text, Uuid

from backend.app.models import (
    Client,
    Communication,
    CommunicationChannel,
    CommunicationDirection,
    CommunicationStatus,
    Deal,
    Task,
    TaskStatus,
    User,
    UserRole,
)


def test_communication_model_matches_the_day_3_persistence_contract() -> None:
    columns = Communication.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "client_id",
        "deal_id",
        "channel",
        "direction",
        "content",
        "occurred_at",
        "status",
    }
    assert isinstance(columns["id"].type, Uuid)
    assert columns["client_id"].nullable is False
    assert columns["deal_id"].nullable is True
    assert isinstance(columns["content"].type, Text)
    assert isinstance(columns["occurred_at"].type, DateTime)
    assert columns["occurred_at"].type.timezone is True
    assert isinstance(columns["channel"].type, SqlEnum)
    assert set(columns["channel"].type.enums) == {item.value for item in CommunicationChannel}
    assert set(columns["direction"].type.enums) == {
        item.value for item in CommunicationDirection
    }
    assert set(columns["status"].type.enums) == {CommunicationStatus.RECORDED.value}
    assert {fk.target_fullname for fk in columns["client_id"].foreign_keys} == {
        "clients.id"
    }
    assert {fk.target_fullname for fk in columns["deal_id"].foreign_keys} == {
        "deals.id"
    }


def test_task_model_matches_the_day_3_persistence_contract() -> None:
    columns = Task.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "title",
        "description",
        "due_at",
        "status",
        "responsible_user_id",
        "client_id",
        "deal_id",
    }
    assert isinstance(columns["id"].type, Uuid)
    assert isinstance(columns["title"].type, String)
    assert columns["title"].type.length == 255
    assert columns["title"].nullable is False
    assert isinstance(columns["description"].type, Text)
    assert columns["description"].nullable is True
    assert isinstance(columns["due_at"].type, DateTime)
    assert columns["due_at"].type.timezone is True
    assert columns["due_at"].nullable is False
    assert isinstance(columns["status"].type, SqlEnum)
    assert set(columns["status"].type.enums) == {item.value for item in TaskStatus}
    assert columns["status"].default.arg is TaskStatus.OPEN
    assert columns["responsible_user_id"].nullable is False
    assert columns["client_id"].nullable is True
    assert columns["deal_id"].nullable is True
    assert {
        fk.target_fullname for fk in columns["responsible_user_id"].foreign_keys
    } == {"users.id"}
    assert {fk.target_fullname for fk in columns["client_id"].foreign_keys} == {
        "clients.id"
    }
    assert {fk.target_fullname for fk in columns["deal_id"].foreign_keys} == {
        "deals.id"
    }


def test_day_3_relationships_connect_to_existing_domain_models() -> None:
    client = Client(name="Relationship Client")
    manager = User(
        email="relationship-manager@example.test",
        password_hash="$argon2id$synthetic-hash",
        display_name="Relationship Manager",
        role=UserRole.MANAGER,
    )
    deal = Deal(name="Relationship Deal", client=client, stage_id=uuid4())
    occurred_at = datetime.now(timezone.utc)
    communication = Communication(
        client=client,
        deal=deal,
        channel=CommunicationChannel.MANUAL,
        direction=CommunicationDirection.OUTGOING,
        content="Recorded contact",
        occurred_at=occurred_at,
        status=CommunicationStatus.RECORDED,
    )
    task = Task(
        title="Follow up",
        due_at=occurred_at,
        responsible_user=manager,
        client=client,
        deal=deal,
    )

    assert communication in client.communications
    assert communication in deal.communications
    assert task in manager.responsible_tasks
    assert task in client.tasks
    assert task in deal.tasks
    assert Task.__table__.columns["status"].default.arg is TaskStatus.OPEN
