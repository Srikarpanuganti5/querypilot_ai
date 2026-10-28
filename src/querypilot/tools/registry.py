"""Five approved analytics tools; independent of HTTP and any LLM provider."""

import logging
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from querypilot.core.config import Settings
from querypilot.db.analytics import AnalyticsRepository, UnsafeDatabaseError
from querypilot.db.session import DatabaseError, create_database
from querypilot.schemas.analytics import (
    CustomerInput,
    CustomerOutput,
    PaymentInput,
    PaymentOutput,
    RefundInput,
    RefundOutput,
    RevenueInput,
    RevenueOutput,
    ToolError,
    ToolResult,
    TopProductsInput,
    TopProductsOutput,
)

logger = logging.getLogger("querypilot.tools")


@dataclass(frozen=True)
class ToolDefinition:
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    description: str


_TOOLS = {
    "get_top_products": ToolDefinition(
        TopProductsInput, TopProductsOutput, "Completed-order product revenue"
    ),
    "get_revenue_summary": ToolDefinition(
        RevenueInput, RevenueOutput, "Completed revenue by UTC day/month or category"
    ),
    "get_refund_analytics": ToolDefinition(
        RefundInput, RefundOutput, "Refund-date category allocation"
    ),
    "get_customer_order_summary": ToolDefinition(
        CustomerInput, CustomerOutput, "Non-sensitive order aggregates by customer ID"
    ),
    "get_payment_status_summary": ToolDefinition(
        PaymentInput, PaymentOutput, "Payment-date attempts and amounts by status"
    ),
}


class ToolRegistry:
    def __init__(self, repository: AnalyticsRepository):
        self._repository = repository

    def definitions(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "description": tool.description,
                "input_schema": tool.input_schema.model_json_schema(),
                "output_schema": tool.output_schema.model_json_schema(),
            }
            for name, tool in _TOOLS.items()
        }

    def execute(self, name: str, arguments: object) -> ToolResult:
        started = time.monotonic()
        known_name = name if isinstance(name, str) and name in _TOOLS else None
        data, error = None, None
        try:
            if known_name is None:
                error = ToolError(code="unknown_tool", message="Unknown analytics tool.")
            else:
                definition = _TOOLS[known_name]
                try:
                    if not isinstance(arguments, dict) or len(arguments) > 4:
                        raise ValueError("Invalid arguments")
                    validated = definition.input_schema.model_validate(arguments)
                except (ValidationError, ValueError):
                    error = ToolError(
                        code="invalid_arguments", message="Arguments do not match the tool schema."
                    )
                else:
                    rows, truncated = self._repository.execute(known_name, validated)
                    try:
                        data = definition.output_schema.model_validate(
                            {"rows": rows, "truncated": truncated}
                        )
                    except ValidationError:
                        error = ToolError(
                            code="invalid_output", message="Analytics result failed validation."
                        )
        except UnsafeDatabaseError:
            error = ToolError(
                code="unsafe_database", message="Database role is not a restricted reader."
            )
        except DatabaseError as exc:
            code = "timeout" if exc.code == "timeout" else "database_error"
            error = ToolError(
                code=code,
                message="Query timed out."
                if code == "timeout"
                else "Analytics database unavailable.",
            )
        except Exception:
            error = ToolError(code="internal_error", message="Analytics execution failed.")
        duration = int((time.monotonic() - started) * 1000)
        status = "success" if error is None else "error"
        logger.info(
            "tool_execution",
            extra={
                "tool": known_name or "unknown",
                "status": status,
                "duration_ms": duration,
            },
        )
        return ToolResult(
            tool=known_name, status=status, data=data, error=error, duration_ms=duration
        )

    def close(self) -> None:
        self._repository.close()


def create_registry(settings: Settings | None = None) -> ToolRegistry:
    config = settings if settings is not None else Settings()
    # Missing reader settings fail explicitly; writer credentials are never consulted.
    return ToolRegistry(
        AnalyticsRepository(create_database(config, reader=True), config.db_statement_timeout_ms)
    )
