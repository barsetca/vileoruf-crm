import os
from collections.abc import Iterator
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import Client, ClientStatus, Deal, PipelineStage, User, UserRole


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)


@pytest.fixture
def isolated_database_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[URL]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_crm_schema_test_{uuid4().hex}"
    maintenance_engine = create_engine(
        source_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    isolated_url = source_url.set(database=database_name)
    database_created = False

    try:
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
        database_created = True
        monkeypatch.setenv("DATABASE_URL", isolated_url.render_as_string(False))
        get_settings.cache_clear()
        yield isolated_url
    finally:
        get_settings.cache_clear()
        if database_created:
            with maintenance_engine.connect() as connection:
                connection.exec_driver_sql(
                    f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'
                )
        maintenance_engine.dispose()


def test_crm_migration_upgrade_downgrade_and_persistence(
    isolated_database_url: URL,
) -> None:
    alembic_config = Config("backend/alembic.ini")
    command.upgrade(alembic_config, "head")

    engine = create_engine(isolated_database_url)
    try:
        inspector = inspect(engine)
        assert {"users", "clients", "pipeline_stages", "deals"}.issubset(
            inspector.get_table_names()
        )
        client_status = next(
            enum for enum in inspector.get_enums() if enum["name"] == "client_status"
        )
        assert set(client_status["labels"]) == {"CUSTOMER", "CLIENT"}
        deal_columns = {column["name"]: column for column in inspector.get_columns("deals")}
        assert deal_columns["responsible_user_id"]["nullable"] is True

        with Session(engine) as session:
            client = Client(name="Migration Test Client")
            stage = PipelineStage(name="Migration Test Stage", position=1)
            manager = User(
                email="crm-migration-manager@example.test",
                password_hash="$argon2id$synthetic-hash",
                display_name="Migration Test Manager",
                role=UserRole.MANAGER,
            )
            unassigned_deal = Deal(
                name="Unassigned Migration Deal",
                estimated_budget=Decimal("2500.50"),
                probability=50,
                client=client,
                stage=stage,
            )
            assigned_deal = Deal(
                name="Assigned Migration Deal",
                client=client,
                stage=stage,
                responsible_user=manager,
            )
            session.add_all([unassigned_deal, assigned_deal])
            session.commit()
            session.refresh(client)
            session.refresh(unassigned_deal)

            assert client.status is ClientStatus.CUSTOMER
            assert unassigned_deal.responsible_user_id is None
            assert assigned_deal.responsible_user_id == manager.id
            assert session.scalar(select(Deal).where(Deal.id == unassigned_deal.id))

            invalid_deal = Deal(
                name="Invalid Probability Deal",
                probability=101,
                client=client,
                stage=stage,
            )
            session.add(invalid_deal)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

        engine.dispose()
        command.downgrade(alembic_config, "20260829_0002")
        downgraded_inspector = inspect(create_engine(isolated_database_url))
        assert "users" in downgraded_inspector.get_table_names()
        assert not {"clients", "pipeline_stages", "deals"}.intersection(
            downgraded_inspector.get_table_names()
        )
        assert "client_status" not in {
            enum["name"] for enum in downgraded_inspector.get_enums()
        }

        command.upgrade(alembic_config, "head")
        upgraded_again_inspector = inspect(create_engine(isolated_database_url))
        assert {"clients", "pipeline_stages", "deals"}.issubset(
            upgraded_again_inspector.get_table_names()
        )
    finally:
        engine.dispose()
