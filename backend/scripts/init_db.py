from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.engine import Connection, Engine

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.db import build_engine

CORE_TABLES = frozenset({"products", "orders", "order_items"})
LEGACY_REVISIONS = {
    CORE_TABLES: "0001_operations",
    CORE_TABLES | {"agent_runs", "tool_executions"}: "0002_agent_audit",
}


class LegacySchemaError(Exception):
    pass


def migration_config(connection: Connection) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


def table_schema(connection: Connection, table: str) -> tuple:
    inspector = inspect(connection)
    columns = [
        (column["name"], str(column["type"]), column["nullable"], column["default"])
        for column in inspector.get_columns(table)
    ]
    return (
        columns,
        inspector.get_pk_constraint(table),
        sorted(inspector.get_foreign_keys(table), key=repr),
        sorted(inspector.get_unique_constraints(table), key=repr),
        sorted(inspector.get_check_constraints(table), key=repr),
        sorted(inspector.get_indexes(table), key=repr),
    )


def verified_legacy_revision(connection: Connection, tables: frozenset[str]) -> str:
    revision = LEGACY_REVISIONS.get(tables)
    if connection.dialect.name != "sqlite" or revision is None:
        raise LegacySchemaError("Unrecognized unversioned database schema. No changes were made.")

    # Compare with the historical revision, independent of future ORM model changes.
    reference = build_engine("sqlite:///:memory:")
    try:
        with reference.begin() as expected:
            command.upgrade(migration_config(expected), revision)
            for table in sorted(tables):
                if table_schema(connection, table) != table_schema(expected, table):
                    raise LegacySchemaError(
                        f"Legacy table {table!r} differs from {revision}. No changes were made."
                    )
    finally:
        reference.dispose()
    return revision


def initialize_database(engine: Engine) -> str:
    with engine.begin() as connection:
        config = migration_config(connection)
        migration = MigrationContext.configure(connection)
        tables = frozenset(inspect(connection).get_table_names()) - {"alembic_version"}
        if tables and not migration.get_current_heads():
            revision = verified_legacy_revision(connection, tables)
            command.stamp(config, revision)

        command.upgrade(config, "head")
        current = MigrationContext.configure(connection).get_current_revision()
        if current is None:
            raise RuntimeError("Alembic did not record a database revision.")
        return current


def main() -> None:
    engine = build_engine(Settings().database_url)
    try:
        revision = initialize_database(engine)
    except LegacySchemaError as exc:
        raise SystemExit(str(exc)) from None
    finally:
        engine.dispose()
    print(f"Database {engine.url.database!r} is at Alembic revision {revision}.")


if __name__ == "__main__":
    main()
