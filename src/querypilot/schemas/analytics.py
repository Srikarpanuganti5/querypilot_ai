"""Provider-independent analytics inputs, bounded outputs, and stable errors."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from querypilot.schemas.documents import DocumentSearchOutput

ToolName = Literal[
    "get_top_products",
    "get_revenue_summary",
    "get_refund_analytics",
    "get_customer_order_summary",
    "get_payment_status_summary",
    "search_business_documents",
]
Money = Annotated[Decimal, Field(ge=0, decimal_places=2)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DateRange(Contract):
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def dates_only(cls, value: object) -> object:
        if value is None:
            return None
        if (
            isinstance(value, datetime)
            or not isinstance(value, (str, date))
            or (isinstance(value, str) and len(value) != 10)
        ):
            raise ValueError("Use a calendar date, YYYY-MM-DD")
        return value

    @model_validator(mode="after")
    def valid_window(self) -> "DateRange":
        if self.start_date is not None and self.end_date is not None:
            if self.start_date >= self.end_date:
                raise ValueError("start_date must precede end_date")
            if (self.end_date - self.start_date).days > 366:
                raise ValueError("Date ranges may not exceed 366 days")
        return self


class TopProductsInput(DateRange):
    limit: int = Field(default=5, strict=True, ge=1, le=20)


class RevenueInput(DateRange):
    group_by: Literal["day", "month", "category"] = "month"


class RefundInput(DateRange):
    limit: int = Field(default=10, strict=True, ge=1, le=20)


class CustomerInput(Contract):
    customer_id: int | None = Field(default=None, strict=True, ge=1, le=2147483647)
    limit: int = Field(default=10, strict=True, ge=1, le=20)


class PaymentInput(DateRange):
    pass


class TopProductRow(Contract):
    product_id: int = Field(ge=1)
    name: str = Field(max_length=120)
    category: str = Field(max_length=60)
    units_sold: int = Field(ge=0)
    revenue: Money


class RevenueRow(Contract):
    bucket: str = Field(max_length=60)
    order_count: int = Field(ge=0)
    revenue: Money


class RefundRow(Contract):
    category: str = Field(max_length=60)
    refund_count: int = Field(ge=0)
    order_count: int = Field(ge=0)
    refund_amount: Money


class CustomerRow(Contract):
    customer_id: int = Field(ge=1)
    order_count: int = Field(ge=0)
    completed_orders: int = Field(ge=0)
    pending_orders: int = Field(ge=0)
    cancelled_orders: int = Field(ge=0)
    refunded_orders: int = Field(ge=0)
    completed_revenue: Money


class PaymentRow(Contract):
    payment_status: Literal["successful", "failed"]
    payment_count: int = Field(ge=0)
    amount: Money


class Output(Contract):
    currency: Literal["USD"] = "USD"
    truncated: bool = False


class TopProductsOutput(Output):
    operation: Literal["get_top_products"] = "get_top_products"
    rows: list[TopProductRow] = Field(max_length=20)


class RevenueOutput(Output):
    operation: Literal["get_revenue_summary"] = "get_revenue_summary"
    rows: list[RevenueRow] = Field(max_length=400)


class RefundOutput(Output):
    operation: Literal["get_refund_analytics"] = "get_refund_analytics"
    rows: list[RefundRow] = Field(max_length=20)


class CustomerOutput(Output):
    operation: Literal["get_customer_order_summary"] = "get_customer_order_summary"
    rows: list[CustomerRow] = Field(max_length=20)


class PaymentOutput(Output):
    operation: Literal["get_payment_status_summary"] = "get_payment_status_summary"
    rows: list[PaymentRow] = Field(max_length=2)


ToolOutput = Annotated[
    TopProductsOutput
    | RevenueOutput
    | RefundOutput
    | CustomerOutput
    | PaymentOutput
    | DocumentSearchOutput,
    Field(discriminator="operation"),
]


class ToolError(Contract):
    code: Literal[
        "unknown_tool",
        "invalid_arguments",
        "configuration_error",
        "unsafe_database",
        "timeout",
        "database_error",
        "invalid_output",
        "internal_error",
        "document_error",
        "sensitive_output",
    ]
    message: str


class ToolResult(Contract):
    tool: ToolName | None
    status: Literal["success", "error"]
    data: ToolOutput | None = None
    error: ToolError | None = None
    duration_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def consistent_result(self) -> "ToolResult":
        if self.status == "success":
            if self.data is None or self.error is not None or self.data.operation != self.tool:
                raise ValueError("Success requires matching data and no error")
        elif self.data is not None or self.error is None:
            raise ValueError("Error requires an error and no data")
        return self
