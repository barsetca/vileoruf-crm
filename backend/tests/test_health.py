import asyncio

import httpx

from backend.app.main import app


def test_health() -> None:
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(
                "/health",
                headers={"Origin": "http://localhost:5173"},
            )

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
