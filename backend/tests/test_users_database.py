import asyncio
import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete

from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models import User, UserRole


pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL opt-in")
PREFIX = "users-api-"


def test_employee_management_end_to_end() -> None:
    admin_id, manager_id = uuid4(), uuid4()
    with SessionLocal() as session:
        session.add_all([
            User(id=admin_id,email=f"{PREFIX}admin@example.test",display_name="Admin",password_hash=hash_password("synthetic admin password"),role=UserRole.ADMIN,is_active=True),
            User(id=manager_id,email=f"{PREFIX}manager@example.test",display_name="Manager",password_hash=hash_password("synthetic manager password"),role=UserRole.MANAGER,is_active=True),
        ]); session.commit()
    async def flow():
        transport=httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport,base_url="http://test") as client:
            admin={"Authorization":f"Bearer {create_access_token(admin_id)}"}; manager={"Authorization":f"Bearer {create_access_token(manager_id)}"}
            assert (await client.get("/users")).status_code==401
            for method,path,body in [("GET","/users",None),("POST","/users",{"email":"x@example.test","display_name":"X","password":"valid password 123","role":"MANAGER"}),("PATCH",f"/users/{admin_id}",{"display_name":"X"})]:
                assert (await client.request(method,path,headers=manager,json=body)).status_code==403
            listing=await client.get("/users",headers=admin); assert listing.status_code==200 and "password_hash" not in listing.text
            created=await client.post("/users",headers=admin,json={"email":" Users-API-New@Example.TEST ","display_name":" New Manager ","password":"new synthetic password","role":"MANAGER"})
            assert created.status_code==201; body=created.json(); assert body["email"]==f"{PREFIX}new@example.test" and body["display_name"]=="New Manager" and body["is_active"] is True and "password" not in created.text
            new_id=body["id"]
            assert (await client.post("/users",headers=admin,json={"email":f"{PREFIX}new@example.test","display_name":"Dup","password":"new synthetic password","role":"ADMIN"})).status_code==409
            assert (await client.patch(f"/users/{admin_id}",headers=admin,json={"is_active":False})).status_code==409
            assert (await client.patch(f"/users/{admin_id}",headers=admin,json={"role":"MANAGER"})).status_code==409
            updated=await client.patch(f"/users/{new_id}",headers=admin,json={"display_name":" Updated ","role":"ADMIN"}); assert updated.status_code==200 and updated.json()["display_name"]=="Updated"
            assert (await client.patch(f"/users/{new_id}",headers=admin,json={"is_active":False})).status_code==200
            assert (await client.patch(f"/users/{new_id}",headers=admin,json={"is_active":True})).status_code==200
            assert (await client.patch(f"/users/{uuid4()}",headers=admin,json={"display_name":"Missing"})).status_code==404
            assert (await client.patch(f"/users/{new_id}",headers=admin,json={})).status_code==422
    try:
        asyncio.run(flow())
        with SessionLocal() as session:
            user=session.get(User, manager_id); user.is_active=False; session.commit()
        async def auth_check():
            transport=httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport,base_url="http://test") as client:
                token=create_access_token(manager_id)
                assert (await client.get("/auth/me",headers={"Authorization":f"Bearer {token}"})).status_code==401
                with SessionLocal() as session:
                    user=session.get(User,manager_id); user.is_active=True; session.commit()
                assert (await client.post("/auth/login",json={"email":f"{PREFIX}manager@example.test","password":"synthetic manager password"})).status_code==200
        asyncio.run(auth_check())
    finally:
        with SessionLocal() as session:
            session.execute(delete(User).where(User.email.like(f"{PREFIX}%"))); session.commit()
