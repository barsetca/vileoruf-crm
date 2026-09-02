import os
from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import (
    Client,
    Communication,
    CommunicationChannel,
    CommunicationDirection,
    CommunicationStatus,
    Deal,
    PipelineStage,
    Task,
    TaskStatus,
    User,
    UserRole,
)


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)


@pytest.fixture
def isolated_database_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[URL]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_crm_day3_schema_test_{uuid4().hex}"
    maintenance_engine = create_engine(
        source_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
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


def test_day_3_migration_and_persistence_on_postgresql(
    isolated_database_url: URL,
) -> None:
    alembic_config = Config("backend/alembic.ini")
    command.upgrade(alembic_config, "head")

    engine = create_engine(isolated_database_url)
    try:
        inspector = inspect(engine)
        assert {"communications", "tasks"}.issubset(inspector.get_table_names())
        enums = {enum["name"]: set(enum["labels"]) for enum in inspector.get_enums()}
        assert enums["communication_channel"] == {
            "EMAIL",
            "TELEGRAM",
            "WHATSAPP",
            "MANUAL",
            "OTHER",
        }
        assert enums["communication_direction"] == {"INCOMING", "OUTGOING"}
        assert enums["communication_status"] == {"RECORDED"}
        assert enums["task_status"] == {"OPEN", "COMPLETED"}
        assert {
            index["name"] for index in inspector.get_indexes("communications")
        } == {
            "ix_communications_client_id",
            "ix_communications_deal_id",
            "ix_communications_occurred_at",
        }
        assert {index["name"] for index in inspector.get_indexes("tasks")} == {
            "ix_tasks_client_id",
            "ix_tasks_deal_id",
            "ix_tasks_responsible_user_id",
        }

        occurred_at = datetime.now(timezone.utc)
        with Session(engine) as session:
            manager = User(
                email="day3-manager@example.test",
                password_hash="$argon2id$synthetic-hash",
                display_name="Day 3 Manager",
                role=UserRole.MANAGER,
            )
            client = Client(name="Day 3 Client")
            stage = PipelineStage(name="Day 3 Stage", position=1)
            deal = Deal(name="Day 3 Deal", client=client, stage=stage)
            client_communication = Communication(
                client=client,
                channel=CommunicationChannel.EMAIL,
                direction=CommunicationDirection.INCOMING,
                content="Client-level history",
                occurred_at=occurred_at,
                status=CommunicationStatus.RECORDED,
            )
            deal_communication = Communication(
                client=client,
                deal=deal,
                channel=CommunicationChannel.TELEGRAM,
                direction=CommunicationDirection.OUTGOING,
                content="Deal-linked history",
                occurred_at=occurred_at,
                status=CommunicationStatus.RECORDED,
            )
            general_task = Task(
                title="General task",
                due_at=occurred_at,
                responsible_user=manager,
            )
            client_task = Task(
                title="Client task",
                due_at=occurred_at,
                responsible_user=manager,
                client=client,
            )
            deal_task = Task(
                title="Deal task",
                due_at=occurred_at,
                responsible_user=manager,
                deal=deal,
                status=TaskStatus.COMPLETED,
            )
            combined_task = Task(
                title="Combined task",
                due_at=occurred_at,
                responsible_user=manager,
                client=client,
                deal=deal,
            )
            session.add_all(
                [
                    client_communication,
                    deal_communication,
                    general_task,
                    client_task,
                    deal_task,
                    combined_task,
                ]
            )
            session.commit()
            session.expire_all()

            persisted_client = session.get(Client, client.id)
            persisted_deal = session.get(Deal, deal.id)
            persisted_manager = session.get(User, manager.id)
            assert persisted_client is not None
            assert persisted_deal is not None
            assert persisted_manager is not None
            assert client_communication.deal_id is None
            assert deal_communication.deal_id == deal.id
            assert client_communication.occurred_at.tzinfo is not None
            assert deal_communication in persisted_deal.communications
            assert client_communication in persisted_client.communications
            assert general_task.client_id is None and general_task.deal_id is None
            assert client_task.client_id == client.id and client_task.deal_id is None
            assert deal_task.client_id is None and deal_task.deal_id == deal.id
            assert combined_task.client_id == client.id and combined_task.deal_id == deal.id
            assert general_task.status is TaskStatus.OPEN
            assert deal_task.status is TaskStatus.COMPLETED
            assert combined_task in persisted_deal.tasks
            assert combined_task in persisted_client.tasks
            assert combined_task in persisted_manager.responsible_tasks

            session.add(
                Communication(
                    client_id=uuid4(),
                    channel=CommunicationChannel.OTHER,
                    direction=CommunicationDirection.INCOMING,
                    content="Invalid client",
                    occurred_at=occurred_at,
                    status=CommunicationStatus.RECORDED,
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(
                Communication(
                    client_id=client.id,
                    deal_id=uuid4(),
                    channel=CommunicationChannel.OTHER,
                    direction=CommunicationDirection.INCOMING,
                    content="Invalid deal",
                    occurred_at=occurred_at,
                    status=CommunicationStatus.RECORDED,
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(Task(title="Missing responsible", due_at=occurred_at))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(
                Task(
                    title="Invalid task relation",
                    due_at=occurred_at,
                    responsible_user_id=manager.id,
                    client_id=uuid4(),
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(
                Task(
                    title="Invalid task deal",
                    due_at=occurred_at,
                    responsible_user_id=manager.id,
                    deal_id=uuid4(),
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(
                Task(
                    title="Invalid responsible user",
                    due_at=occurred_at,
                    responsible_user_id=uuid4(),
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(
                Task(due_at=occurred_at, responsible_user_id=manager.id)
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(
                Task(title="Missing due date", responsible_user_id=manager.id)
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

        command.downgrade(alembic_config, "20260831_0003")
        downgraded_engine = create_engine(isolated_database_url)
        try:
            downgraded_inspector = inspect(downgraded_engine)
            assert not {"communications", "tasks"}.intersection(
                downgraded_inspector.get_table_names()
            )
            enum_names = {enum["name"] for enum in downgraded_inspector.get_enums()}
            assert not {
                "communication_channel",
                "communication_direction",
                "communication_status",
                "task_status",
            }.intersection(enum_names)
        finally:
            downgraded_engine.dispose()

        command.upgrade(alembic_config, "head")
        upgraded_engine = create_engine(isolated_database_url)
        try:
            assert {"communications", "tasks"}.issubset(
                inspect(upgraded_engine).get_table_names()
            )
        finally:
            upgraded_engine.dispose()
    finally:
        engine.dispose()
