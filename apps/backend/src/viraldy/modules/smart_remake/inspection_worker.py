"""Worker entry kept separate from route dispatch and Inspector implementation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from .inspection_service import InspectionService


async def run_inspection_job(
    service: InspectionService,
    project_id: UUID,
    operation_id: UUID,
    *,
    invoke_model: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    return await service.execute(project_id, operation_id, invoke_model=invoke_model)
