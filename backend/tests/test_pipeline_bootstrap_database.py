import os
from collections.abc import Iterator
from io import StringIO
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.models import Client, Deal, PipelineStage, User
from backend.app.scripts.bootstrap_pipeline import (
    SYSTEM_PIPELINE,
    bootstrap_system_pipeline,
    main,
)


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)


@pytest.fixture
def isolated_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[sessionmaker[Session]]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_pipeline_bootstrap_test_{uuid4().hex}"
    maintenance_engine = create_engine(
        source_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    isolated_url = source_url.set(database=database_name)
    isolated_engine = None
    database_created = False

    try:
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
        database_created = True
        monkeypatch.setenv("DATABASE_URL", isolated_url.render_as_string(False))
        get_settings.cache_clear()
        command.upgrade(Config("backend/alembic.ini"), "head")
        isolated_engine = create_engine(isolated_url, pool_pre_ping=True)
        yield sessionmaker(
            bind=isolated_engine,
            autoflush=False,
            expire_on_commit=False,
        )
    finally:
        get_settings.cache_clear()
        if isolated_engine is not None:
            isolated_engine.dispose()
        if database_created:
            with maintenance_engine.connect() as connection:
                connection.exec_driver_sql(
                    f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'
                )
        maintenance_engine.dispose()


def read_pipeline(session_factory: sessionmaker[Session]) -> list[tuple[str, int]]:
    with session_factory() as session:
        return list(
            session.execute(
                select(PipelineStage.name, PipelineStage.position).order_by(
                    PipelineStage.position
                )
            ).tuples()
        )


def test_empty_pipeline_bootstrap_is_idempotent(
    isolated_session_factory: sessionmaker[Session],
) -> None:
    with isolated_session_factory() as session:
        first = bootstrap_system_pipeline(session, app_env="test")
        assert [(stage.name, stage.position) for stage in first] == list(
            SYSTEM_PIPELINE
        )

    with isolated_session_factory() as session:
        second = bootstrap_system_pipeline(session, app_env="test")
        assert [(stage.name, stage.position) for stage in second] == list(
            SYSTEM_PIPELINE
        )

    assert read_pipeline(isolated_session_factory) == list(SYSTEM_PIPELINE)
    with isolated_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Client)) == 0
        assert session.scalar(select(func.count()).select_from(Deal)) == 0
        assert session.scalar(select(func.count()).select_from(User)) == 0


def test_partial_system_pipeline_is_completed_and_reordered(
    isolated_session_factory: sessionmaker[Session],
) -> None:
    with isolated_session_factory() as session:
        session.add_all(
            [
                PipelineStage(name="New Lead", position=10),
                PipelineStage(name="Contact", position=11),
                PipelineStage(name="Proposal", position=4),
            ]
        )
        session.commit()

    with isolated_session_factory() as session:
        bootstrap_system_pipeline(session, app_env="development")

    assert read_pipeline(isolated_session_factory) == list(SYSTEM_PIPELINE)


def test_conflict_rolls_back_without_changing_user_stage_or_partial_bootstrap(
    isolated_session_factory: sessionmaker[Session],
) -> None:
    custom_stage_id = uuid4()
    with isolated_session_factory() as session:
        session.add(
            PipelineStage(
                id=custom_stage_id,
                name="Custom Review",
                position=3,
            )
        )
        session.commit()

    stdout = StringIO()
    stderr = StringIO()
    exit_code = main(
        session_factory=isolated_session_factory,
        settings_factory=get_settings,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "Position 3" in stderr.getvalue()

    with isolated_session_factory() as session:
        persisted = session.get(PipelineStage, custom_stage_id)
        assert persisted is not None
        assert (persisted.name, persisted.position) == ("Custom Review", 3)
        assert read_pipeline(isolated_session_factory) == [("Custom Review", 3)]


@pytest.mark.parametrize("app_env", ["development", "test", "production"])
def test_cli_allows_each_official_environment_in_isolated_database(
    isolated_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    get_settings.cache_clear()
    stdout = StringIO()
    stderr = StringIO()

    try:
        exit_code = main(
            session_factory=isolated_session_factory,
            settings_factory=get_settings,
            stdout=stdout,
            stderr=stderr,
        )
    finally:
        get_settings.cache_clear()

    assert exit_code == 0
    assert f"System pipeline ready in {app_env}: 7 stages." in stdout.getvalue()
    assert stderr.getvalue() == ""
    assert read_pipeline(isolated_session_factory) == list(SYSTEM_PIPELINE)
