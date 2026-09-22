import asyncio
import time
from typing import Any, Callable, Awaitable

from .errors import SmartRemakeError


async def wait_for_batch(
    request_ids: list[str],
    get_status: Callable[[str], Awaitable[dict[str, Any]]],
    *,
    failure_code: str,
    interval_seconds: float = 2.0,
    timeout_seconds: float = 900.0,
) -> dict[str, dict[str, Any]]:
    pending = set(request_ids)
    statuses: dict[str, dict[str, Any]] = {}
    deadline = time.monotonic() + timeout_seconds
    failed_statuses = {"failed", "error", "cancelled", "canceled"}

    while pending:
        if time.monotonic() >= deadline:
            raise SmartRemakeError(
                "FlowKit batch polling timed out.",
                "FLOWKIT_POLL_TIMEOUT",
                {"requestIds": sorted(pending)},
            )
        completed = set()
        for request_id in sorted(pending):
            status_payload = await get_status(request_id)
            statuses[request_id] = status_payload
            status = str(status_payload.get("status", "")).lower()
            if status in {"completed", "succeeded", "success", "done"}:
                completed.add(request_id)
            elif status in failed_statuses:
                raise SmartRemakeError(
                    f"FlowKit request {request_id} failed.",
                    failure_code,
                    {"requestId": request_id, "status": status_payload},
                )
        pending -= completed
        if pending:
            await asyncio.sleep(interval_seconds)
    return statuses
