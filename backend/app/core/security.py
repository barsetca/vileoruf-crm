from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidTokenError as PyJwtInvalidTokenError,
)

from backend.app.core.config import get_security_settings


MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

password_hasher = PasswordHasher()


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenErrorReason(str, Enum):
    EXPIRED = "expired"
    INVALID_SIGNATURE = "invalid_signature"
    MALFORMED = "malformed"
    WRONG_TYPE = "wrong_type"


class InvalidTokenError(ValueError):
    def __init__(self, reason: TokenErrorReason) -> None:
        self.reason = reason
        super().__init__(f"Invalid token: {reason.value}")


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    token_type: TokenType
    issued_at: datetime
    expires_at: datetime


def validate_password(password: str) -> None:
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password length must be between {MIN_PASSWORD_LENGTH} "
            f"and {MAX_PASSWORD_LENGTH} characters"
        )


def hash_password(password: str) -> str:
    validate_password(password)
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False


def create_access_token(
    user_id: UUID | str,
    *,
    now: datetime | None = None,
) -> str:
    settings = get_security_settings()
    return _create_token(
        user_id,
        TokenType.ACCESS,
        timedelta(minutes=settings.access_token_expire_minutes),
        now=now,
    )


def create_refresh_token(
    user_id: UUID | str,
    *,
    now: datetime | None = None,
) -> str:
    settings = get_security_settings()
    return _create_token(
        user_id,
        TokenType.REFRESH,
        timedelta(days=settings.refresh_token_expire_days),
        now=now,
    )


def decode_token(token: str, expected_type: TokenType) -> TokenClaims:
    settings = get_security_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "type", "iat", "exp"]},
        )
    except ExpiredSignatureError as error:
        raise InvalidTokenError(TokenErrorReason.EXPIRED) from error
    except InvalidSignatureError as error:
        raise InvalidTokenError(TokenErrorReason.INVALID_SIGNATURE) from error
    except PyJwtInvalidTokenError as error:
        raise InvalidTokenError(TokenErrorReason.MALFORMED) from error

    try:
        token_type = TokenType(payload["type"])
        issued_at = datetime.fromtimestamp(payload["iat"], timezone.utc)
        expires_at = datetime.fromtimestamp(payload["exp"], timezone.utc)
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise InvalidTokenError(TokenErrorReason.MALFORMED) from error

    if token_type is not expected_type:
        raise InvalidTokenError(TokenErrorReason.WRONG_TYPE)

    return TokenClaims(
        subject=payload["sub"],
        token_type=token_type,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def _create_token(
    user_id: UUID | str,
    token_type: TokenType,
    lifetime: timedelta,
    *,
    now: datetime | None,
) -> str:
    settings = get_security_settings()
    issued_at = now or datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type.value,
        "iat": issued_at,
        "exp": issued_at + lifetime,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
