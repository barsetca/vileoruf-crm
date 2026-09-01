from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import PipelineStage, User


class ReferenceDataPersistenceError(ValueError):
    pass


def list_pipeline_stages(session: Session) -> list[PipelineStage]:
    try:
        return list(session.scalars(select(PipelineStage).order_by(PipelineStage.position)))
    except SQLAlchemyError as error:
        session.rollback()
        raise ReferenceDataPersistenceError from error


def list_employee_references(session: Session) -> list[User]:
    try:
        return list(session.scalars(select(User).order_by(User.display_name, User.id)))
    except SQLAlchemyError as error:
        session.rollback()
        raise ReferenceDataPersistenceError from error
