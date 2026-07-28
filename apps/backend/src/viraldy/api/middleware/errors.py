from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from viraldy.api.responses.envelope import failure
from viraldy.shared.errors.base import AppError

logger = structlog.get_logger(__name__)


def request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=failure(exc.code, exc.message, request_id(request), exc.details),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=failure(
            "VALIDATION_ERROR",
            "Request validation failed.",
            request_id(request),
            {"errors": exc.errors()},
        ),
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unexpected_api_error", path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=failure("INTERNAL_ERROR", "Internal server error.", request_id(request)),
    )
