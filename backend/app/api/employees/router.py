from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.reference_data import EmployeeReference
from backend.app.services.reference_data import (
    ReferenceDataPersistenceError,
    list_employee_references,
)


router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("/reference", response_model=list[EmployeeReference])
async def get_employee_references(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return list_employee_references(session)
    except ReferenceDataPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reference data operation failed",
        ) from error
