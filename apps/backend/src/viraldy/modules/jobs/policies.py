from __future__ import annotations

from viraldy.shared.errors.base import AppError


def ensure_transition(current: str, target: str) -> None:
    allowed = {
        "queued": {"dispatching", "running", "cancelled"},
        "dispatching": {"running", "queued", "failed"},
        "running": {"retrying", "succeeded", "failed", "cancelled"},
        "retrying": {"running", "failed"},
    }
    if target not in allowed.get(current, set()):
        raise AppError(
            "INVALID_JOB_TRANSITION", f"Cannot transition job from {current} to {target}."
        )
