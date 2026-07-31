from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.ai_gateway.repository import AiModelRunRepository, AiUsageRecord
from viraldy.modules.ai_gateway.schemas import (
    AiModelRunResponse,
    AiModelRunStatus,
    AiUsageAggregateResponse,
)
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

    async def usage_summary(self, workspace_id: UUID) -> AiUsageAggregateResponse:
        runs = await self._repository.list_completed_for_usage(workspace_id)
        return summarize_usage_records(runs)


def summarize_usage_records(runs: list[AiUsageRecord]) -> AiUsageAggregateResponse:
    reported = [
        run
        for run in runs
        if any(
            type(run.usage_json.get(field)) is int
            for field in (
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "cached_input_tokens",
            )
        )
    ]

    def token_sum(field: str) -> int | None:
        values = [value for run in reported if type(value := run.usage_json.get(field)) is int]
        return sum(values) if values else None

    costs = [run.estimated_cost for run in reported if run.estimated_cost is not None]
    cost_complete = bool(reported) and len(costs) == len(reported)
    return AiUsageAggregateResponse(
        completed_run_count=len(runs),
        usage_reported_run_count=len(reported),
        input_tokens=token_sum("input_tokens"),
        output_tokens=token_sum("output_tokens"),
        total_tokens=token_sum("total_tokens"),
        cached_input_tokens=token_sum("cached_input_tokens"),
        estimated_cost=sum(costs) if cost_complete else None,
        cost_estimate_complete=cost_complete,
    )
