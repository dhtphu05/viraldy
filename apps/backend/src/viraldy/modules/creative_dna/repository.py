from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.creative_dna.models import CreativeDnaVersionModel


class CreativeDnaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, workspace_id: UUID, dna_version_id: UUID) -> CreativeDnaVersionModel | None:
        result = await self._session.execute(
            select(CreativeDnaVersionModel).where(
                CreativeDnaVersionModel.workspace_id == workspace_id,
                CreativeDnaVersionModel.id == dna_version_id,
            )
        )
        return result.scalar_one_or_none()

    async def latest_for_reference(
        self, workspace_id: UUID, reference_id: UUID
    ) -> CreativeDnaVersionModel | None:
        result = await self._session.execute(
            select(CreativeDnaVersionModel)
            .where(
                CreativeDnaVersionModel.workspace_id == workspace_id,
                CreativeDnaVersionModel.reference_id == reference_id,
            )
            .order_by(CreativeDnaVersionModel.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class SyncCreativeDnaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, workspace_id: UUID, dna_version_id: UUID) -> CreativeDnaVersionModel | None:
        return self._session.execute(
            select(CreativeDnaVersionModel).where(
                CreativeDnaVersionModel.workspace_id == workspace_id,
                CreativeDnaVersionModel.id == dna_version_id,
            )
        ).scalar_one_or_none()

    def latest_for_asset_version(
        self, workspace_id: UUID, asset_version_id: UUID
    ) -> CreativeDnaVersionModel | None:
        return self._session.execute(
            select(CreativeDnaVersionModel)
            .where(
                CreativeDnaVersionModel.workspace_id == workspace_id,
                CreativeDnaVersionModel.asset_version_id == asset_version_id,
            )
            .order_by(CreativeDnaVersionModel.version_number.desc())
            .limit(1)
        ).scalar_one_or_none()

    def create(
        self,
        workspace_id: UUID,
        reference_id: UUID | None,
        asset_version_id: UUID,
        dna_json: dict[str, Any],
        confidence: str,
        analysis_mode: str,
        taxonomy_version: str,
        model_version: str | None,
        prompt_version: str | None,
    ) -> CreativeDnaVersionModel:
        next_version = (
            self._session.execute(
                select(func.max(CreativeDnaVersionModel.version_number)).where(
                    CreativeDnaVersionModel.asset_version_id == asset_version_id
                )
            ).scalar_one()
            or 0
        ) + 1
        dna = CreativeDnaVersionModel(
            workspace_id=workspace_id,
            reference_id=reference_id,
            asset_version_id=asset_version_id,
            version_number=next_version,
            status="completed",
            dna_json=dna_json,
            confidence=confidence,
            analysis_mode=analysis_mode,
            taxonomy_version=taxonomy_version,
            model_version=model_version,
            prompt_version=prompt_version,
        )
        self._session.add(dna)
        self._session.flush()
        return dna
