import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest

from backend.app.core.config import get_security_settings
from backend.app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
)
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import User, UserRole


TEST_JWT_SECRET = "auth-http-test-secret-that-is-not-used-outside-tests"
VALID_PASSWORD = "synthetic auth password"


class FakeSession:
    def __init__(self, user: User | None) -> None:
        self.user = user

    def scalar(self, statement):
        return self.user

    def get(self, model, user_id):
        if self.user is not None and self.user.id == user_id:
            return self.user
        return None


@pytest.fixture(autouse=True)
def configure_auth(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    get_security_settings.cache_clear()
    yield
    app.dependency_overrides.clear()
    get_security_settings.cache_clear()


@pytest.fixture
def active_user() -> User:
    return User(
        id=uuid4(),
        email="admin@example.com",
        password_hash=hash_password(VALID_PASSWORD),
        display_name="Studio Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )


def request(
    method: str,
    path: str,
    *,
    user: User | None,
    headers: dict[str, str] | None = None,
    json: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
) -> httpx.Response:
    async def override_db() -> FakeSession:
        return FakeSession(user)

    app.dependency_overrides[get_db] = override_db

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            if cookies:
                client.cookies.update(cookies)
            return await client.request(
                method,
                path,
                headers=headers,
                json=json,
            )

    return asyncio.run(send())


def test_login_normalizes_email_and_sets_safe_tokens(active_user: User) -> None:
    response = request(
        "POST",
        "/auth/login",
        user=active_user,
        json={"email": " Admin@Example.COM ", "password": VALID_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": str(active_user.id),
        "email": active_user.email,
        "display_name": active_user.display_name,
        "role": "ADMIN",
        "is_active": True,
    }
    assert "refresh_token" not in body
    assert "password_hash" not in str(body)
    assert decode_token(body["access_token"], TokenType.ACCESS).subject == str(
        active_user.id
    )
    refresh_token = response.cookies["refresh_token"]
    assert decode_token(refresh_token, TokenType.REFRESH).subject == str(active_user.id)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/auth" in cookie
    assert "Max-Age=604800" in cookie
    assert "Secure" not in cookie


@pytest.mark.parametrize(
    ("user_present", "password"),
    [(True, "incorrect auth password"), (False, VALID_PASSWORD)],
)
def test_login_failures_are_generic(
    active_user: User,
    user_present: bool,
    password: str,
) -> None:
    response = request(
        "POST",
        "/auth/login",
        user=active_user if user_present else None,
        json={"email": "missing@example.test", "password": password},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}
    assert "refresh_token" not in response.headers.get("set-cookie", "")


def test_inactive_user_cannot_login(active_user: User) -> None:
    active_user.is_active = False
    response = request(
        "POST",
        "/auth/login",
        user=active_user,
        json={"email": active_user.email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}
    assert "set-cookie" not in response.headers


def test_refresh_returns_new_access_for_current_active_user(active_user: User) -> None:
    refresh = create_refresh_token(active_user.id)
    response = request(
        "POST",
        "/auth/refresh",
        user=active_user,
        cookies={"refresh_token": refresh},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["id"] == str(active_user.id)
    assert decode_token(body["access_token"], TokenType.ACCESS).subject == str(
        active_user.id
    )
    assert "refresh_token" not in body


@pytest.mark.parametrize("token_kind", ["missing", "invalid", "access", "expired"])
def test_refresh_rejects_invalid_cookie_states(
    active_user: User,
    token_kind: str,
) -> None:
    cookies = None
    if token_kind == "invalid":
        cookies = {"refresh_token": "not-a-jwt"}
    elif token_kind == "access":
        cookies = {"refresh_token": create_access_token(active_user.id)}
    elif token_kind == "expired":
        cookies = {
            "refresh_token": create_refresh_token(
                active_user.id,
                now=datetime.now(timezone.utc) - timedelta(days=8),
            )
        }
    response = request(
        "POST", "/auth/refresh", user=active_user, cookies=cookies
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired refresh token"}


def test_refresh_rechecks_user_active_state(active_user: User) -> None:
    token = create_refresh_token(active_user.id)
    active_user.is_active = False
    response = request(
        "POST",
        "/auth/refresh",
        user=active_user,
        cookies={"refresh_token": token},
    )
    assert response.status_code == 401


def test_logout_is_idempotent_and_clears_matching_cookie_attributes() -> None:
    for cookies in ({"refresh_token": "token"}, None):
        response = request("POST", "/auth/logout", user=None, cookies=cookies)
        assert response.status_code == 204
        cookie = response.headers["set-cookie"]
        assert "refresh_token=" in cookie
        assert "Max-Age=0" in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie
        assert "Path=/auth" in cookie


def test_me_returns_safe_current_database_user(active_user: User) -> None:
    token = create_access_token(active_user.id)
    response = request(
        "GET",
        "/auth/me",
        user=active_user,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"
    assert "password_hash" not in response.text


@pytest.mark.parametrize(
    "authorization",
    [None, "Basic abc", "Bearer not-a-jwt"],
)
def test_me_rejects_missing_wrong_scheme_and_malformed_bearer(
    active_user: User,
    authorization: str | None,
) -> None:
    headers = {"Authorization": authorization} if authorization else None
    response = request("GET", "/auth/me", user=active_user, headers=headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("kind", ["expired", "refresh", "unknown", "malformed-sub"])
def test_me_rejects_invalid_or_unresolvable_access_identity(
    active_user: User,
    kind: str,
) -> None:
    user: User | None = active_user
    if kind == "expired":
        token = create_access_token(
            active_user.id,
            now=datetime.now(timezone.utc) - timedelta(minutes=31),
        )
    elif kind == "refresh":
        token = create_refresh_token(active_user.id)
    elif kind == "unknown":
        token = create_access_token(uuid4())
    else:
        token = create_access_token("not-a-uuid")
    response = request(
        "GET",
        "/auth/me",
        user=user,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_me_rechecks_user_active_state(active_user: User) -> None:
    token = create_access_token(active_user.id)
    active_user.is_active = False
    response = request(
        "GET",
        "/auth/me",
        user=active_user,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_secure_cookie_is_controlled_by_environment(
    active_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    get_security_settings.cache_clear()
    response = request(
        "POST",
        "/auth/login",
        user=active_user,
        json={"email": active_user.email, "password": VALID_PASSWORD},
    )
    assert "Secure" in response.headers["set-cookie"]


def test_credentialed_cors_is_restricted() -> None:
    allowed = request(
        "OPTIONS",
        "/auth/login",
        user=None,
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,idempotency-key",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert "idempotency-key" in allowed.headers["access-control-allow-headers"].lower()

    denied = request(
        "OPTIONS",
        "/auth/login",
        user=None,
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_openapi_contains_only_intended_auth_paths() -> None:
    paths = app.openapi()["paths"]
    assert set(path for path in paths if path.startswith("/auth")) == {
        "/auth/login",
        "/auth/refresh",
        "/auth/logout",
        "/auth/me",
    }
    assert set(paths["/auth/login"]) == {"post"}
    assert set(paths["/auth/refresh"]) == {"post"}
    assert set(paths["/auth/logout"]) == {"post"}
    assert set(paths["/auth/me"]) == {"get"}
    assert "/register" not in paths
    assert set(paths["/users"]) == {"get", "post"}
    assert set(paths["/users/{user_id}"]) == {"patch"}
    assert "delete" not in paths["/users/{user_id}"]
