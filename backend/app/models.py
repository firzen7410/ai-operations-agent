from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_products_sku"),
        CheckConstraint("price_cents >= 0", name="ck_products_price_nonnegative"),
        CheckConstraint("stock >= 0", name="ck_products_stock_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    price_cents: Mapped[int]
    stock: Mapped[int] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    @property
    def price(self) -> Decimal:
        return Decimal(self.price_cents).scaleb(-2)


class OrderStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_status_ordered_at", "status", "ordered_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ordered_at: Mapped[datetime] = mapped_column(index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            name="ck_orders_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    items: Mapped[list["OrderItem"]] = relationship(
        order_by="OrderItem.id", cascade="all, delete-orphan", passive_deletes=True
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price_cents >= 0", name="ck_order_items_price_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", name="fk_order_items_product_id"), index=True
    )
    quantity: Mapped[int]
    unit_price_cents: Mapped[int]

    @property
    def unit_price(self) -> Decimal:
        return Decimal(self.unit_price_cents).scaleb(-2)


class AgentRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint("status IN ('running', 'completed', 'failed')", name="ck_agent_runs_status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default=AgentRunStatus.RUNNING)
    response: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    completed_at: Mapped[datetime | None]
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        order_by="ToolExecution.id", cascade="all, delete-orphan", passive_deletes=True
    )


class ToolExecution(Base):
    __tablename__ = "tool_executions"
    __table_args__ = (
        CheckConstraint("status IN ('success', 'failed')", name="ck_tool_executions_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(64))
    arguments: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    result: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    status: Mapped[str] = mapped_column(String(16))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
