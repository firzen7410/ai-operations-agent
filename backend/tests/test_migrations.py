from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from backend.app.config import PROJECT_ROOT
from backend.app.db import Base, build_engine
from backend.app.models import AgentRun, Order, OrderItem, OrderStatus, Product, ToolExecution, utc_now
from backend.scripts.init_db import CORE_TABLES, LegacySchemaError, initialize_database

HEAD = "0002_agent_audit"
RUN_ID = UUID("a0a872de-3046-4259-81a8-47ea6eec9701")


@pytest.fixture
def migration_db(tmp_path, monkeypatch):
    url = URL.create("sqlite", database=str(tmp_path / "migration.db")).render_as_string()
    monkeypatch.setenv("DATABASE_URL", url)
    engine = build_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


def test_migrate_empty_database(migration_db):
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    assert set(inspect(migration_db).get_table_names()) == {
        *Base.metadata.tables, "alembic_version",
    }
    assert initialize_database(migration_db) == HEAD
    command.check(config)


@pytest.mark.parametrize("has_agent_tables", [False, True])
def test_adopt_legacy_database_and_preserve_data(migration_db, has_agent_tables):
    tables = [
        table for table in Base.metadata.sorted_tables
        if has_agent_tables or table.name in CORE_TABLES
    ]
    Base.metadata.create_all(migration_db, tables=tables)
    with Session(migration_db) as session, session.begin():
        product = Product(id=1, sku="LEGACY", name="舊商品", price_cents=990, stock=8)
        session.add(product)
        session.flush()
        session.add(Order(
            id=1, status=OrderStatus.COMPLETED, ordered_at=utc_now(),
            items=[OrderItem(product_id=1, quantity=3, unit_price_cents=990)],
        ))
        if has_agent_tables:
            session.add(AgentRun(
                id=RUN_ID, user_message="查庫存", status="completed", response="已查詢",
                tool_executions=[ToolExecution(
                    tool_name="get_low_stock_products", arguments={"threshold": 10},
                    result={"total": 1}, status="success",
                )],
            ))

    assert initialize_database(migration_db) == HEAD
    assert initialize_database(migration_db) == HEAD

    with Session(migration_db) as session:
        assert session.get(Product, 1).sku == "LEGACY"
        assert session.get(Order, 1).items[0].quantity == 3
        assert session.get(Order, 1).items[0].unit_price_cents == 990
        run = session.get(AgentRun, RUN_ID)
        if has_agent_tables:
            assert run.response == "已查詢"
            assert run.tool_executions[0].result == {"total": 1}
        else:
            assert run is None
            assert session.scalar(select(ToolExecution)) is None


def test_reject_drifted_legacy_schema_without_stamping(migration_db):
    tables = [Base.metadata.tables[name] for name in CORE_TABLES]
    Base.metadata.create_all(migration_db, tables=tables)
    with migration_db.begin() as conn:
        conn.exec_driver_sql("DROP INDEX ix_products_stock")

    with pytest.raises(LegacySchemaError, match="products.*differs"):
        initialize_database(migration_db)

    assert set(inspect(migration_db).get_table_names()) == CORE_TABLES


def test_reject_unrecognized_schema_without_migrating(migration_db):
    with migration_db.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")

    with pytest.raises(LegacySchemaError, match="Unrecognized"):
        initialize_database(migration_db)

    assert inspect(migration_db).get_table_names() == ["unrelated"]


def test_failed_legacy_upgrade_rolls_back_tables_and_revision(migration_db, monkeypatch):
    tables = [Base.metadata.tables[name] for name in CORE_TABLES]
    Base.metadata.create_all(migration_db, tables=tables)
    upgrade = command.upgrade

    def fail_after_upgrade(config, revision):
        upgrade(config, revision)
        if config.attributes["connection"].engine is migration_db:
            raise RuntimeError("Simulated migration failure")

    monkeypatch.setattr(command, "upgrade", fail_after_upgrade)

    with pytest.raises(RuntimeError, match="Simulated migration failure"):
        initialize_database(migration_db)

    assert set(inspect(migration_db).get_table_names()) == CORE_TABLES
