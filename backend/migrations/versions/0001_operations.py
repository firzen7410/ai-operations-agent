"""Create product and order tables."""

import sqlalchemy as sa
from alembic import op

revision = "0001_operations"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
        sa.CheckConstraint("price_cents >= 0", name="ck_products_price_nonnegative"),
        sa.CheckConstraint("stock >= 0", name="ck_products_stock_nonnegative"),
    )
    op.create_index("ix_products_stock", "products", ["stock"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ordered_at", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "completed", "cancelled",
                name="ck_orders_status", native_enum=False, create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_orders_ordered_at", "orders", ["ordered_at"])
    op.create_index("ix_orders_status_ordered_at", "orders", ["status", "ordered_at"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price_cents >= 0", name="ck_order_items_price_nonnegative"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name="fk_order_items_product_id"
        ),
    )
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"])


def downgrade() -> None:
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("products")
