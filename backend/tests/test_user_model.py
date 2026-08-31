from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, Uuid

from backend.app.models import User, UserRole


def test_user_model_contains_only_approved_persisted_fields() -> None:
    columns = User.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "email",
        "password_hash",
        "display_name",
        "role",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert "password" not in columns
    assert "plain_password" not in columns
    assert "raw_password" not in columns


def test_user_model_database_constraints_and_defaults() -> None:
    columns = User.__table__.columns

    assert isinstance(columns["id"].type, Uuid)
    assert columns["id"].primary_key
    assert columns["email"].unique
    assert columns["email"].nullable is False
    assert columns["email"].type.length == 320
    assert columns["password_hash"].nullable is False
    assert columns["password_hash"].type.length == 512
    assert columns["display_name"].nullable is False
    assert columns["role"].nullable is False
    assert columns["role"].default is None
    assert isinstance(columns["role"].type, SqlEnum)
    assert set(columns["role"].type.enums) == {"ADMIN", "MANAGER"}
    assert columns["is_active"].default.arg is True
    assert columns["is_active"].server_default is not None
    assert isinstance(columns["created_at"].type, DateTime)
    assert columns["created_at"].type.timezone is True
    assert isinstance(columns["updated_at"].type, DateTime)
    assert columns["updated_at"].type.timezone is True
    assert columns["updated_at"].onupdate is not None


def test_user_can_be_constructed_with_each_approved_role() -> None:
    for role in UserRole:
        user_id = uuid4()
        user = User(
            id=user_id,
            email=f"{role.value.lower()}@example.test",
            password_hash="$argon2id$stored-hash-only",
            display_name=role.value.title(),
            role=role,
        )

        assert isinstance(user.id, UUID)
        assert user.id == user_id
        assert user.role is role
        assert isinstance(user.email, str)


def test_user_timestamp_factories_are_timezone_aware() -> None:
    columns = User.__table__.columns
    created_at = columns["created_at"].default.arg(None)
    updated_at = columns["updated_at"].onupdate.arg(None)

    assert isinstance(created_at, datetime)
    assert created_at.tzinfo is not None
    assert isinstance(updated_at, datetime)
    assert updated_at.tzinfo is not None
