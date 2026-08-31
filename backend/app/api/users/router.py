from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_admin
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.users import UserCreate, UserResponse, UserUpdate
from backend.app.services.users import AdminSafetyError, DuplicateEmailError, UserManagementError, UserNotFoundError, create_user, list_users, update_user


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def get_users(session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]):
    return list_users(session)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def post_user(payload: UserCreate, session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]):
    try:
        return create_user(session, **payload.model_dump())
    except DuplicateEmailError as error:
        raise HTTPException(status_code=409, detail="User with this email already exists") from error
    except UserManagementError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.patch("/{user_id}", response_model=UserResponse)
async def patch_user(user_id: UUID, payload: UserUpdate, session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]):
    try:
        return update_user(session, target_id=user_id, actor=admin, changes=payload.model_dump(exclude_unset=True))
    except UserNotFoundError as error:
        raise HTTPException(status_code=404, detail="User not found") from error
    except AdminSafetyError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except UserManagementError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
