import asyncio
import os
from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete

from backend.app.core.security import hash_password
from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models import User, UserRole


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)

SYNTHETIC_EMAIL = "auth-flow-admin@example.test"
SYNTHETIC_PASSWORD = "synthetic auth flow password"


@pytest.fixture(autouse=True)
def clean_synthetic_user() -> Iterator[None]:
    with SessionLocal() as session:
        session.execute(delete(User).where(User.email == SYNTHETIC_EMAIL))
        session.commit()
    yield
    with SessionLocal() as session:
        session.execute(delete(User).where(User.email == SYNTHETIC_EMAIL))
        session.commit()


def test_real_postgresql_auth_flow_and_deactivation() -> None:
    user_id = uuid4()
    with SessionLocal() as session:
        session.add(
            User(
                id=user_id,
                email=SYNTHETIC_EMAIL,
                password_hash=hash_password(SYNTHETIC_PASSWORD),
                display_name="Synthetic Auth Admin",
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
        session.commit()

    async def flow() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            login = await client.post(
                "/auth/login",
                json={
                    "email": " Auth-Flow-Admin@Example.TEST ",
                    "password": SYNTHETIC_PASSWORD,
                },
            )
            assert login.status_code == 200
            access_token = login.json()["access_token"]
            assert "refresh_token" in client.cookies

            me = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert me.status_code == 200
            assert me.json()["id"] == str(user_id)

            refresh = await client.post("/auth/refresh")
            assert refresh.status_code == 200
            refreshed_access = refresh.json()["access_token"]

            with SessionLocal() as session:
                user = session.get(User, user_id)
                assert user is not None
                user.is_active = False
                session.commit()

            inactive_me = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {refreshed_access}"},
            )
            assert inactive_me.status_code == 401
            assert (await client.post("/auth/refresh")).status_code == 401

            logout = await client.post("/auth/logout")
            assert logout.status_code == 204
            assert "Max-Age=0" in logout.headers["set-cookie"]

    asyncio.run(flow())
