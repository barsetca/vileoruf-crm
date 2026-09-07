import asyncio

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import EmailDraftState, IntegrationConnectionStatus, IntegrationProvider, User, UserRole
from backend.app.services.integrations_adapters import ProviderErrorCode, RetryClass
from backend.app.services.integrations_crypto import IntegrationTokenError, decrypt_token_payload, encrypt_token_payload
import backend.app.services.integrations_crypto as crypto


@pytest.fixture(autouse=True)
def overrides():
    async def db(): return object()
    async def reject(): raise HTTPException(401, "Authentication required")
    app.dependency_overrides[get_db] = db; app.dependency_overrides[get_current_user] = reject
    yield
    app.dependency_overrides.clear()

def request(path):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:return await client.get(path)
    return asyncio.run(send())

def test_integration_contract_enums_and_sent_draft_foundation():
    assert {x.value for x in IntegrationProvider} == {"GMAIL","TELEGRAM","GOOGLE_CALENDAR","WHATSAPP"}
    assert {x.value for x in IntegrationConnectionStatus} == {"DISCONNECTED","CONNECTING","CONNECTED","ERROR"}
    assert {x.value for x in EmailDraftState} == {"DRAFT","SENT"}
    assert ProviderErrorCode.AUTH_REQUIRED.value == "AUTH_REQUIRED" and RetryClass.UNCERTAIN.value == "UNCERTAIN"

def test_crypto_round_trip_and_missing_configuration(monkeypatch):
    key=Fernet.generate_key().decode()
    class Settings: integration_token_encryption_key=type("S",(),{"get_secret_value":lambda self:key})()
    monkeypatch.setattr(crypto,"get_integration_security_settings",lambda:Settings())
    ciphertext=encrypt_token_payload(b"synthetic-token")
    assert ciphertext != "synthetic-token" and decrypt_token_payload(ciphertext)==b"synthetic-token"
    class Missing: integration_token_encryption_key=None
    monkeypatch.setattr(crypto,"get_integration_security_settings",lambda:Missing())
    with pytest.raises(IntegrationTokenError): encrypt_token_payload(b"x")

def test_integration_settings_requires_authentication_and_is_admin_wired():
    assert request("/settings/integrations").status_code == 401
    wired={(route.path,method) for route in app.routes for method in getattr(route,"methods",set()) if any(dep.call.__name__=="require_admin" for dep in getattr(getattr(route,"dependant",None),"dependencies",[]))}
    assert ("/settings/integrations","GET") in wired
    manager=User(email="m@example.test",password_hash="x",display_name="m",role=UserRole.MANAGER,is_active=True)
    from backend.app.api.dependencies import require_admin
    with pytest.raises(HTTPException) as error: require_admin(manager)
    assert error.value.status_code == 403
