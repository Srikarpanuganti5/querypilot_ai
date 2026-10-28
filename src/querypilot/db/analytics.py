"""Code-owned SELECT builders and runtime privilege verification; no caller SQL."""

from datetime import UTC, datetime

from sqlalchemy import Select, case, distinct, func, select, text
from sqlalchemy.orm import Session

from querypilot.db.models import Customer, Order, OrderItem, Payment, Product, Refund
from querypilot.db.session import Database
from querypilot.schemas.analytics import (
    CustomerInput,
    DateRange,
    PaymentInput,
    RefundInput,
    RevenueInput,
    TopProductsInput,
)

MAX_ROWS = 400


class UnsafeDatabaseError(Exception):
    pass


def _window(statement: Select, column: object, args: DateRange) -> Select:
    if args.start_date is not None:
        statement = statement.where(
            column >= datetime.combine(args.start_date, datetime.min.time(), UTC)
        )
    if args.end_date is not None:
        statement = statement.where(
            column < datetime.combine(args.end_date, datetime.min.time(), UTC)
        )
    return statement


def _top_products(args: TopProductsInput) -> Select:
    revenue = func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue")
    query = (
        select(
            Product.product_id,
            Product.name,
            Product.category,
            func.sum(OrderItem.quantity).label("units_sold"),
            revenue,
        )
        .join(OrderItem, OrderItem.product_id == Product.product_id)
        .join(Order, Order.order_id == OrderItem.order_id)
        .where(Order.status == "completed")
        .group_by(Product.product_id)
        .order_by(revenue.desc(), Product.product_id)
    )
    return _window(query, Order.order_date, args)


def _revenue(args: RevenueInput) -> Select:
    if args.group_by == "category":
        bucket = Product.category.label("bucket")
        query = (
            select(
                bucket,
                func.count(distinct(Order.order_id)).label("order_count"),
                func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
            )
            .select_from(Order)
            .join(OrderItem)
            .join(Product)
        )
    else:
        pattern = {"day": "YYYY-MM-DD", "month": "YYYY-MM"}[args.group_by]
        bucket = func.to_char(func.timezone("UTC", Order.order_date), pattern).label("bucket")
        query = select(
            bucket,
            func.count(Order.order_id).label("order_count"),
            func.sum(Order.total_amount).label("revenue"),
        )
    query = query.where(Order.status == "completed").group_by(bucket).order_by(bucket)
    return _window(query, Order.order_date, args)


def _refunds(args: RefundInput) -> Select:
    amount = func.round(
        func.sum(
            Refund.amount
            * OrderItem.quantity
            * OrderItem.unit_price
            / func.nullif(Order.total_amount, 0)
        ),
        2,
    ).label("refund_amount")
    query = (
        select(
            Product.category,
            func.count(distinct(Refund.refund_id)).label("refund_count"),
            func.count(distinct(Order.order_id)).label("order_count"),
            amount,
        )
        .select_from(Refund)
        .join(Payment)
        .join(Order)
        .join(OrderItem)
        .join(Product)
        .where(Payment.payment_status == "successful")
        .group_by(Product.category)
        .order_by(amount.desc(), Product.category)
    )
    return _window(query, Refund.refund_date, args)


def _customers(args: CustomerInput) -> Select:
    query = (
        select(
            Customer.customer_id,
            func.count(Order.order_id).label("order_count"),
            *[
                func.sum(case((Order.status == status, 1), else_=0)).label(f"{status}_orders")
                for status in ("completed", "pending", "cancelled", "refunded")
            ],
            func.coalesce(
                func.sum(case((Order.status == "completed", Order.total_amount), else_=0)), 0
            ).label("completed_revenue"),
        )
        .outerjoin(Order)
        .group_by(Customer.customer_id)
        .order_by(func.count(Order.order_id).desc(), Customer.customer_id)
    )
    if args.customer_id is not None:
        query = query.where(Customer.customer_id == args.customer_id)
    return query


def _payments(args: PaymentInput) -> Select:
    query = (
        select(
            Payment.payment_status,
            func.count(Payment.payment_id).label("payment_count"),
            func.sum(Payment.amount).label("amount"),
        )
        .group_by(Payment.payment_status)
        .order_by(Payment.payment_status)
    )
    return _window(query, Payment.payment_date, args)


_BUILDERS = {
    "get_top_products": _top_products,
    "get_revenue_summary": _revenue,
    "get_refund_analytics": _refunds,
    "get_customer_order_summary": _customers,
    "get_payment_status_summary": _payments,
}


def _check_reader(session: Session) -> None:
    unsafe = session.scalar(
        text("""
        SELECT current_user <> session_user
            OR r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolbypassrls OR r.rolreplication
            OR EXISTS (SELECT 1 FROM pg_auth_members m WHERE m.member=r.oid)
            OR has_database_privilege(current_user, current_database(), 'CREATE,TEMP')
            OR has_schema_privilege(current_user, current_schema(), 'CREATE')
        FROM pg_roles r WHERE r.rolname=current_user
    """)
    )
    if unsafe is not False:
        raise UnsafeDatabaseError("Restricted reader credentials are required.")
    # All identifiers derive from this fixed list; SQL binds the table name as a value.
    for name in ("customers", "products", "orders", "order_items", "payments", "refunds"):
        allowed = session.scalar(
            text("""
            SELECT has_table_privilege(current_user,
                format('%I.%I', current_schema(), CAST(:table AS text)), 'SELECT')
                AND NOT has_table_privilege(current_user,
                    format('%I.%I', current_schema(), CAST(:table AS text)),
                    'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                AND NOT EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname=current_schema() AND c.relname=CAST(:table AS text)
                        AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
                )
        """),
            {"table": name},
        )
        if allowed is not True:
            raise UnsafeDatabaseError("Restricted reader credentials are required.")


class AnalyticsRepository:
    def __init__(self, database: Database, timeout_ms: int = 5000):
        if not 100 <= timeout_ms <= 30000:
            raise ValueError("Query timeout must be between 100 and 30000 ms")
        self.database = database
        self.timeout_ms = timeout_ms

    def execute(self, operation: str, arguments: object) -> tuple[list[dict], bool]:
        # Dispatch is internal and allowlisted; no SQL/string/expression argument is accepted.
        if operation not in _BUILDERS:
            raise ValueError("Unknown analytics operation")
        limit = getattr(arguments, "limit", MAX_ROWS if operation == "get_revenue_summary" else 2)
        query = _BUILDERS[operation](arguments).limit(limit + 1)
        with self.database.transaction() as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            session.execute(
                select(func.set_config("statement_timeout", str(self.timeout_ms), True))
            )
            _check_reader(session)
            rows = [dict(row) for row in session.execute(query).mappings().fetchmany(limit + 1)]
        return rows[:limit], len(rows) > limit

    def close(self) -> None:
        self.database.close()
