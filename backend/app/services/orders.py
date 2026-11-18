from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from backend.app.models import Order, OrderItem, Product
from backend.app.schemas.order import OrderCreate, OrderFilters
from backend.app.services.errors import ConflictError, NotFoundError, is_constraint_error


def create_order(session: Session, data: OrderCreate) -> Order:
    ids = [item.product_id for item in data.items]
    products = {
        product.id: product
        for product in session.scalars(select(Product).where(Product.id.in_(ids)))
    }
    missing = [product_id for product_id in ids if product_id not in products]
    if missing:
        raise NotFoundError(f"Products not found: {', '.join(map(str, missing))}")

    order = Order(
        ordered_at=data.ordered_at.replace(tzinfo=None),
        status=data.status,
        items=[
            OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price_cents=products[item.product_id].price_cents,
            )
            for item in data.items
        ],
    )
    session.add(order)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if is_constraint_error(
            exc, sqlite_code="SQLITE_CONSTRAINT_FOREIGNKEY", constraint="fk_order_items_product_id"
        ):
            raise ConflictError("A product was removed while creating the order") from exc
        raise
    return order


def list_orders(session: Session, filters: OrderFilters) -> tuple[list[Order], int]:
    query = select(Order)
    if filters.start is not None:
        query = query.where(Order.ordered_at >= filters.start.replace(tzinfo=None))
    if filters.end is not None:
        query = query.where(Order.ordered_at < filters.end.replace(tzinfo=None))
    if filters.status is not None:
        query = query.where(Order.status == filters.status)

    total = session.scalar(query.with_only_columns(func.count(), maintain_column_froms=True))
    page = (
        query.order_by(Order.ordered_at.desc(), Order.id.desc())
        .offset(filters.offset)
        .limit(filters.limit)
    )
    return list(session.scalars(page)), total or 0


def get_order(session: Session, order_id: int) -> Order:
    order = session.get(Order, order_id, options=(selectinload(Order.items),))
    if order is None:
        raise NotFoundError("Order not found")
    return order
