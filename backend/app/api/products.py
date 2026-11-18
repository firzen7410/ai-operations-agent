from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from backend.app.db import DbSession
from backend.app.models import Product
from backend.app.schemas.common import Page, PositiveId
from backend.app.schemas.product import ProductCreate, ProductFilters, ProductRead, ProductUpdate
from backend.app.services import products

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, session: DbSession) -> Product:
    return products.create_product(session, data)


@router.get("", response_model=Page[ProductRead])
def list_products(filters: Annotated[ProductFilters, Query()], session: DbSession) -> Page[ProductRead]:
    items, total = products.list_products(session, filters)
    return Page[ProductRead](items=items, total=total, limit=filters.limit, offset=filters.offset)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: PositiveId, session: DbSession) -> Product:
    return products.get_product(session, product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(product_id: PositiveId, changes: ProductUpdate, session: DbSession) -> Product:
    return products.update_product(session, product_id, changes)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: PositiveId, session: DbSession) -> Response:
    products.delete_product(session, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
