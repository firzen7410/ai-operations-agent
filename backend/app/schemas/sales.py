from decimal import Decimal

from pydantic import BaseModel

from backend.app.schemas.common import DateRange, PositiveId, UtcTimestamp


class SalesFilters(DateRange):
    product_id: PositiveId | None = None


class ProductSales(BaseModel):
    product_id: int
    sku: str
    name: str
    units_sold: int
    revenue: Decimal


class SalesSummary(BaseModel):
    start: UtcTimestamp
    end: UtcTimestamp
    units_sold: int
    revenue: Decimal
    items: list[ProductSales]
