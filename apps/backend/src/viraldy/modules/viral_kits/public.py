from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.viral_kits.contracts import (
    GenerationBriefV1,
    GenerationSceneV1,
    ViralKitV1,
)
from viraldy.modules.viral_kits.repository import ViralKitRepository
from viraldy.shared.errors.base import NotFoundError


@dataclass(frozen=True, slots=True)
class ViralKitVersionSnapshot:
    viral_kit_id: UUID
    viral_kit_version_id: UUID
    workspace_id: UUID
    version: int
    status: str
    viral_kit: ViralKitV1


class ViralKitQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = ViralKitRepository(session)

    async def get_version_snapshot(
        self,
        workspace_id: UUID,
        viral_kit_id: UUID,
        version: int | None = None,
    ) -> ViralKitVersionSnapshot:
        kit = await self._repository.get_kit(workspace_id, viral_kit_id)
        if kit is None:
            raise NotFoundError("VIRAL_KIT_NOT_FOUND", "ViralKit was not found.")
        if version is None:
            version_model = await self._repository.get_latest_version(workspace_id, viral_kit_id)
        else:
            version_model = await self._repository.get_version(
                workspace_id,
                viral_kit_id,
                version,
            )
        if version_model is None:
            raise NotFoundError("VIRAL_KIT_VERSION_NOT_FOUND", "ViralKit version was not found.")
        return ViralKitVersionSnapshot(
            viral_kit_id=kit.id,
            viral_kit_version_id=version_model.id,
            workspace_id=workspace_id,
            version=version_model.version,
            status=kit.status,
            viral_kit=ViralKitV1.model_validate(version_model.viral_kit_json),
        )

    async def get_version_snapshot_by_id(
        self,
        workspace_id: UUID,
        viral_kit_version_id: UUID,
    ) -> ViralKitVersionSnapshot:
        version_model = await self._repository.get_version_by_id(
            workspace_id,
            viral_kit_version_id,
        )
        if version_model is None:
            raise NotFoundError("VIRAL_KIT_VERSION_NOT_FOUND", "ViralKit version was not found.")
        kit = await self._repository.get_kit(workspace_id, version_model.viral_kit_id)
        if kit is None:
            raise NotFoundError("VIRAL_KIT_NOT_FOUND", "ViralKit was not found.")
        return ViralKitVersionSnapshot(
            viral_kit_id=kit.id,
            viral_kit_version_id=version_model.id,
            workspace_id=workspace_id,
            version=version_model.version,
            status=kit.status,
            viral_kit=ViralKitV1.model_validate(version_model.viral_kit_json),
        )


__all__ = [
    "GenerationBriefV1",
    "GenerationSceneV1",
    "ViralKitQueries",
    "ViralKitV1",
    "ViralKitVersionSnapshot",
]
