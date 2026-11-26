from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from .errors import SmartRemakeError


async def wait_for_kie_task(
    task_id: str,
    status_fn: Callable[[str], Awaitable[dict[str, Any]]],
    *,
    interval_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_state: str | None = None
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            task = await asyncio.wait_for(status_fn(task_id), timeout=remaining)
        except TimeoutError:
            break
        except SmartRemakeError as exc:
            raise SmartRemakeError(str(exc), exc.code, {"taskId": task_id}) from exc
        state = task.get("status")
        if state == "completed":
            return task
        if state == "failed":
            raise SmartRemakeError(
                task.get("error_message") or "KIE generation failed.",
                "KIE_TASK_FAILED",
                {"taskId": task_id},
            )
        if state not in {"queued", "processing"}:
            raise SmartRemakeError(
                "KIE returned an unknown task state.",
                "KIE_INVALID_RESPONSE",
                {"taskId": task_id},
            )
        last_state = state
        await asyncio.sleep(min(max(interval_seconds, 0.001), max(deadline - time.monotonic(), 0)))
    raise SmartRemakeError(
        "KIE is still rendering. Check this existing task instead of creating another render.",
        "KIE_POLL_TIMEOUT",
        {"taskId": task_id, "lastState": last_state},
    )
