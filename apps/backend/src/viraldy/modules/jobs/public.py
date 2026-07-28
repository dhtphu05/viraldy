from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.jobs.dispatcher import CeleryJobDispatcher
from viraldy.modules.jobs.schemas import JobResponse
from viraldy.modules.jobs.service import JobService

__all__ = ["JobResponse", "request_process_asset"]


async def request_process_asset(
    session: AsyncSession,
    workspace_id: UUID,
    asset_id: UUID,
    asset_version_id: UUID,
    idempotency_key: str | None,
) -> JobResponse:
    return await JobService(session, CeleryJobDispatcher()).request_process_asset(
        workspace_id=workspace_id,
        asset_id=asset_id,
        asset_version_id=asset_version_id,
        idempotency_key=idempotency_key,
    )
