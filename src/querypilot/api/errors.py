"""Consistent client errors without request values or internal exception text."""

from http import HTTPStatus

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from querypilot.schemas.system import ErrorDetail, ErrorResponse, ValidationIssue


def error_response(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: list[ValidationIssue] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(
            code=code, message=message, request_id=request.state.request_id, details=details or []
        )
    )
    return JSONResponse(body.model_dump(), status_code=status, headers=headers)


async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    # Exception.detail can contain internal or user-provided text; use standard phrases.
    message = HTTPStatus(exc.status_code).phrase if exc.status_code in HTTPStatus else "HTTP error"
    return error_response(request, exc.status_code, "http_error", message, headers=exc.headers)


async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ValidationIssue(location=list(item["loc"]), type=item["type"]) for item in exc.errors()
    ]
    return error_response(request, 422, "validation_error", "Request validation failed", details)


async def internal_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(request, 500, "internal_error", "An unexpected error occurred")
