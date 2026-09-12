from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user, require_admin
from backend.app.db.session import get_db
from backend.app.models import User, UserRole
from backend.app.schemas.deals import DealCreate, DealResponse, DealTransition, DealUpdate
from backend.app.schemas.public_requests import PublicRequestSnapshotResponse
from backend.app.models import PublicRequest
from backend.app.services.deals import (
    DealClientNotFoundError,
    DealEditForbiddenError,
    DealNotFoundError,
    DealPersistenceError,
    DealStageNotFoundError,
    DealServiceNotFoundError,
    InactiveDealServiceError,
    InvalidResponsibleUserError,
    ResponsibleAssignmentForbiddenError,
    ResponsibleUserNotFoundError,
    create_deal,
    archive_deal,
    get_deal,
    list_deals,
    restore_deal,
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
        values = payload.model_dump()
        analysis_language = values.pop("ai_analysis_language")
        return create_deal(
            session,
            values=values,
            current_user=current_user,
            responsible_was_supplied="responsible_user_id" in payload.model_fields_set,
            analysis_language=analysis_language,
        )
    except DealClientNotFoundError as error:
        raise HTTPException(status_code=404, detail="Client not found") from error
    except DealStageNotFoundError as error:
        raise HTTPException(status_code=404, detail="Pipeline stage not found") from error
    except DealServiceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Service not found") from error
    except InactiveDealServiceError as error:
        raise HTTPException(status_code=422, detail="Service and Category must be active") from error
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
    archived: bool = False,
):
    try:
        if archived and current_user.role.value != "ADMIN":
            raise HTTPException(status_code=403, detail="Administrator access required")
        return list_deals(session, limit=limit, offset=offset, archived=archived)
    except DealPersistenceError as error:
        raise _persistence_error() from error


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal_by_id(
    deal_id: UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        deal = get_deal(session, deal_id=deal_id)
        if deal.archived_at is not None and current_user.role is not UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
        return deal
    except DealNotFoundError as error:
        raise HTTPException(status_code=404, detail="Deal not found") from error
    except DealPersistenceError as error:
        raise _persistence_error() from error


@router.get("/{deal_id}/public-request", response_model=PublicRequestSnapshotResponse | None)
async def get_deal_public_request(
    deal_id: UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        deal = get_deal(session, deal_id=deal_id)
        if deal.archived_at is not None and current_user.role is not UserRole.ADMIN:
            raise HTTPException(status_code=404, detail="Deal not found")
        return session.scalar(select(PublicRequest).where(PublicRequest.deal_id == deal.id))
    except DealNotFoundError as error:
        raise HTTPException(status_code=404, detail="Deal not found") from error


@router.patch("/{deal_id}", response_model=DealResponse)
async def patch_deal(
    deal_id: UUID,
    payload: DealUpdate,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        existing = get_deal(session, deal_id=deal_id)
        if existing.archived_at is not None and current_user.role is not UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
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
    except DealServiceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Service not found") from error
    except InactiveDealServiceError as error:
        raise HTTPException(status_code=422, detail="Service and Category must be active") from error
    except DealPersistenceError as error:
        raise _persistence_error() from error


def _persistence_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Deal operation failed",
    )


@router.post("/{deal_id}/archive", response_model=DealResponse)
async def post_deal_archive(deal_id: UUID, session: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(require_admin)]):
    try: return archive_deal(session, deal_id=deal_id)
    except DealNotFoundError as error: raise HTTPException(status_code=404, detail="Deal not found") from error
    except DealPersistenceError as error: raise _persistence_error() from error


@router.post("/{deal_id}/restore", response_model=DealResponse)
async def post_deal_restore(deal_id: UUID, session: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(require_admin)]):
    try: return restore_deal(session, deal_id=deal_id)
    except DealNotFoundError as error: raise HTTPException(status_code=404, detail="Deal not found") from error
    except DealPersistenceError as error: raise _persistence_error() from error


@router.post("/{deal_id}/transition", response_model=DealResponse)
async def post_deal_transition(
    deal_id: UUID,
    payload: DealTransition,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        existing = get_deal(session, deal_id=deal_id)
        if existing.archived_at is not None:
            raise DealNotFoundError
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
