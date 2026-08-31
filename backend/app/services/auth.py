from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.identity import normalize_email
from backend.app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from backend.app.models import User


class AuthenticationError(ValueError):
    """Expected authentication failure safe to normalize at the HTTP boundary."""


def authenticate_user(session: Session, *, email: str, password: str) -> User:
    user = session.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError
    if not user.is_active:
        raise AuthenticationError
    return user


def issue_login_tokens(user: User) -> tuple[str, str]:
    return create_access_token(user.id), create_refresh_token(user.id)


def resolve_user_from_token(
    session: Session,
    *,
    token: str,
    expected_type: TokenType,
) -> User:
    try:
        claims = decode_token(token, expected_type)
        user_id = UUID(claims.subject)
    except (InvalidTokenError, ValueError, AttributeError) as error:
        raise AuthenticationError from error

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError
    return user


def refresh_access_token(session: Session, *, refresh_token: str) -> tuple[str, User]:
    user = resolve_user_from_token(
        session,
        token=refresh_token,
        expected_type=TokenType.REFRESH,
    )
    return create_access_token(user.id), user
