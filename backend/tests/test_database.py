import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db import Base, build_engine
from backend.app.models import Order, OrderItem, OrderStatus, Product, utc_now


@pytest.fixture
def engine(tmp_path):
    url = URL.create("sqlite", database=str(tmp_path / "constraints.db"))
    engine = build_engine(url.render_as_string())
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()


@pytest.mark.parametrize("price,stock", [(-1, 1), (100, -1)])
def test_product_checks_are_enforced(engine: Engine, price: int, stock: int):
    with Session(engine) as session, pytest.raises(IntegrityError, match="CHECK"):
        with session.begin():
            session.add(Product(sku="SKU", name="Test", price_cents=price, stock=stock))


def test_order_rolls_back_when_item_violates_foreign_key(engine: Engine):
    with Session(engine) as session:
        with pytest.raises(IntegrityError, match="FOREIGN KEY"):
            with session.begin():
                session.add(
                    Order(
                        ordered_at=utc_now(),
                        status=OrderStatus.COMPLETED,
                        items=[OrderItem(product_id=999, quantity=1, unit_price_cents=100)],
                    )
                )

        assert session.scalar(select(func.count()).select_from(Order)) == 0
        assert session.scalar(select(func.count()).select_from(OrderItem)) == 0
