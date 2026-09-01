from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.clients import ClientCreate, ClientResponse, ClientUpdate
from backend.app.services.clients import (
    ClientNotFoundError,
    ClientPersistenceError,
    create_client,
    get_client,
    list_clients,
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
):
    try:
        return list_clients(session, limit=limit, offset=offset)
    except ClientPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Client operation failed",
        ) from error


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client_by_id(
    client_id: UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return get_client(session, client_id=client_id)
    except ClientNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from error
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
    except ClientPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Client operation failed",
        ) from error
