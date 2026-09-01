import sys
from collections.abc import Callable
from typing import TextIO

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import AppEnvironment, Settings, get_settings
from backend.app.db.session import SessionLocal
from backend.app.models import PipelineStage
from backend.app.models.pipeline_stage import SYSTEM_PIPELINE


class PipelineBootstrapError(ValueError):
    """Expected, safe-to-display system pipeline bootstrap failure."""


def bootstrap_system_pipeline(
    session: Session,
    *,
    app_env: AppEnvironment,
) -> list[PipelineStage]:
    try:
        session.execute(
            text("LOCK TABLE pipeline_stages IN SHARE ROW EXCLUSIVE MODE")
        )
        stages = list(session.scalars(select(PipelineStage)))
        system_names = {name for name, _ in SYSTEM_PIPELINE}
        desired_positions = {position: name for name, position in SYSTEM_PIPELINE}

        for stage in stages:
            expected_name = desired_positions.get(stage.position)
            if expected_name is not None and stage.name not in system_names:
                raise PipelineBootstrapError(
                    f"Position {stage.position} required by system stage "
                    f"'{expected_name}' is occupied by non-system stage "
                    f"'{stage.name}'."
                )

        by_name = {stage.name: stage for stage in stages if stage.name in system_names}
        next_temporary_position = max(
            (stage.position for stage in stages),
            default=0,
        ) + 1

        for stage in by_name.values():
            stage.position = next_temporary_position
            next_temporary_position += 1
        session.flush()

        result = []
        for name, position in SYSTEM_PIPELINE:
            stage = by_name.get(name)
            if stage is None:
                stage = PipelineStage(name=name, position=position)
                session.add(stage)
            else:
                stage.position = position
            result.append(stage)

        session.commit()
        for stage in result:
            session.refresh(stage)
        return result
    except PipelineBootstrapError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise PipelineBootstrapError(
            "Database operation failed; system pipeline was not changed."
        ) from error


def main(
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    settings_factory: Callable[[], Settings] = get_settings,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    settings = settings_factory()
    try:
        with session_factory() as session:
            stages = bootstrap_system_pipeline(
                session,
                app_env=settings.app_env,
            )
    except PipelineBootstrapError as error:
        print(f"System pipeline bootstrap failed: {error}", file=stderr)
        return 1

    print(
        f"System pipeline ready in {settings.app_env}: {len(stages)} stages.",
        file=stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
