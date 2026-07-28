from __future__ import annotations

import pytest

from viraldy.modules.jobs.policies import ensure_transition
from viraldy.shared.errors.base import AppError


def test_job_state_machine_allows_queued_to_running() -> None:
    ensure_transition("queued", "running")


def test_job_state_machine_rejects_completed_to_running() -> None:
    with pytest.raises(AppError, match="INVALID_JOB_TRANSITION"):
        ensure_transition("completed", "running")
