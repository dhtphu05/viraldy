from __future__ import annotations

from viraldy.shared.errors.base import AppError

ACTION_TYPES = {"viewed", "accepted", "rejected", "applied", "ignored"}


def validate_action_type(action_type: str) -> None:
    if action_type not in ACTION_TYPES:
        raise AppError(
            "INVALID_RECOMMENDATION_ACTION", "Recommendation action type is not supported."
        )
