"""Public system metadata and sanitized error contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    service: str
    version: str


class InfoResponse(BaseModel):
    name: str
    version: str
    description: str


class ValidationIssue(BaseModel):
    location: list[str | int]
    type: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[ValidationIssue] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorDetail
