from alembic import context
from sqlalchemy.engine import Connection

from backend.app import models  # Register application tables for autogenerate.
from backend.app.config import Settings
from backend.app.db import Base, build_engine


def run_migrations(connection: Connection) -> None:
    sqlite = connection.dialect.name == "sqlite"
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        render_as_batch=sqlite,
        transactional_ddl=True if sqlite else None,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        run_migrations(connection)
        return

    engine = build_engine(Settings().database_url)
    try:
        with engine.connect() as connection:
            run_migrations(connection)
    finally:
        engine.dispose()


def run_offline() -> None:
    context.configure(url=Settings().database_url, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
