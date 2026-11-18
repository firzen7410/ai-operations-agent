import argparse
from datetime import UTC, date, datetime, timedelta
from random import Random

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.db import build_engine
from backend.app.models import Order, OrderItem, OrderStatus, Product


def seed_data(session: Session, *, seed: int, as_of: date) -> tuple[int, int]:
    if session.scalar(select(exists().where(Product.id.is_not(None)))) or session.scalar(
        select(exists().where(Order.id.is_not(None)))
    ):
        raise ValueError("Seed data requires an empty database")

    rng = Random(seed)
    anchor = datetime(as_of.year, as_of.month, as_of.day)
    catalog = [
        ("DEMO-001", "Coffee Filters", 850, 4),
        ("DEMO-002", "Glass Server", 1690, 8),
        ("DEMO-003", "Dripper", 1290, 22),
        ("DEMO-004", "Digital Scale", 2490, 36),
        ("DEMO-005", "Travel Mug", 1990, 14),
    ]
    products = [
        Product(
            sku=sku, name=name, price_cents=price, stock=stock,
            created_at=anchor - timedelta(days=60), updated_at=anchor,
        )
        for sku, name, price, stock in catalog
    ]
    session.add_all(products)
    session.flush()

    statuses = [OrderStatus.COMPLETED] * 8 + [OrderStatus.PENDING, OrderStatus.CANCELLED]
    orders = []
    for status in statuses * 5:
        ordered_at = anchor - timedelta(days=rng.randint(1, 45), hours=rng.randrange(24))
        selected = rng.sample(products, rng.randint(1, 3))
        orders.append(
            Order(
                ordered_at=ordered_at,
                created_at=ordered_at,
                status=status,
                items=[
                    OrderItem(
                        product_id=product.id,
                        quantity=rng.randint(1, 6),
                        unit_price_cents=product.price_cents,
                    )
                    for product in selected
                ],
            )
        )
    session.add_all(orders)
    return len(products), len(orders)


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate an empty development database.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(UTC).date())
    args = parser.parse_args()
    engine = build_engine(Settings().database_url)
    try:
        with Session(engine) as session, session.begin():
            counts = seed_data(session, seed=args.seed, as_of=args.as_of)
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")
    finally:
        engine.dispose()
    print(f"Created {counts[0]} products and {counts[1]} orders (as of {args.as_of} UTC).")


if __name__ == "__main__":
    main()
