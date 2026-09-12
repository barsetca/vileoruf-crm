from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user, require_admin
from backend.app.db.session import get_db
from backend.app.models import User, UserRole
from backend.app.schemas.clients import ClientCreate, ClientResponse, ClientUpdate
from backend.app.services.clients import (
    ClientNotFoundError,
    ClientEmailConflictError,
    ClientPersistenceError,
    create_client,
    archive_client,
    get_client,
    list_clients,
    restore_client,
    update_client,
)


router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def post_client(
    payload: ClientCreate,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return create_client(session, values=payload.model_dump())
    except ClientEmailConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A client with this email already exists") from error
    except ClientPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Client operation failed",
        ) from error


@router.get("", response_model=list[ClientResponse])
async def get_clients(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    archived: bool = False,
):
    try:
        if archived and current_user.role.value != "ADMIN":
            raise HTTPException(status_code=403, detail="Administrator access required")
        return list_clients(session, limit=limit, offset=offset, archived=archived)
    except ClientEmailConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A client with this email already exists") from error
    except ClientPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Client operation failed",
        ) from error


@router.post("/{client_id}/archive", response_model=ClientResponse)
async def post_client_archive(client_id: UUID, session: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(require_admin)]):
    try: return archive_client(session, client_id=client_id)
    except ClientNotFoundError as error: raise HTTPException(status_code=404, detail="Client not found") from error
    except ClientPersistenceError as error: raise HTTPException(status_code=500, detail="Client operation failed") from error


@router.post("/{client_id}/restore", response_model=ClientResponse)
async def post_client_restore(client_id: UUID, session: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(require_admin)]):
    try: return restore_client(session, client_id=client_id)
    except ClientNotFoundError as error: raise HTTPException(status_code=404, detail="Client not found") from error
    except ClientPersistenceError as error: raise HTTPException(status_code=500, detail="Client operation failed") from error


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client_by_id(
    client_id: UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        client = get_client(session, client_id=client_id)
        if client.archived_at is not None and current_user.role is not UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        return client
    except ClientNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from error
    except ClientEmailConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A client with this email already exists") from error
    except ClientPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Client operation failed",
        ) from error


@router.patch("/{client_id}", response_model=ClientResponse)
async def patch_client(
    client_id: UUID,
    payload: ClientUpdate,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        existing = get_client(session, client_id=client_id)
        if existing.archived_at is not None and current_user.role is not UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        return update_client(
            session,
            client_id=client_id,
            changes=payload.model_dump(exclude_unset=True),
        )
    except ClientNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from error
    except ClientEmailConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A client with this email already exists") from error
    except ClientPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Client operation failed",
        ) from error
