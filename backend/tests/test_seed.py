from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, selectinload

from backend.app.db import Base, build_engine
from backend.app.models import Order, Product
from backend.app.schemas.sales import SalesFilters
from backend.app.services.sales import get_sales_summary
from backend.scripts.seed import seed_data


def snapshot(session: Session) -> tuple:
    products = session.scalars(select(Product).order_by(Product.id))
    orders = session.scalars(select(Order).options(selectinload(Order.items)).order_by(Order.id))
    return (
        [(p.sku, p.name, p.price_cents, p.stock, p.created_at, p.updated_at) for p in products],
        [
            (
                order.ordered_at,
                order.created_at,
                order.status,
                [(item.product_id, item.quantity, item.unit_price_cents) for item in order.items],
            )
            for order in orders
        ],
        get_sales_summary(
            session, SalesFilters(start="2026-10-19T00:00:00Z", end="2026-11-18T00:00:00Z")
        ),
    )


def test_seed_is_reproducible_and_refuses_existing_data(tmp_path):
    snapshots = []
    for name in ("first.db", "second.db"):
        engine = build_engine(URL.create("sqlite", database=str(tmp_path / name)).render_as_string())
        try:
            Base.metadata.create_all(engine)
            with Session(engine) as session, session.begin():
                assert seed_data(session, seed=42, as_of=date(2026, 11, 18)) == (5, 50)

            with Session(engine) as session:
                baseline = snapshot(session)
                with pytest.raises(ValueError, match="empty database"):
                    seed_data(session, seed=42, as_of=date(2026, 11, 18))
                assert snapshot(session) == baseline
                snapshots.append(baseline)
        finally:
            engine.dispose()

    assert snapshots[0] == snapshots[1]
