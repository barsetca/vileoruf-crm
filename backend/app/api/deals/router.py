from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.deals import DealCreate, DealResponse, DealTransition, DealUpdate
from backend.app.services.deals import (
    DealClientNotFoundError,
    DealEditForbiddenError,
    DealNotFoundError,
    DealPersistenceError,
    DealStageNotFoundError,
    InvalidResponsibleUserError,
    ResponsibleAssignmentForbiddenError,
    ResponsibleUserNotFoundError,
    create_deal,
    get_deal,
    list_deals,
    transition_deal,
    update_deal,
)


router = APIRouter(prefix="/deals", tags=["deals"])


@router.post("", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def post_deal(
    payload: DealCreate,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return create_deal(
            session,
            values=payload.model_dump(),
            current_user=current_user,
            responsible_was_supplied="responsible_user_id" in payload.model_fields_set,
        )
    except DealClientNotFoundError as error:
        raise HTTPException(status_code=404, detail="Client not found") from error
    except DealStageNotFoundError as error:
        raise HTTPException(status_code=404, detail="Pipeline stage not found") from error
    except ResponsibleUserNotFoundError as error:
        raise HTTPException(status_code=404, detail="Responsible user not found") from error
    except InvalidResponsibleUserError as error:
        raise HTTPException(
            status_code=422,
            detail="Responsible user must be an active ADMIN or MANAGER",
        ) from error
    except ResponsibleAssignmentForbiddenError as error:
        raise HTTPException(
            status_code=403,
            detail="Managers cannot assign responsible users",
        ) from error
    except DealPersistenceError as error:
        raise _persistence_error() from error


@router.get("", response_model=list[DealResponse])
async def get_deals(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    try:
        return list_deals(session, limit=limit, offset=offset)
    except DealPersistenceError as error:
        raise _persistence_error() from error


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal_by_id(
    deal_id: UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return get_deal(session, deal_id=deal_id)
    except DealNotFoundError as error:
        raise HTTPException(status_code=404, detail="Deal not found") from error
    except DealPersistenceError as error:
        raise _persistence_error() from error


@router.patch("/{deal_id}", response_model=DealResponse)
async def patch_deal(
    deal_id: UUID,
    payload: DealUpdate,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return update_deal(
            session,
            deal_id=deal_id,
            changes=payload.model_dump(exclude_unset=True),
            current_user=current_user,
        )
    except DealNotFoundError as error:
        raise HTTPException(status_code=404, detail="Deal not found") from error
    except DealEditForbiddenError as error:
        raise HTTPException(
            status_code=403,
            detail="Deal can only be edited by its responsible manager",
        ) from error
    except ResponsibleAssignmentForbiddenError as error:
        raise HTTPException(
            status_code=403,
            detail="Managers cannot assign responsible users",
        ) from error
    except ResponsibleUserNotFoundError as error:
        raise HTTPException(status_code=404, detail="Responsible user not found") from error
    except InvalidResponsibleUserError as error:
        raise HTTPException(
            status_code=422,
            detail="Responsible user must be an active ADMIN or MANAGER",
        ) from error
    except DealPersistenceError as error:
        raise _persistence_error() from error


def _persistence_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Deal operation failed",
    )


@router.post("/{deal_id}/transition", response_model=DealResponse)
async def post_deal_transition(
    deal_id: UUID,
    payload: DealTransition,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return transition_deal(
            session,
            deal_id=deal_id,
            stage_id=payload.stage_id,
            current_user=current_user,
        )
    except DealNotFoundError as error:
        raise HTTPException(status_code=404, detail="Deal not found") from error
    except DealStageNotFoundError as error:
        raise HTTPException(status_code=404, detail="Pipeline stage not found") from error
    except DealEditForbiddenError as error:
        raise HTTPException(
            status_code=403,
            detail="Deal can only be transitioned by its responsible manager",
        ) from error
    except DealPersistenceError as error:
        raise _persistence_error() from error
