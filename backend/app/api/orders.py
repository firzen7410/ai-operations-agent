from typing import Annotated

from fastapi import APIRouter, Query, status

from backend.app.db import DbSession
from backend.app.models import Order
from backend.app.schemas.common import Page, PositiveId
from backend.app.schemas.order import OrderCreate, OrderFilters, OrderRead, OrderSummary
from backend.app.services import orders

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, session: DbSession) -> Order:
    return orders.create_order(session, data)


@router.get("", response_model=Page[OrderSummary])
def list_orders(filters: Annotated[OrderFilters, Query()], session: DbSession) -> Page[OrderSummary]:
    items, total = orders.list_orders(session, filters)
    return Page[OrderSummary](items=items, total=total, limit=filters.limit, offset=filters.offset)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: PositiveId, session: DbSession) -> Order:
    return orders.get_order(session, order_id)
