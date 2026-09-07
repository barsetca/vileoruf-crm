import asyncio
from types import SimpleNamespace

import httpx
from fastapi import HTTPException

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import User, UserRole
import backend.app.api.integrations.router as router_module


def _request():
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.get("/settings/integrations/telegram/availability")
    return asyncio.run(send())


def test_employee_telegram_availability_is_narrow_and_authenticated(monkeypatch):
    admin=User(email="admin@test",password_hash="x",display_name="Admin",role=UserRole.ADMIN,is_active=True)
    manager=User(email="manager@test",password_hash="x",display_name="Manager",role=UserRole.MANAGER,is_active=True)
    app.dependency_overrides[get_db]=lambda: object()
    try:
        for user, available in ((admin, True),(manager, False)):
            app.dependency_overrides[get_current_user]=lambda user=user: user
            monkeypatch.setattr(router_module,"telegram_operational_available",lambda session, available=available: available)
            response=_request()
            assert response.status_code==200 and response.json()=={"provider":"TELEGRAM","available":available}
        async def unauthenticated(): raise HTTPException(401,"Authentication required")
        app.dependency_overrides[get_current_user]=unauthenticated
        assert _request().status_code==401
    finally: app.dependency_overrides.clear()
