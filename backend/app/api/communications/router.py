from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.communications import CommunicationCreate, CommunicationResponse
from backend.app.services.communications import (
    CommunicationClientNotFoundError,
    CommunicationCreateForbiddenError,
    CommunicationDealClientMismatchError,
    CommunicationDealNotFoundError,
    CommunicationNotFoundError,
    CommunicationPersistenceError,
    create_communication,
    get_communication,
    list_communications,
)


router = APIRouter(prefix="/communications", tags=["communications"])


@router.post("", response_model=CommunicationResponse, status_code=status.HTTP_201_CREATED)
async def post_communication(
    payload: CommunicationCreate,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return create_communication(
            session,
            values=payload.model_dump(),
            current_user=current_user,
        )
    except CommunicationClientNotFoundError as error:
        raise HTTPException(status_code=404, detail="Client not found") from error
    except CommunicationDealNotFoundError as error:
        raise HTTPException(status_code=404, detail="Deal not found") from error
    except CommunicationDealClientMismatchError as error:
        raise HTTPException(status_code=422, detail="Deal does not belong to client") from error
    except CommunicationCreateForbiddenError as error:
        raise HTTPException(
            status_code=403,
            detail="Managers can only record communications for their responsible deals",
        ) from error
    except CommunicationPersistenceError as error:
        raise _persistence_error() from error


@router.get("", response_model=list[CommunicationResponse])
async def get_communications(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    client_id: UUID | None = None,
    deal_id: UUID | None = None,
):
    try:
        return list_communications(
            session,
            limit=limit,
            offset=offset,
            client_id=client_id,
            deal_id=deal_id,
        )
    except CommunicationPersistenceError as error:
        raise _persistence_error() from error


@router.get("/{communication_id}", response_model=CommunicationResponse)
async def get_communication_by_id(
    communication_id: UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return get_communication(session, communication_id=communication_id)
    except CommunicationNotFoundError as error:
        raise HTTPException(status_code=404, detail="Communication not found") from error
    except CommunicationPersistenceError as error:
        raise _persistence_error() from error


def _persistence_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Communication operation failed",
    )
