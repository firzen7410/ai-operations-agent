from decimal import Decimal
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.models import OrderStatus
from backend.app.schemas.common import (
    InputTimestamp,
    Pagination,
    PositiveId,
    UtcTimestamp,
    validate_date_range,
)


class OrderItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: PositiveId
    quantity: Annotated[int, Field(strict=True, ge=1, le=10_000)]


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ordered_at: InputTimestamp
    status: OrderStatus
    items: list[OrderItemCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_unique_products(self) -> Self:
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("Each product may appear only once per order")
        return self


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ordered_at: UtcTimestamp
    status: OrderStatus
    created_at: UtcTimestamp


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    product_id: int
    quantity: int
    unit_price: Decimal


class OrderRead(OrderSummary):
    items: list[OrderItemRead]


class OrderFilters(Pagination):
    status: OrderStatus | None = None
    start: InputTimestamp | None = None
    end: InputTimestamp | None = None

    @model_validator(mode="after")
    def check_range(self) -> Self:
        validate_date_range(self.start, self.end)
        return self
