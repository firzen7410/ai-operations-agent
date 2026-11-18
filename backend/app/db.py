from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str) -> Engine:
    if make_url(database_url).get_backend_name() != "sqlite":
        return create_engine(database_url)

    engine = create_engine(database_url, connect_args={"autocommit": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        # SQLite ignores this PRAGMA inside a transaction.
        connection.autocommit = True
        try:
            connection.execute("PRAGMA foreign_keys = ON").close()
        finally:
            connection.autocommit = False

    return engine


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.db_engine, expire_on_commit=False) as session:
        yield session


DbSession = Annotated[Session, Depends(get_session)]
