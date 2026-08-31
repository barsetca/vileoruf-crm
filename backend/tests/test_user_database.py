import os
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from backend.app.db.session import SessionLocal
from backend.app.models import User, UserRole


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)


def test_user_persistence_constraints_defaults_and_update_timestamp() -> None:
    email = f"user-model-{uuid4()}@example.test"

    try:
        with SessionLocal() as session:
            user = User(
                email=email,
                password_hash="$argon2id$persisted-hash-only",
                display_name="Database Test User",
                role=UserRole.ADMIN,
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.id is not None
            assert user.role is UserRole.ADMIN
            assert user.is_active is True
            assert user.created_at.tzinfo is not None
            assert user.updated_at.tzinfo is not None
            assert user.password_hash == "$argon2id$persisted-hash-only"
            assert not hasattr(user, "password")

            original_updated_at = user.updated_at
            user.display_name = "Updated Database Test User"
            session.commit()
            session.refresh(user)

            assert user.updated_at > original_updated_at

            session.add(
                User(
                    email=email,
                    password_hash="$argon2id$another-persisted-hash",
                    display_name="Duplicate Email",
                    role=UserRole.MANAGER,
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        with SessionLocal() as cleanup_session:
            cleanup_session.execute(delete(User).where(User.email == email))
            cleanup_session.commit()
