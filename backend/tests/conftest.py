import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import URL

from backend.app.db import build_engine
from backend.app.main import app
from backend.scripts.init_db import initialize_database


@pytest.fixture
def request_api(tmp_path, monkeypatch):
    database_url = URL.create("sqlite", database=str(tmp_path / "test.db")).render_as_string()
    monkeypatch.setenv("DATABASE_URL", database_url)
    engine = build_engine(database_url)
    try:
        initialize_database(engine)
    finally:
        engine.dispose()

    def send(method: str, path: str, **kwargs):
        async def request():
            async with app.router.lifespan_context(app):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    return await client.request(method, path, **kwargs)

        return asyncio.run(request())

    return send
