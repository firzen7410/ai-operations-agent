import asyncio

from httpx import ASGITransport, AsyncClient

from backend.app.main import app


def test_health_returns_ok() -> None:
    async def request_health() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    asyncio.run(request_health())
