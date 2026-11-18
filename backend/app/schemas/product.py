from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator, with_config
from typing_extensions import TypedDict

from backend.app.schemas.common import MAX_INT, Money, Pagination, UtcTimestamp

Sku = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Stock = Annotated[int, Field(ge=0, le=MAX_INT)]


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: Sku
    name: Name
    price: Money
    stock: Stock


@with_config(ConfigDict(extra="forbid"))
class ProductUpdate(TypedDict, total=False):
    sku: Sku
    name: Name
    price: Money
    stock: Stock


class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: UtcTimestamp
    updated_at: UtcTimestamp


class ProductFilters(Pagination):
    name: Name | None = None
    sku: Sku | None = None
    min_stock: Stock | None = None
    max_stock: Stock | None = None
    stock_below: Stock | None = None

    @model_validator(mode="after")
    def validate_stock_range(self) -> Self:
        if self.min_stock is not None and self.max_stock is not None:
            if self.min_stock > self.max_stock:
                raise ValueError("min_stock must be less than or equal to max_stock")
        return self
