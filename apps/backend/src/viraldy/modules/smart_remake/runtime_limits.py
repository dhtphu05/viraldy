"""Finite KIE worker windows derived from server-owned execution workloads."""

from __future__ import annotations

import math
import os
from typing import Any

DEFAULT_KIE_POLL_TIMEOUT_SECONDS = 900.0
# Per video call: up to three uploads (270s), provider response (60s),
# download (120s), decode (120s), and persistence/reconciliation margin.
KIE_COMPLETION_GRACE_SECONDS = 1200
# Each generated conditioning image has one image call (180s) and inspection (300s).
KIE_CONDITIONING_WINDOW_SECONDS = 480
KIE_PREPARATION_WINDOW_SECONDS = 300
KIE_SHUTDOWN_GRACE_SECONDS = 60


def kie_poll_timeout_seconds() -> float:
    raw = os.getenv("KIE_POLL_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_KIE_POLL_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except ValueError:
        return DEFAULT_KIE_POLL_TIMEOUT_SECONDS
    if not math.isfinite(timeout):
        raise ValueError("KIE_POLL_TIMEOUT_SECONDS must be finite.")
    return timeout if timeout > 0 else DEFAULT_KIE_POLL_TIMEOUT_SECONDS


def kie_job_runtime_input(
    state: dict[str, Any], context: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    """Called only by owned enqueue paths, never with browser-supplied counts."""
    kind = result.get("kind")
    if kind not in {"render", "repair"}:
        return {}
    plan = result.get("renderPlan") or context.get("renderPlan") or {}
    groups = plan.get("groups") or []
    if kind == "repair":
        calls = 1
    elif groups:
        calls = len(groups)
    else:
        calls = len(state.get("scenes") or [])
    if not calls:
        return {}
    return {
        "kie_runtime": {
            "schemaVersion": 1,
            "videoCallCount": calls,
            "conditioningImageCount": 2 * calls if plan.get("imageModel") else 0,
            "analysisCallCount": int(bool(result.get("request", {}).get("repairIntent"))),
            "pollTimeoutSeconds": kie_poll_timeout_seconds(),
        }
    }


def kie_worker_timeout_seconds(input_json: dict[str, Any] | None = None) -> int | None:
    """Dispatch and recovery use the same frozen metadata; old jobs stay unchanged."""
    runtime = (input_json or {}).get("kie_runtime")
    if not isinstance(runtime, dict) or runtime.get("schemaVersion") != 1:
        return None
    counts: list[int] = []
    for key in ("videoCallCount", "conditioningImageCount", "analysisCallCount"):
        value = runtime.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return None
        counts.append(value)
    calls, images, analysis = counts
    if calls < 1 or analysis > 1:
        return None
    poll = runtime.get("pollTimeoutSeconds")
    if (
        isinstance(poll, bool)
        or not isinstance(poll, int | float)
        or not math.isfinite(poll)
        or poll <= 0
    ):
        return None
    return (
        KIE_PREPARATION_WINDOW_SECONDS
        + calls * (math.ceil(poll) + KIE_COMPLETION_GRACE_SECONDS)
        + images * KIE_CONDITIONING_WINDOW_SECONDS
        + analysis * KIE_PREPARATION_WINDOW_SECONDS
        + KIE_SHUTDOWN_GRACE_SECONDS
    )


def kie_job_poll_timeout_seconds(input_json: dict[str, Any]) -> float | None:
    if kie_worker_timeout_seconds(input_json) is None:
        return None
    return float(input_json["kie_runtime"]["pollTimeoutSeconds"])
