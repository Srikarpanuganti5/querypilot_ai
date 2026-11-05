"""Approved analytics and document search; independent of HTTP and LLM providers."""

import logging
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from querypilot.core.config import Settings
from querypilot.core.security import SecretGuard
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
from querypilot.schemas.documents import DocumentSearchInput, DocumentSearchOutput
from querypilot.services.document_search import DocumentError, DocumentIndex

logger = logging.getLogger("querypilot.tools")


@dataclass(frozen=True)
class ToolDefinition:
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    description: str


_TOOLS = {
    "search_business_documents": ToolDefinition(
        DocumentSearchInput,
        DocumentSearchOutput,
        "Retrieve untrusted synthetic business passages with citations",
    ),
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
    def __init__(
        self,
        repository: AnalyticsRepository | None = None,
        *,
        document_index: DocumentIndex | None = None,
        settings: Settings | None = None,
    ):
        self._repository = repository
        self._document_index = document_index
        self._settings = settings
        self._guard = SecretGuard(settings if settings is not None else Settings())

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
                error = ToolError(code="unknown_tool", message="Unknown tool.")
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
                    if known_name == "search_business_documents":
                        if self._document_index is None:
                            config = self._settings if self._settings is not None else Settings()
                            self._document_index = DocumentIndex.from_directory(
                                config.documents_path
                            )
                        output = self._document_index.search(validated).model_dump()
                    else:
                        if self._repository is None:
                            config = self._settings if self._settings is not None else Settings()
                            try:
                                self._repository = AnalyticsRepository(
                                    create_database(config, reader=True),
                                    config.db_statement_timeout_ms,
                                )
                            except DatabaseError:
                                raise _ConfigurationError from None
                        rows, truncated = self._repository.execute(known_name, validated)
                        output = {"rows": rows, "truncated": truncated}
                    try:
                        data = definition.output_schema.model_validate(output)
                        if self._guard.contains(data.model_dump(mode="json")):
                            data = None
                            error = ToolError(
                                code="sensitive_output",
                                message="Credential-like tool content was withheld.",
                            )
                    except ValidationError:
                        error = ToolError(
                            code="invalid_output", message="Tool result failed validation."
                        )
        except _ConfigurationError:
            error = ToolError(
                code="configuration_error", message="Configure restricted READER_DATABASE_URL."
            )
        except DocumentError:
            error = ToolError(
                code="document_error", message="Business document collection unavailable."
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
            error = ToolError(code="internal_error", message="Tool execution failed.")
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
        if self._repository is not None:
            self._repository.close()


class _ConfigurationError(Exception):
    pass


def create_registry(settings: Settings | None = None) -> ToolRegistry:
    config = settings if settings is not None else Settings()
    # Search needs no database. Reader credentials are required lazily for SQL calls only.
    return ToolRegistry(settings=config)
