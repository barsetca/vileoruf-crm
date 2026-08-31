from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from backend.app.core.config import get_security_settings
from backend.app.core.security import (
    InvalidTokenError,
    TokenErrorReason,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password,
    verify_password,
)


TEST_JWT_SECRET = "focused-test-secret-that-is-not-used-outside-tests"


@pytest.fixture(autouse=True)
def configure_security(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    get_security_settings.cache_clear()
    yield
    get_security_settings.cache_clear()


def test_password_hashing_and_verification() -> None:
    password = "correct horse battery staple"
    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != password
    assert first_hash.startswith("$argon2id$")
    assert verify_password(password, first_hash)
    assert not verify_password("incorrect password", first_hash)
    assert first_hash != second_hash


@pytest.mark.parametrize("length", [12, 128])
def test_password_policy_accepts_boundaries(length: int) -> None:
    password = "p" * length

    validate_password(password)
    assert hash_password(password).startswith("$argon2id$")


@pytest.mark.parametrize("length", [11, 129])
def test_password_policy_rejects_outside_boundaries(length: int) -> None:
    with pytest.raises(ValueError, match="Password length"):
        validate_password("p" * length)


def test_malformed_password_hash_is_handled_safely() -> None:
    assert not verify_password("valid length password", "not-an-argon2-hash")


def test_access_token_round_trip_and_claims() -> None:
    user_id = uuid4()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    token = create_access_token(user_id, now=now)
    claims = decode_token(token, TokenType.ACCESS)
    raw_claims = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])

    assert claims.subject == str(user_id)
    assert claims.token_type is TokenType.ACCESS
    assert claims.issued_at == now
    assert claims.expires_at - claims.issued_at == timedelta(minutes=30)
    assert {"sub", "type", "iat", "exp"} <= raw_claims.keys()
    assert "role" not in raw_claims
    assert "email" not in raw_claims


def test_refresh_token_round_trip_and_claims() -> None:
    user_id = uuid4()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    token = create_refresh_token(user_id, now=now)
    claims = decode_token(token, TokenType.REFRESH)

    assert claims.subject == str(user_id)
    assert claims.token_type is TokenType.REFRESH
    assert claims.issued_at == now
    assert claims.expires_at - claims.issued_at == timedelta(days=7)


def test_wrong_expected_token_type_is_rejected() -> None:
    token = create_refresh_token(uuid4())

    with pytest.raises(InvalidTokenError) as error:
        decode_token(token, TokenType.ACCESS)

    assert error.value.reason is TokenErrorReason.WRONG_TYPE


def test_invalid_signature_is_rejected() -> None:
    token = create_access_token(uuid4())
    header, payload, signature = token.split(".")
    replacement = "A" if signature[0] != "A" else "B"
    tampered = ".".join((header, payload, replacement + signature[1:]))

    with pytest.raises(InvalidTokenError) as error:
        decode_token(tampered, TokenType.ACCESS)

    assert error.value.reason is TokenErrorReason.INVALID_SIGNATURE


def test_malformed_token_is_rejected() -> None:
    with pytest.raises(InvalidTokenError) as error:
        decode_token("not-a-jwt", TokenType.ACCESS)

    assert error.value.reason is TokenErrorReason.MALFORMED


def test_expired_token_is_rejected() -> None:
    old_time = datetime.now(timezone.utc) - timedelta(minutes=31)
    token = create_access_token(uuid4(), now=old_time)

    with pytest.raises(InvalidTokenError) as error:
        decode_token(token, TokenType.ACCESS)

    assert error.value.reason is TokenErrorReason.EXPIRED
