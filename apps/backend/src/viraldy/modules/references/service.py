from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.public import AssetRepository
from viraldy.modules.jobs.public import get_existing_idempotent_job, request_mvp_job
from viraldy.modules.products.public import ProductLookupPort
from viraldy.modules.reference_boards.public import ReferenceBoardRepository
from viraldy.modules.references.repository import ReferenceRepository
from viraldy.modules.references.schemas import (
    AnalyzeReferenceResponse,
    CreateReferenceRequest,
    ReferenceResponse,
)
from viraldy.shared.errors.base import AppError, NotFoundError


class ReferenceService:
    def __init__(self, session: AsyncSession, product_lookup: ProductLookupPort) -> None:
        self._session = session
        self._repository = ReferenceRepository(session)
        self._assets = AssetRepository(session)
        self._boards = ReferenceBoardRepository(session)
        self._product_lookup = product_lookup

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateReferenceRequest,
    ) -> ReferenceResponse:
        if await self._boards.get(workspace_id, data.board_id) is None:
            raise NotFoundError("REFERENCE_BOARD_NOT_FOUND", "Reference board was not found.")
        if await self._assets.get(workspace_id, data.asset_id) is None:
            raise NotFoundError("ASSET_NOT_FOUND", "Asset was not found.")
        if data.product_id and not await self._product_lookup.exists_in_workspace(
            workspace_id, data.product_id
        ):
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        reference = await self._repository.create(
            workspace_id,
            user_id,
            data.board_id,
            data.asset_id,
            data.product_id,
            data.source_platform,
            data.source_url,
            data.title,
            data.notes,
        )
        await self._session.commit()
        return ReferenceResponse.model_validate(reference)

    async def list(self, workspace_id: UUID) -> list[ReferenceResponse]:
        references = await self._repository.list(workspace_id)
        return [ReferenceResponse.model_validate(reference) for reference in references]

    async def get(self, workspace_id: UUID, reference_id: UUID) -> ReferenceResponse:
        reference = await self._repository.get(workspace_id, reference_id)
        if reference is None:
            raise NotFoundError("REFERENCE_NOT_FOUND", "Reference was not found.")
        return ReferenceResponse.model_validate(reference)

    async def analyze(
        self,
        workspace_id: UUID,
        reference_id: UUID,
        idempotency_key: str | None,
    ) -> AnalyzeReferenceResponse:
        reference = await self._repository.get(workspace_id, reference_id)
        if reference is None:
            raise NotFoundError("REFERENCE_NOT_FOUND", "Reference was not found.")
        existing_job = await get_existing_idempotent_job(
            self._session, workspace_id, "analyze_reference", idempotency_key
        )
        if existing_job is not None:
            return AnalyzeReferenceResponse(
                reference=ReferenceResponse.model_validate(reference),
                job=existing_job,
            )
        version = await self._assets.get_current_version(reference.asset_id)
        if version is None:
            raise AppError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
        await self._repository.set_status(reference, "processing")
        job = await request_mvp_job(
            self._session,
            workspace_id,
            "reference",
            reference_id,
            "analyze_reference",
            {
                "reference_id": str(reference_id),
                "asset_id": str(reference.asset_id),
                "asset_version_id": str(version.id),
            },
            idempotency_key,
        )
        return AnalyzeReferenceResponse(
            reference=ReferenceResponse.model_validate(reference), job=job
        )
