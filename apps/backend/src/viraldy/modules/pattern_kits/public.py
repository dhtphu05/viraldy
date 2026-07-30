from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.pattern_kits.contracts import PatternKitV1
from viraldy.modules.pattern_kits.repository import PatternKitRepository
from viraldy.shared.errors.base import NotFoundError


@dataclass(frozen=True, slots=True)
class PatternKitVersionSnapshot:
    pattern_kit_id: UUID
    pattern_kit_version_id: UUID
    workspace_id: UUID
    version: int
    status: str
    pattern: PatternKitV1


class PatternKitQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = PatternKitRepository(session)

    async def get_version_snapshot(
        self,
        workspace_id: UUID,
        pattern_kit_id: UUID,
        version: int | None = None,
    ) -> PatternKitVersionSnapshot:
        kit = await self._repository.get_kit(workspace_id, pattern_kit_id)
        if kit is None:
            raise NotFoundError("PATTERN_KIT_NOT_FOUND", "PatternKit was not found.")
        if version is None:
            version_model = await self._repository.get_latest_version(workspace_id, pattern_kit_id)
        else:
            version_model = await self._repository.get_version(
                workspace_id,
                pattern_kit_id,
                version,
            )
        if version_model is None:
            raise NotFoundError(
                "PATTERN_KIT_VERSION_NOT_FOUND",
                "PatternKit version was not found.",
            )
        return PatternKitVersionSnapshot(
            pattern_kit_id=kit.id,
            pattern_kit_version_id=version_model.id,
            workspace_id=workspace_id,
            version=version_model.version,
            status=kit.status,
            pattern=PatternKitV1.model_validate(version_model.pattern_json),
        )


__all__ = ["PatternKitQueries", "PatternKitV1", "PatternKitVersionSnapshot"]
