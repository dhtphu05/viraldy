from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

import structlog.contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        incoming = request.headers.get("X-Request-ID")
        try:
            request_id = str(UUID(incoming)) if incoming else str(uuid4())
        except (TypeError, ValueError):
            request_id = str(uuid4())
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = cast(Response, await call_next(request))
        response.headers["X-Request-ID"] = request_id
        structlog.contextvars.clear_contextvars()
        return response
