from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import Product
from backend.app.schemas.common import MAX_INT, DateRange
from backend.app.schemas.product import ProductFilters, ProductRead
from backend.app.schemas.sales import SalesFilters
from backend.app.services.products import list_products
from backend.app.services.sales import product_sales_query, read_product_sales

ToolResult = dict[str, Any]
Nonnegative = Annotated[int, Field(strict=True, ge=0, le=MAX_INT)]
ProductId = Annotated[int, Field(strict=True, gt=0, le=MAX_INT)]


class ToolPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: Annotated[int, Field(strict=True, ge=1, le=50)] = 20
    offset: Nonnegative = 0


class LowStockArgs(ToolPage):
    threshold: Nonnegative


class SalesArgs(ToolPage, DateRange):
    product_id: ProductId | None = None

    @model_validator(mode="after")
    def bound_range(self) -> Self:
        if self.end - self.start > timedelta(days=366):
            raise ValueError("Date range must not exceed 366 days")
        return self


class RestockArgs(ToolPage, DateRange):
    product_ids: Annotated[list[ProductId], Field(min_length=1, max_length=50)] | None = None
    stock_below: Nonnegative | None = None
    units_sold_above: Nonnegative | None = None
    lead_time_days: Annotated[int, Field(strict=True, ge=1, le=365)] = 14
    safety_stock: Nonnegative = 5

    @model_validator(mode="after")
    def bound_range(self) -> Self:
        if self.end - self.start > timedelta(days=366):
            raise ValueError("Date range must not exceed 366 days")
        return self


def low_stock(session: Session, args: LowStockArgs) -> ToolResult:
    items, total = list_products(
        session, ProductFilters(stock_below=args.threshold, limit=args.limit, offset=args.offset)
    )
    return {
        "items": [ProductRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "limit": args.limit,
        "offset": args.offset,
        "stock_below": args.threshold,
    }


def sales_summary(session: Session, args: SalesArgs) -> ToolResult:
    filters = SalesFilters(start=args.start, end=args.end, product_id=args.product_id)
    query = product_sales_query(filters)
    grouped = query.subquery()
    totals = select(func.count(), func.sum(grouped.c.units_sold), func.sum(grouped.c.revenue_cents))
    total, units, revenue_cents = session.execute(totals).one()
    page = query.order_by(Product.id).limit(args.limit).offset(args.offset)
    return {
        "start": args.start.isoformat(),
        "end": args.end.isoformat(),
        "units_sold": int(units or 0),
        "revenue": str(Decimal(revenue_cents or 0).scaleb(-2)),
        "items": [item.model_dump(mode="json") for item in read_product_sales(session, page)],
        "total": total,
        "limit": args.limit,
        "offset": args.offset,
    }


def calculate_restock(session: Session, args: RestockArgs) -> ToolResult:
    history = product_sales_query(SalesFilters(start=args.start, end=args.end)).subquery()
    units_sold = func.coalesce(history.c.units_sold, 0)
    query = select(Product.id, Product.sku, Product.name, Product.stock, units_sold).outerjoin(
        history, history.c.id == Product.id
    )
    if args.product_ids is not None:
        query = query.where(Product.id.in_(args.product_ids))
    if args.stock_below is not None:
        query = query.where(Product.stock < args.stock_below)
    if args.units_sold_above is not None:
        query = query.where(units_sold > args.units_sold_above)

    total = session.scalar(select(func.count()).select_from(query.subquery()))
    duration = (args.end - args.start) // timedelta(microseconds=1)
    day = timedelta(days=1) // timedelta(microseconds=1)
    recommendations = []
    page = query.order_by(Product.stock, Product.id).limit(args.limit).offset(args.offset)
    for product_id, sku, name, stock, units_sold_value in session.execute(page):
        units = int(units_sold_value)
        daily_demand = Decimal(units * day) / duration
        lead_time_units = (units * day * args.lead_time_days + duration - 1) // duration
        recommendations.append({
            "product_id": product_id,
            "sku": sku,
            "name": name,
            "stock": stock,
            "units_sold": units,
            "average_daily_units": f"{daily_demand:.2f}",
            "lead_time_units": lead_time_units,
            "recommended_quantity": max(0, lead_time_units + args.safety_stock - stock),
        })

    return {
        "start": args.start.isoformat(),
        "end": args.end.isoformat(),
        "lead_time_days": args.lead_time_days,
        "safety_stock": args.safety_stock,
        "stock_below": args.stock_below,
        "units_sold_above": args.units_sold_above,
        "items": recommendations,
        "total": total,
        "limit": args.limit,
        "offset": args.offset,
    }


@dataclass(frozen=True)
class Tool[T: BaseModel]:
    description: str
    arguments: type[T]
    execute: Callable[[Session, T], ToolResult]


class ToolInputError(Exception):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {
            "get_low_stock_products": Tool(
                "List products whose current stock is strictly below threshold. Use pagination.",
                LowStockArgs, low_stock,
            ),
            "get_sales_summary": Tool(
                "Summarize completed sales for a timezone-aware start (inclusive) and end "
                "(exclusive). Optionally filter by product_id. Totals cover all pages.",
                SalesArgs, sales_summary,
            ),
            "calculate_restock": Tool(
                "Calculate restock recommendations from completed sales for timezone-aware start "
                "(inclusive) and end (exclusive). Can combine stock_below and units_sold_above "
                "(both strict) without looking up IDs first. Defaults: 14 lead days, 5 safety units.",
                RestockArgs, calculate_restock,
            ),
        }

    def definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.arguments.model_json_schema(),
                },
            }
            for name, tool in self._tools.items()
        ]

    def prepare(self, name: str, raw_arguments: str) -> tuple[Tool, BaseModel]:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolInputError("工具不在允許清單中。")
        try:
            return tool, tool.arguments.model_validate_json(raw_arguments)
        except ValidationError as exc:
            fields = ", ".join(
                f"{'.'.join(map(str, error['loc'])) or 'arguments'}: {error['type']}"
                for error in exc.errors(include_url=False, include_context=False, include_input=False)
                if error["type"] != "extra_forbidden"
            )
            hint = f"（{fields[:250]}）" if fields else ""
            raise ToolInputError(f"工具參數驗證失敗{hint}。") from None
