from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Product
from backend.app.schemas.product import ProductCreate, ProductFilters, ProductUpdate
from backend.app.services.errors import ConflictError, NotFoundError, is_constraint_error


def get_product(session: Session, product_id: int) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    return product


def list_products(session: Session, filters: ProductFilters) -> tuple[list[Product], int]:
    query = select(Product)
    if filters.name is not None:
        query = query.where(Product.name.icontains(filters.name, autoescape=True))
    if filters.sku is not None:
        query = query.where(Product.sku == filters.sku)
    if filters.min_stock is not None:
        query = query.where(Product.stock >= filters.min_stock)
    if filters.max_stock is not None:
        query = query.where(Product.stock <= filters.max_stock)
    if filters.stock_below is not None:
        query = query.where(Product.stock < filters.stock_below)

    total = session.scalar(query.with_only_columns(func.count(), maintain_column_froms=True))
    page = query.order_by(Product.id).offset(filters.offset).limit(filters.limit)
    return list(session.scalars(page)), total or 0


def save_product(session: Session, product: Product) -> Product:
    session.add(product)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if is_constraint_error(exc, sqlite_code="SQLITE_CONSTRAINT_UNIQUE", constraint="uq_products_sku"):
            raise ConflictError("SKU already exists") from exc
        raise
    return product


def create_product(session: Session, data: ProductCreate) -> Product:
    product = Product(
        sku=data.sku, name=data.name, price_cents=int(data.price * 100), stock=data.stock
    )
    return save_product(session, product)


def update_product(session: Session, product_id: int, changes: ProductUpdate) -> Product:
    product = get_product(session, product_id)
    if "sku" in changes:
        product.sku = changes["sku"]
    if "name" in changes:
        product.name = changes["name"]
    if "price" in changes:
        product.price_cents = int(changes["price"] * 100)
    if "stock" in changes:
        product.stock = changes["stock"]
    return save_product(session, product)


def delete_product(session: Session, product_id: int) -> None:
    session.delete(get_product(session, product_id))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if is_constraint_error(
            exc, sqlite_code="SQLITE_CONSTRAINT_FOREIGNKEY", constraint="fk_order_items_product_id"
        ):
            raise ConflictError("Product is referenced by an order") from exc
        raise
