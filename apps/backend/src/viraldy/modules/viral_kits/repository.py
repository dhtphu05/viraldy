from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.viral_kits.contracts import ViralKitV1
from viraldy.modules.viral_kits.models import (
    ViralKitCampaignPackLinkModel,
    ViralKitConceptActionModel,
    ViralKitModel,
    ViralKitPatternLinkModel,
    ViralKitVersionModel,
)
from viraldy.platform.clock.utc import utc_now


class ViralKitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_with_version(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        viral_kit: ViralKitV1,
    ) -> tuple[ViralKitModel, ViralKitVersionModel]:
        kit = ViralKitModel(
            id=viral_kit.id,
            workspace_id=workspace_id,
            product_id=viral_kit.product.product_id,
            name=viral_kit.name,
            objective=viral_kit.objective,
            platform=viral_kit.platform,
            target_market=viral_kit.target_market,
            status=viral_kit.status,
            latest_version=viral_kit.version,
            selected_concept_id=viral_kit.selected_concept_id,
            created_by_user_id=user_id,
        )
        self._session.add(kit)
        await self._session.flush()
        version = await self._create_version_row(
            kit=kit,
            user_id=user_id,
            viral_kit=viral_kit,
            parent_version=None,
            change_reason=None,
        )
        await self._replace_pattern_links(workspace_id, version.id, viral_kit)
        return kit, version

    async def list_kits(
        self,
        *,
        workspace_id: UUID,
        status: str | None = None,
        product_id: UUID | None = None,
        objective: str | None = None,
        platform: str | None = None,
        target_market: str | None = None,
        created_by: UUID | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[ViralKitModel]:
        statement = select(ViralKitModel).where(ViralKitModel.workspace_id == workspace_id)
        if status is None:
            statement = statement.where(ViralKitModel.status != "archived")
        else:
            statement = statement.where(ViralKitModel.status == status)
        if product_id is not None:
            statement = statement.where(ViralKitModel.product_id == product_id)
        if objective is not None:
            statement = statement.where(ViralKitModel.objective == objective)
        if platform is not None:
            statement = statement.where(ViralKitModel.platform == platform)
        if target_market is not None:
            statement = statement.where(ViralKitModel.target_market == target_market)
        if created_by is not None:
            statement = statement.where(ViralKitModel.created_by_user_id == created_by)
        if search is not None:
            statement = statement.where(ViralKitModel.name.ilike(f"%{search}%"))
        result = await self._session.execute(
            statement.order_by(ViralKitModel.created_at.desc()).limit(limit)
        )
        return list(result.scalars())

    async def get_kit(self, workspace_id: UUID, viral_kit_id: UUID) -> ViralKitModel | None:
        result = await self._session.execute(
            select(ViralKitModel).where(
                ViralKitModel.workspace_id == workspace_id,
                ViralKitModel.id == viral_kit_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version(
        self,
        workspace_id: UUID,
        viral_kit_id: UUID,
    ) -> ViralKitVersionModel | None:
        result = await self._session.execute(
            select(ViralKitVersionModel)
            .where(
                ViralKitVersionModel.workspace_id == workspace_id,
                ViralKitVersionModel.viral_kit_id == viral_kit_id,
            )
            .order_by(ViralKitVersionModel.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        workspace_id: UUID,
        viral_kit_id: UUID,
    ) -> list[ViralKitVersionModel]:
        result = await self._session.execute(
            select(ViralKitVersionModel)
            .where(
                ViralKitVersionModel.workspace_id == workspace_id,
                ViralKitVersionModel.viral_kit_id == viral_kit_id,
            )
            .order_by(ViralKitVersionModel.version.desc())
        )
        return list(result.scalars())

    async def get_version(
        self,
        workspace_id: UUID,
        viral_kit_id: UUID,
        version: int,
    ) -> ViralKitVersionModel | None:
        result = await self._session.execute(
            select(ViralKitVersionModel).where(
                ViralKitVersionModel.workspace_id == workspace_id,
                ViralKitVersionModel.viral_kit_id == viral_kit_id,
                ViralKitVersionModel.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def get_version_by_id(
        self,
        workspace_id: UUID,
        viral_kit_version_id: UUID,
    ) -> ViralKitVersionModel | None:
        result = await self._session.execute(
            select(ViralKitVersionModel).where(
                ViralKitVersionModel.workspace_id == workspace_id,
                ViralKitVersionModel.id == viral_kit_version_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_version(
        self,
        *,
        kit: ViralKitModel,
        user_id: UUID,
        viral_kit: ViralKitV1,
        parent_version: int,
        change_reason: str,
    ) -> ViralKitVersionModel:
        kit.latest_version = parent_version + 1
        kit.name = viral_kit.name
        kit.objective = viral_kit.objective
        kit.platform = viral_kit.platform
        kit.target_market = viral_kit.target_market
        kit.status = viral_kit.status
        kit.selected_concept_id = viral_kit.selected_concept_id
        version = await self._create_version_row(
            kit=kit,
            user_id=user_id,
            viral_kit=viral_kit,
            parent_version=parent_version,
            change_reason=change_reason,
        )
        await self._replace_pattern_links(kit.workspace_id, version.id, viral_kit)
        await self._session.flush()
        return version

    async def record_concept_action(
        self,
        *,
        kit: ViralKitModel,
        concept_id: str,
        action: str,
        reason: str | None,
        actor_user_id: UUID,
    ) -> ViralKitConceptActionModel:
        if action == "selected":
            kit.selected_concept_id = concept_id
            kit.status = "concept_selected"
        elif action == "restored" and kit.selected_concept_id == concept_id:
            kit.selected_concept_id = None
            kit.status = "ready_for_review"
        row = ViralKitConceptActionModel(
            workspace_id=kit.workspace_id,
            viral_kit_id=kit.id,
            viral_kit_version=kit.latest_version,
            concept_id=concept_id,
            action=action,
            reason=reason,
            actor_user_id=actor_user_id,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def record_campaign_pack_link(
        self,
        *,
        workspace_id: UUID,
        viral_kit_version_id: UUID,
        concept_id: str,
        campaign_pack_id: UUID,
        campaign_pack_version_id: UUID,
    ) -> ViralKitCampaignPackLinkModel:
        row = ViralKitCampaignPackLinkModel(
            workspace_id=workspace_id,
            viral_kit_version_id=viral_kit_version_id,
            concept_id=concept_id,
            campaign_pack_id=campaign_pack_id,
            campaign_pack_version_id=campaign_pack_version_id,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def archive(self, kit: ViralKitModel) -> None:
        kit.status = "archived"
        kit.archived_at = utc_now()
        await self._session.flush()

    async def _create_version_row(
        self,
        *,
        kit: ViralKitModel,
        user_id: UUID,
        viral_kit: ViralKitV1,
        parent_version: int | None,
        change_reason: str | None,
    ) -> ViralKitVersionModel:
        version = ViralKitVersionModel(
            viral_kit_id=kit.id,
            workspace_id=kit.workspace_id,
            version=viral_kit.version,
            parent_version=parent_version,
            change_reason=change_reason,
            schema_version=viral_kit.schema_version,
            product_context_version=viral_kit.product.product_context_version,
            product_snapshot_json=viral_kit.product.snapshot_json.model_dump(mode="json"),
            viral_kit_json=viral_kit.model_dump(mode="json"),
            model_run_id=viral_kit.provenance.model_run_id,
            created_by_user_id=user_id,
        )
        self._session.add(version)
        await self._session.flush()
        return version

    async def _replace_pattern_links(
        self,
        workspace_id: UUID,
        viral_kit_version_id: UUID,
        viral_kit: ViralKitV1,
    ) -> None:
        for match in viral_kit.pattern_matches:
            self._session.add(
                ViralKitPatternLinkModel(
                    workspace_id=workspace_id,
                    viral_kit_version_id=viral_kit_version_id,
                    pattern_kit_version_id=match.pattern_kit_version_id,
                    match_score=match.match_score,
                    applicability_status=match.applicability_status,
                    selection_reason=match.selection_reason,
                )
            )
        await self._session.flush()
