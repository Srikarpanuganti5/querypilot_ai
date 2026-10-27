"""initial ecommerce schema"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("customer_id", name=op.f("pk_customers")),
        sa.UniqueConstraint("email", name=op.f("uq_customers_email")),
    )
    op.create_table(
        "products",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price > 0", name="ck_products_price_positive"),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_products_stock_nonnegative"),
        sa.PrimaryKeyConstraint("product_id", name=op.f("pk_products")),
    )
    op.create_index("ix_products_category", "products", ["category"], unique=False)
    op.create_table(
        "orders",
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("order_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.CheckConstraint(
            "status IN ('completed','pending','cancelled','refunded')", name="ck_orders_status"
        ),
        sa.CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customers.customer_id"], name=op.f("fk_orders_customer_id_customers")
        ),
        sa.PrimaryKeyConstraint("order_id", name=op.f("pk_orders")),
    )
    op.create_index(op.f("ix_orders_customer_id"), "orders", ["customer_id"], unique=False)
    op.create_index("ix_orders_status_date", "orders", ["status", "order_date"], unique=False)
    op.create_table(
        "order_items",
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price > 0", name="ck_order_items_price_positive"),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.order_id"], name=op.f("fk_order_items_order_id_orders")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.product_id"], name=op.f("fk_order_items_product_id_products")
        ),
        sa.PrimaryKeyConstraint("order_item_id", name=op.f("pk_order_items")),
        sa.UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_items_product_id"), "order_items", ["product_id"], unique=False)
    op.create_table(
        "payments",
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payment_method", sa.String(length=20), nullable=False),
        sa.Column("payment_status", sa.String(length=20), nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "payment_method IN ('card','bank_transfer','wallet')", name="ck_payments_method"
        ),
        sa.CheckConstraint("payment_status IN ('successful','failed')", name="ck_payments_status"),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.order_id"], name=op.f("fk_payments_order_id_orders")
        ),
        sa.PrimaryKeyConstraint("payment_id", name=op.f("pk_payments")),
    )
    op.create_index(op.f("ix_payments_order_id"), "payments", ["order_id"], unique=False)
    op.create_index(
        "ix_payments_status_date", "payments", ["payment_status", "payment_date"], unique=False
    )
    op.create_index(
        "uq_payments_successful_order",
        "payments",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("payment_status = 'successful'"),
    )
    op.create_table(
        "refunds",
        sa.Column("refund_id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("refund_reason", sa.String(length=200), nullable=False),
        sa.Column("refund_date", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_refunds_amount_positive"),
        sa.ForeignKeyConstraint(
            ["payment_id"], ["payments.payment_id"], name=op.f("fk_refunds_payment_id_payments")
        ),
        sa.PrimaryKeyConstraint("refund_id", name=op.f("pk_refunds")),
    )
    op.create_index(op.f("ix_refunds_payment_id"), "refunds", ["payment_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_refunds_payment_id"), table_name="refunds")
    op.drop_table("refunds")
    op.drop_index(
        "uq_payments_successful_order",
        table_name="payments",
        postgresql_where=sa.text("payment_status = 'successful'"),
    )
    op.drop_index("ix_payments_status_date", table_name="payments")
    op.drop_index(op.f("ix_payments_order_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_order_items_product_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_status_date", table_name="orders")
    op.drop_index(op.f("ix_orders_customer_id"), table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_table("products")
    op.drop_table("customers")
