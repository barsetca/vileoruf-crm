from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import Client, ClientStatus


class ClientServiceError(ValueError):
    pass


class ClientNotFoundError(ClientServiceError):
    pass


class ClientPersistenceError(ClientServiceError):
    pass


def list_clients(session: Session, *, limit: int, offset: int) -> list[Client]:
    statement = (
        select(Client)
        .order_by(Client.created_at.desc(), Client.id.desc())
        .limit(limit)
        .offset(offset)
    )
    try:
        return list(session.scalars(statement))
    except SQLAlchemyError as error:
        session.rollback()
        raise ClientPersistenceError from error


def get_client(session: Session, *, client_id: UUID) -> Client:
    try:
        client = session.get(Client, client_id)
    except SQLAlchemyError as error:
        session.rollback()
        raise ClientPersistenceError from error
    if client is None:
        raise ClientNotFoundError
    return client


def create_client(session: Session, *, values: dict) -> Client:
    client = Client(**values, status=ClientStatus.CUSTOMER)
    session.add(client)
    try:
        session.commit()
        session.refresh(client)
    except SQLAlchemyError as error:
        session.rollback()
        raise ClientPersistenceError from error
    return client


def update_client(
    session: Session,
    *,
    client_id: UUID,
    changes: dict,
) -> Client:
    client = session.get(Client, client_id)
    if client is None:
        raise ClientNotFoundError

    for field, value in changes.items():
        setattr(client, field, value)

    try:
        session.commit()
        session.refresh(client)
    except SQLAlchemyError as error:
        session.rollback()
        raise ClientPersistenceError from error
    return client
