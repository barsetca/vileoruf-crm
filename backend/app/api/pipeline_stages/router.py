from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.reference_data import PipelineStageReference
from backend.app.services.reference_data import (
    ReferenceDataPersistenceError,
    list_pipeline_stages,
)


router = APIRouter(prefix="/pipeline-stages", tags=["pipeline-stages"])


@router.get("", response_model=list[PipelineStageReference])
async def get_pipeline_stages(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return list_pipeline_stages(session)
    except ReferenceDataPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reference data operation failed",
        ) from error
