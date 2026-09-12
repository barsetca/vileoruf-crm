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
from backend.app.models.communication import CommunicationDirection
from backend.app.models.integrations import ExternalMessage
from backend.app.models.user import utc_now
from backend.app.services.ai.deal_prediction import invalidate_latest_deal_prediction
from backend.app.services.ai.next_best_action import invalidate_latest_next_best_action
from backend.app.services.business import invalidate_latest_lead_scoring


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


class CommunicationMutationError(CommunicationServiceError):
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

        communication = Communication(
            **values,
            status=CommunicationStatus.RECORDED,
            read_at=None if values["direction"] == CommunicationDirection.INCOMING else None,
        )
        session.add(communication)
        if communication.deal_id is not None:
            invalidate_latest_lead_scoring(session, deal_id=communication.deal_id)
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


def _assert_mutable_incoming(session: Session, communication_id: UUID, current_user: User) -> Communication:
    communication = session.get(Communication, communication_id)
    if communication is None or communication.direction != CommunicationDirection.INCOMING:
        raise CommunicationNotFoundError
    client = session.get(Client, communication.client_id)
    if client is None or client.archived_at is not None:
        raise CommunicationMutationError
    if current_user.role is UserRole.MANAGER and communication.deal_id is not None:
        deal = session.get(Deal, communication.deal_id)
        if deal is None or deal.responsible_user_id != current_user.id:
            raise CommunicationCreateForbiddenError
    return communication


def mark_communication_read(session: Session, *, communication_id: UUID, current_user: User) -> Communication:
    try:
        communication = _assert_mutable_incoming(session, communication_id, current_user)
        if communication.read_at is None:
            communication.read_at = utc_now()
            session.commit()
            session.refresh(communication)
        return communication
    except CommunicationServiceError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise CommunicationPersistenceError from error


def assign_communication_deal(session: Session, *, communication_id: UUID, deal_id: UUID, current_user: User) -> Communication:
    try:
        communication = _assert_mutable_incoming(session, communication_id, current_user)
        deal = session.get(Deal, deal_id)
        if deal is None or deal.archived_at is not None or deal.client.archived_at is not None:
            raise CommunicationMutationError
        if deal.client_id != communication.client_id:
            raise CommunicationDealClientMismatchError
        if current_user.role is UserRole.MANAGER and deal.responsible_user_id != current_user.id:
            raise CommunicationCreateForbiddenError
        if communication.deal_id != deal.id:
            old_deal_id = communication.deal_id
            communication.deal_id = deal.id
            external = session.scalar(select(ExternalMessage).where(ExternalMessage.communication_id == communication.id))
            if external is not None:
                external.deal_id = deal.id
            if old_deal_id is not None:
                _invalidate_deal(session, old_deal_id)
            _invalidate_deal(session, deal.id)
            session.commit()
            session.refresh(communication)
        return communication
    except CommunicationServiceError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise CommunicationPersistenceError from error


def detach_communication_deal(session: Session, *, communication_id: UUID, current_user: User) -> Communication:
    try:
        communication = _assert_mutable_incoming(session, communication_id, current_user)
        if communication.deal_id is not None:
            old_deal_id = communication.deal_id
            communication.deal_id = None
            external = session.scalar(select(ExternalMessage).where(ExternalMessage.communication_id == communication.id))
            if external is not None:
                external.deal_id = None
            _invalidate_deal(session, old_deal_id)
            session.commit()
            session.refresh(communication)
        return communication
    except CommunicationServiceError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise CommunicationPersistenceError from error


def _invalidate_deal(session: Session, deal_id: UUID) -> None:
    invalidate_latest_lead_scoring(session, deal_id=deal_id)
    invalidate_latest_deal_prediction(session, deal_id=deal_id)
    invalidate_latest_next_best_action(session, deal_id=deal_id)


def unread_communications_summary(session: Session) -> tuple[int, list[tuple[Client, list[Communication]]]]:
    rows = list(session.scalars(
        select(Communication)
        .join(Client)
        .where(Communication.direction == CommunicationDirection.INCOMING, Communication.read_at.is_(None), Client.archived_at.is_(None))
        .order_by(Communication.occurred_at.desc(), Communication.id.desc())
    ))
    grouped: dict[UUID, tuple[Client, list[Communication]]] = {}
    for item in rows:
        if item.client_id not in grouped:
            grouped[item.client_id] = (item.client, [])
        grouped[item.client_id][1].append(item)
    return len(rows), list(grouped.values())
