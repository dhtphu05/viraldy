from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.ai_gateway.repository import AiModelRunRepository
from viraldy.modules.ai_gateway.schemas import AiModelRunResponse, AiModelRunStatus
from viraldy.shared.errors.base import NotFoundError


class AiModelRunService:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = AiModelRunRepository(session)

    async def list_runs(
        self,
        *,
        workspace_id: UUID,
        subject_type: str | None,
        subject_id: UUID | None,
        operation: str | None,
        status: AiModelRunStatus | None,
        limit: int,
    ) -> list[AiModelRunResponse]:
        runs = await self._repository.list_runs(
            workspace_id=workspace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            operation=operation,
            status=status,
            limit=limit,
        )
        return [AiModelRunResponse.model_validate(run) for run in runs]

    async def get_run(
        self,
        workspace_id: UUID,
        model_run_id: UUID,
    ) -> AiModelRunResponse:
        run = await self._repository.get_run(workspace_id, model_run_id)
        if run is None:
            raise NotFoundError("MODEL_RUN_NOT_FOUND", "Model run was not found.")
        return AiModelRunResponse.model_validate(run)
