from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import (
    Client,
    Communication,
    CommunicationStatus,
    Deal,
    User,
    UserRole,
)
from backend.app.services.ai.deal_prediction import invalidate_latest_deal_prediction
from backend.app.services.ai.next_best_action import invalidate_latest_next_best_action


class CommunicationServiceError(ValueError):
    pass


class CommunicationNotFoundError(CommunicationServiceError):
    pass


class CommunicationClientNotFoundError(CommunicationServiceError):
    pass


class CommunicationDealNotFoundError(CommunicationServiceError):
    pass


class CommunicationDealClientMismatchError(CommunicationServiceError):
    pass


class CommunicationCreateForbiddenError(CommunicationServiceError):
    pass


class CommunicationPersistenceError(CommunicationServiceError):
    pass


def list_communications(
    session: Session,
    *,
    limit: int,
    offset: int,
    client_id: UUID | None,
    deal_id: UUID | None,
) -> list[Communication]:
    statement = select(Communication)
    if client_id is not None:
        statement = statement.where(Communication.client_id == client_id)
    if deal_id is not None:
        statement = statement.where(Communication.deal_id == deal_id)
    statement = (
        statement.order_by(Communication.occurred_at.desc(), Communication.id.desc())
        .limit(limit)
        .offset(offset)
    )
    try:
        return list(session.scalars(statement))
    except SQLAlchemyError as error:
        session.rollback()
        raise CommunicationPersistenceError from error


def get_communication(session: Session, *, communication_id: UUID) -> Communication:
    try:
        communication = session.get(Communication, communication_id)
    except SQLAlchemyError as error:
        session.rollback()
        raise CommunicationPersistenceError from error
    if communication is None:
        raise CommunicationNotFoundError
    return communication


def create_communication(
    session: Session,
    *,
    values: dict,
    current_user: User,
) -> Communication:
    try:
        client = session.get(Client, values["client_id"])
        if client is None:
            raise CommunicationClientNotFoundError

        deal_id = values.get("deal_id")
        if deal_id is not None:
            deal = session.get(Deal, deal_id)
            if deal is None:
                raise CommunicationDealNotFoundError
            if deal.client_id != client.id:
                raise CommunicationDealClientMismatchError
            if (
                current_user.role is UserRole.MANAGER
                and deal.responsible_user_id != current_user.id
            ):
                raise CommunicationCreateForbiddenError

        communication = Communication(**values, status=CommunicationStatus.RECORDED)
        session.add(communication)
        if communication.deal_id is not None:
            invalidate_latest_deal_prediction(session, deal_id=communication.deal_id)
            invalidate_latest_next_best_action(session, deal_id=communication.deal_id)
        session.commit()
        session.refresh(communication)
        return communication
    except CommunicationServiceError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise CommunicationPersistenceError from error
