from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.public_requests import PublicRequestCreate, PublicRequestResponse
from backend.app.services.public_requests import PublicRequestError, create_public_request


router = APIRouter(prefix="/public", tags=["public"])


@router.post("/requests", response_model=PublicRequestResponse, status_code=status.HTTP_201_CREATED)
async def post_public_request(payload: PublicRequestCreate, session: Annotated[Session, Depends(get_db)]):
    try:
        create_public_request(session, values=payload.model_dump())
    except PublicRequestError as error:
        raise HTTPException(status_code=503, detail="Request could not be accepted") from error
    return PublicRequestResponse()
