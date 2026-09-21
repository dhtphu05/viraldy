import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from .errors import SmartRemakeError


async def wait_for_unifically_task(
    task_id: str,
    status_fn: Callable[[str], Awaitable[dict[str, Any]]],
    *,
    interval_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status: dict[str, Any] | None = None

    while time.monotonic() < deadline:
        status = await status_fn(task_id)
        last_status = status
        state = str(status.get("status", "")).lower()
        if state == "completed":
            return status
        if state == "failed":
            raise SmartRemakeError(
                status.get("error_message") or "Unifically task failed.",
                "UNIFICALLY_TASK_FAILED",
                {"taskId": task_id, "status": status},
            )
        await asyncio.sleep(interval_seconds)

    raise SmartRemakeError(
        "Unifically task polling timed out.",
        "UNIFICALLY_POLL_TIMEOUT",
        {"taskId": task_id, "lastStatus": last_status},
    )
