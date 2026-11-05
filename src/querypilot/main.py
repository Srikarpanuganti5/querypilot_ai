"""FastAPI composition root. Run with uvicorn querypilot.main:app --reload."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from querypilot.api.errors import http_error, internal_error, validation_error
from querypilot.api.middleware import AgentBodyLimitMiddleware, RequestLoggingMiddleware
from querypilot.api.router import router
from querypilot.core.config import Settings, get_settings
from querypilot.core.logging import configure_logging
from querypilot.schemas.system import ErrorResponse

logger = logging.getLogger("querypilot.lifecycle")


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(config.log_level, settings=config)
        logger.info("application_started")
        try:
            yield
        finally:
            logger.info("application_stopped")

    application = FastAPI(
        title="QueryPilot AI",
        version=version("querypilot-ai"),
        description="Tool-Using LLM Agent API",
        debug=False,
        lifespan=lifespan,
    )
    application.state.settings = config
    application.add_exception_handler(HTTPException, http_error)
    application.add_exception_handler(RequestValidationError, validation_error)
    application.add_exception_handler(Exception, internal_error)
    application.include_router(
        router,
        responses={
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    application.add_middleware(AgentBodyLimitMiddleware)
    application.add_middleware(RequestLoggingMiddleware)
    # Outer CORS middleware also decorates the sanitized 500 responses.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
        expose_headers=["X-Request-ID"],
    )
    return application


app = create_app()
