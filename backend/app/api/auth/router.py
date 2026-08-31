from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.core.config import get_security_settings
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.auth import (
    AccessTokenResponse,
    AuthUserResponse,
    LoginRequest,
    LoginResponse,
)
from backend.app.services.auth import (
    AuthenticationError,
    authenticate_user,
    issue_login_tokens,
    refresh_access_token,
)


REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/auth"

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    try:
        user = authenticate_user(
            session,
            email=request.email,
            password=request.password,
        )
    except AuthenticationError as error:
        raise _invalid_login() from error

    access_token, refresh_token = issue_login_tokens(user)
    _set_refresh_cookie(response, refresh_token)
    return LoginResponse(access_token=access_token, user=user)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    session: Annotated[Session, Depends(get_db)],
    refresh_token: Annotated[
        str | None,
        Cookie(alias=REFRESH_COOKIE_NAME),
    ] = None,
) -> AccessTokenResponse:
    if not refresh_token:
        raise _invalid_refresh()
    try:
        access_token, user = refresh_access_token(
            session,
            refresh_token=refresh_token,
        )
    except AuthenticationError as error:
        raise _invalid_refresh() from error
    return AccessTokenResponse(access_token=access_token, user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    settings = get_security_settings()
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.get("/me", response_model=AuthUserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_security_settings()
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )


def _invalid_login() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _invalid_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
