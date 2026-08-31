import os
from collections.abc import Iterator
from io import StringIO
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.core.security import verify_password
from backend.app.db.base import Base
from backend.app.models import User, UserRole
from backend.app.scripts.create_admin import create_first_admin, main


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)

SYNTHETIC_EMAIL = "bootstrap-admin@example.test"
SYNTHETIC_PASSWORD = "synthetic bootstrap password"


@pytest.fixture
def isolated_session_factory() -> Iterator[sessionmaker[Session]]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_bootstrap_test_{uuid4().hex}"
    maintenance_url = source_url.set(database="postgres")
    isolated_url = source_url.set(database=database_name)
    maintenance_engine = create_engine(
        maintenance_url,
        isolation_level="AUTOCOMMIT",
    )
    isolated_engine = None

    try:
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')

        isolated_engine = create_engine(isolated_url, pool_pre_ping=True)
        Base.metadata.create_all(isolated_engine)
        yield sessionmaker(
            bind=isolated_engine,
            autoflush=False,
            expire_on_commit=False,
        )
    finally:
        if isolated_engine is not None:
            isolated_engine.dispose()
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(
                f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'
            )
        maintenance_engine.dispose()


def test_create_first_admin_against_postgresql(
    isolated_session_factory: sessionmaker[Session],
) -> None:
    with isolated_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0

    ordinary_values = iter(
        ["  Bootstrap-Admin@Example.TEST ", "  Synthetic Bootstrap Admin  "]
    )
    secret_values = iter([SYNTHETIC_PASSWORD, SYNTHETIC_PASSWORD])
    stdout = StringIO()
    exit_code = main(
        session_factory=isolated_session_factory,
        input_func=lambda prompt: next(ordinary_values),
        password_input=lambda prompt: next(secret_values),
        stdout=stdout,
    )

    assert exit_code == 0
    assert "ADMIN created successfully." in stdout.getvalue()
    assert SYNTHETIC_PASSWORD not in stdout.getvalue()

    with isolated_session_factory() as session:
        persisted = session.scalar(select(User).where(User.email == SYNTHETIC_EMAIL))
        assert persisted is not None
        assert persisted.email == SYNTHETIC_EMAIL
        assert persisted.display_name == "Synthetic Bootstrap Admin"
        assert persisted.role is UserRole.ADMIN
        assert persisted.is_active is True
        assert persisted.password_hash.startswith("$argon2id$")
        assert persisted.password_hash != SYNTHETIC_PASSWORD
        assert verify_password(SYNTHETIC_PASSWORD, persisted.password_hash)
        assert not hasattr(persisted, "password")

        assert session.scalar(select(func.count()).select_from(User)) == 1


def test_repeated_bootstrap_refuses_without_changing_existing_admin(
    isolated_session_factory: sessionmaker[Session],
) -> None:
    with isolated_session_factory() as session:
        existing = create_first_admin(
            session,
            email=SYNTHETIC_EMAIL,
            display_name="Synthetic Bootstrap Admin",
            password=SYNTHETIC_PASSWORD,
        )
        original = (
            existing.id,
            existing.email,
            existing.role,
            existing.is_active,
            existing.password_hash,
        )

        with pytest.raises(ValueError, match="ADMIN already exists"):
            create_first_admin(
                session,
                email="another-admin@example.test",
                display_name="Another Admin",
                password=SYNTHETIC_PASSWORD,
            )

        persisted = session.get(User, existing.id)
        assert persisted is not None
        assert (
            persisted.id,
            persisted.email,
            persisted.role,
            persisted.is_active,
            persisted.password_hash,
        ) == original
        assert session.scalar(select(func.count()).select_from(User)) == 1
