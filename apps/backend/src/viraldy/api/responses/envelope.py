from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    has_next: bool


class ResponseMeta(BaseModel):
    request_id: str
    pagination: PaginationMeta | None = None


class Envelope(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: Any
    meta: ResponseMeta
    error: ErrorBody | None = None


def success(data: Any, request_id: str, pagination: PaginationMeta | None = None) -> Envelope:
    return Envelope(data=data, meta=ResponseMeta(request_id=request_id, pagination=pagination))


def failure(
    code: str, message: str, request_id: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "data": None,
        "meta": {"request_id": request_id},
        "error": {"code": code, "message": message, "details": details or {}},
    }
