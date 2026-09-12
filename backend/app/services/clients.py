from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import Client, ClientStatus
from backend.app.models.user import utc_now
from backend.app.core.identity import normalize_email


class ClientServiceError(ValueError):
    pass


class ClientNotFoundError(ClientServiceError):
    pass


class ClientPersistenceError(ClientServiceError):
    pass


class ClientEmailConflictError(ClientServiceError):
    pass


def list_clients(session: Session, *, limit: int, offset: int, archived: bool = False) -> list[Client]:
    statement = (
        select(Client)
        .where(Client.archived_at.is_not(None) if archived else Client.archived_at.is_(None))
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


def archive_client(session: Session, *, client_id: UUID) -> Client:
    client = get_client(session, client_id=client_id)
    if client.archived_at is None:
        client.archived_at = utc_now()
        _commit(session, client)
    return client


def restore_client(session: Session, *, client_id: UUID) -> Client:
    client = get_client(session, client_id=client_id)
    if client.archived_at is not None:
        client.archived_at = None
        _commit(session, client)
    return client


def _commit(session: Session, client: Client) -> None:
    try:
        session.commit(); session.refresh(client)
    except SQLAlchemyError as error:
        session.rollback(); raise ClientPersistenceError from error


def create_client(session: Session, *, values: dict) -> Client:
    values = dict(values)
    values["email"] = normalize_email(values.get("email"))
    _ensure_email_available(session, email=values["email"])
    client = Client(**values, status=ClientStatus.CUSTOMER)
    session.add(client)
    try:
        session.commit()
        session.refresh(client)
    except IntegrityError as error:
        session.rollback()
        raise ClientEmailConflictError from error
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

    if "email" in changes:
        changes = dict(changes)
        changes["email"] = normalize_email(changes["email"])
        _ensure_email_available(session, email=changes["email"], excluding_client_id=client.id)

    for field, value in changes.items():
        setattr(client, field, value)

    try:
        session.commit()
        session.refresh(client)
    except IntegrityError as error:
        session.rollback()
        raise ClientEmailConflictError from error
    except SQLAlchemyError as error:
        session.rollback()
        raise ClientPersistenceError from error
    return client


def find_client_by_email(session: Session, email: str | None) -> Client | None:
    normalized = normalize_email(email)
    if normalized is None:
        return None
    return session.scalar(select(Client).where(func.lower(func.btrim(Client.email)) == normalized))


def _ensure_email_available(session: Session, *, email: str | None, excluding_client_id: UUID | None = None) -> None:
    if email is None:
        return
    statement = select(Client.id).where(func.lower(func.btrim(Client.email)) == email)
    if excluding_client_id is not None:
        statement = statement.where(Client.id != excluding_client_id)
    if session.scalar(statement) is not None:
        raise ClientEmailConflictError
