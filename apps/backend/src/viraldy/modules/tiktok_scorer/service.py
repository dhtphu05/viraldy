from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.public import AssetRepository
from viraldy.modules.jobs.public import get_existing_idempotent_job, request_mvp_job
from viraldy.modules.tiktok_scorer.repository import TikTokScoreRepository
from viraldy.modules.tiktok_scorer.schemas import (
    CreateTikTokScoreRequest,
    CreateTikTokScoreResponse,
    TikTokScoreRunResponse,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, NotFoundError


class TikTokScoreService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repository = TikTokScoreRepository(session)
        self._assets = AssetRepository(session)

    async def create(
        self,
        workspace_id: UUID,
        data: CreateTikTokScoreRequest,
        idempotency_key: str | None,
    ) -> CreateTikTokScoreResponse:
        asset = await self._assets.get(workspace_id, data.asset_id)
        if asset is None:
            raise NotFoundError("ASSET_NOT_FOUND", "Asset was not found.")
        version = await self._assets.get_current_version_in_workspace(workspace_id, data.asset_id)
        if version is None:
            raise AppError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
        existing_job = await get_existing_idempotent_job(
            self._session, workspace_id, "score_tiktok_asset", idempotency_key
        )
        if existing_job is not None:
            run = await self._repository.get(workspace_id, existing_job.subject_id)
            if run is None:
                raise AppError(
                    "IDEMPOTENT_SCORE_RUN_NOT_FOUND",
                    "Existing idempotent score run was not found.",
                )
            return CreateTikTokScoreResponse(
                score_run=TikTokScoreRunResponse.model_validate(run),
                job=existing_job,
            )
        run = await self._repository.create_pending(
            workspace_id, version.id, self._settings.ai_mode
        )
        job = await request_mvp_job(
            self._session,
            workspace_id,
            "tiktok_score_run",
            run.id,
            "score_tiktok_asset",
            {
                "score_run_id": str(run.id),
                "asset_id": str(data.asset_id),
                "asset_version_id": str(version.id),
                "product_id": str(data.product_id) if data.product_id else None,
                "objective": data.objective,
            },
            idempotency_key,
        )
        if job.subject_id != run.id:
            existing_run = await self._repository.get(workspace_id, job.subject_id)
            if existing_run is None:
                raise AppError(
                    "IDEMPOTENT_SCORE_RUN_NOT_FOUND",
                    "Existing idempotent score run was not found.",
                )
            run = existing_run
        return CreateTikTokScoreResponse(
            score_run=TikTokScoreRunResponse.model_validate(run),
            job=job,
        )

    async def get(self, workspace_id: UUID, score_run_id: UUID) -> TikTokScoreRunResponse:
        run = await self._repository.get(workspace_id, score_run_id)
        if run is None:
            raise NotFoundError("TIKTOK_SCORE_RUN_NOT_FOUND", "TikTok score run was not found.")
        return TikTokScoreRunResponse.model_validate(run)
