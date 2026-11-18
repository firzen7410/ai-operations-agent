from decimal import Decimal

from sqlalchemy import BigInteger, Select, cast, func, select
from sqlalchemy.orm import Session

from backend.app.models import Order, OrderItem, OrderStatus, Product
from backend.app.schemas.sales import ProductSales, SalesFilters, SalesSummary


def product_sales_query(filters: SalesFilters) -> Select:
    units = func.sum(cast(OrderItem.quantity, BigInteger)).label("units_sold")
    revenue = func.sum(cast(OrderItem.unit_price_cents, BigInteger) * OrderItem.quantity).label(
        "revenue_cents"
    )
    query = (
        select(Product.id, Product.sku, Product.name, units, revenue)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.status == OrderStatus.COMPLETED,
            Order.ordered_at >= filters.start.replace(tzinfo=None),
            Order.ordered_at < filters.end.replace(tzinfo=None),
        )
        .group_by(Product.id, Product.sku, Product.name)
    )
    if filters.product_id is not None:
        query = query.where(Product.id == filters.product_id)
    return query


def read_product_sales(session: Session, query: Select) -> list[ProductSales]:
    return [
        ProductSales(
            product_id=product_id,
            sku=sku,
            name=name,
            units_sold=units_sold,
            revenue=Decimal(revenue_cents).scaleb(-2),
        )
        for product_id, sku, name, units_sold, revenue_cents in session.execute(query)
    ]


def get_sales_summary(session: Session, filters: SalesFilters) -> SalesSummary:
    items = read_product_sales(session, product_sales_query(filters).order_by(Product.id))
    return SalesSummary(
        start=filters.start,
        end=filters.end,
        units_sold=sum(item.units_sold for item in items),
        revenue=sum((item.revenue for item in items), Decimal("0.00")),
        items=items,
    )
