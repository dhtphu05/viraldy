from __future__ import annotations

from fastapi import Request


def get_request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))
