from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import AIResultLanguage
from backend.app.schemas.public_requests import PublicRequestCreate, PublicRequestResponse
from backend.app.services.public_requests import PublicRequestError, create_public_request
from backend.app.schemas.business import ServiceResponse
from backend.app.services.business import list_services


router = APIRouter(prefix="/public", tags=["public"])


@router.get("/services", response_model=list[ServiceResponse])
async def get_public_services(session: Annotated[Session, Depends(get_db)]):
    return list_services(session, active_only=True)


@router.post("/requests", response_model=PublicRequestResponse, status_code=status.HTTP_201_CREATED)
async def post_public_request(payload: PublicRequestCreate, session: Annotated[Session, Depends(get_db)]):
    try:
        create_public_request(
            session,
            values=payload.model_dump(),
            analysis_language=AIResultLanguage.RU,
        )
    except PublicRequestError as error:
        raise HTTPException(status_code=503, detail="Request could not be accepted") from error
    return PublicRequestResponse()
