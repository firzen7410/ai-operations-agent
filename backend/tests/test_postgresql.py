import asyncio
import json
import os
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema

from backend.app.api.agent import get_provider
from backend.app.db import Base, build_engine, get_session
from backend.app.main import app
from backend.app.services.llm import AssistantReply
from backend.scripts.init_db import migration_config

START = "2026-11-01T00:00:00Z"
END = "2026-12-01T00:00:00Z"


@pytest.fixture
def postgres_connection():
    database_url = os.environ.get("TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("Set TEST_POSTGRES_URL to run PostgreSQL integration tests.")
    if make_url(database_url).drivername != "postgresql+psycopg":
        pytest.fail("TEST_POSTGRES_URL must use the postgresql+psycopg dialect.")

    schema = f"test_operations_{uuid4().hex}"
    engine = build_engine(database_url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(CreateSchema(schema))
                connection.execute(
                    text("SELECT set_config('search_path', :schema, true)"), {"schema": schema}
                )
                command.upgrade(migration_config(connection), "head")
                yield connection
            finally:
                transaction.rollback()

            # Rollback must also remove the schema created for this test.
            assert not inspect(connection).has_schema(schema)
    finally:
        engine.dispose()


def test_postgresql_migrations_match_models(postgres_connection):
    config = migration_config(postgres_connection)
    actual = MigrationContext.configure(postgres_connection).get_current_revision()
    assert actual == ScriptDirectory.from_config(config).get_current_head()
    assert set(inspect(postgres_connection).get_table_names()) == {
        *Base.metadata.tables, "alembic_version",
    }
    command.check(config)


class FakeLlmProvider:
    def complete(self, messages, tools, *, timeout):
        count = sum(message["role"] == "tool" for message in messages)
        if count == 2:
            return AssistantReply(content="建議補貨 16 件。")
        name = "get_sales_summary" if count == 0 else "calculate_restock"
        return AssistantReply.model_validate({
            "tool_calls": [{
                "type": "function",
                "id": f"pg-call-{count}",
                "function": {
                    "name": name,
                    "arguments": json.dumps({"start": START, "end": END}),
                },
            }],
        })


def test_postgresql_api_and_agent_persistence(postgres_connection, monkeypatch):
    def session_override():
        with Session(
            postgres_connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ) as session:
            yield session

    monkeypatch.setitem(app.dependency_overrides, get_session, session_override)
    monkeypatch.setitem(app.dependency_overrides, get_provider, FakeLlmProvider)

    async def exercise_api():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            product = {"sku": "PG-TEST", "name": "測試商品", "price": "9.90", "stock": 4}
            created = await client.post("/products", json=product)
            assert created.status_code == 201
            product_id = created.json()["id"]
            assert (await client.post("/products", json=product)).status_code == 409

            order = {
                "status": "completed",
                "ordered_at": START,
                "items": [{"product_id": product_id, "quantity": 31}],
            }
            created_order = await client.post("/orders", json=order)
            assert created_order.status_code == 201
            detail = await client.get(f"/orders/{created_order.json()['id']}")
            assert detail.json()["items"][0]["unit_price"] == "9.90"
            assert (await client.delete(f"/products/{product_id}")).status_code == 409

            summary = await client.get("/sales/summary", params={"start": START, "end": END})
            assert summary.json()["units_sold"] == 31
            assert summary.json()["revenue"] == "306.90"

            requested = await client.post("/agent/runs", json={"message": "請計算補貨"})
            assert requested.status_code == 201
            run = requested.json()
            assert run["status"] == "completed", run["error_message"]
            sales, restock = run["tool_executions"]
            assert sales["result"]["units_sold"] == 31
            assert isinstance(sales["result"]["units_sold"], int)
            assert restock["result"]["items"][0]["recommended_quantity"] == 16
            assert isinstance(restock["result"]["items"][0]["recommended_quantity"], int)
            assert (await client.get(f"/agent/runs/{run['id']}")).json() == run

    asyncio.run(exercise_api())
