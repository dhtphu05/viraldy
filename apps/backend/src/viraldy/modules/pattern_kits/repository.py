from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.pattern_kits.contracts import PatternKitV1
from viraldy.modules.pattern_kits.models import (
    PatternKitActionModel,
    PatternKitEvidenceLinkModel,
    PatternKitModel,
    PatternKitSourceModel,
    PatternKitVersionModel,
)
from viraldy.platform.clock.utc import utc_now


class PatternKitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_kit_with_version(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        pattern: PatternKitV1,
        source_rows: list[tuple[UUID, UUID]],
        evidence_links: list[tuple[UUID, str]],
    ) -> tuple[PatternKitModel, PatternKitVersionModel]:
        kit = PatternKitModel(
            id=pattern.id,
            workspace_id=workspace_id,
            name=pattern.name,
            kind=pattern.kind,
            scope=pattern.scope,
            status=pattern.status,
            primary_category=_first(pattern.applicability.suitable_categories),
            target_platforms_json=list(pattern.applicability.platforms),
            target_markets_json=list(pattern.applicability.markets),
            objectives_json=list(pattern.applicability.objectives),
            latest_version=pattern.version,
            created_by_user_id=user_id,
        )
        self._session.add(kit)
        await self._session.flush()
        version = await self._create_version_row(
            kit=kit,
            user_id=user_id,
            pattern=pattern,
            parent_version=None,
            change_reason=None,
        )
        await self._replace_version_sources(workspace_id, version.id, source_rows)
        await self._replace_version_evidence_links(workspace_id, version.id, evidence_links)
        return kit, version

    async def list_kits(
        self,
        *,
        workspace_id: UUID,
        status: str | None = None,
        kind: str | None = None,
        category: str | None = None,
        platform: str | None = None,
        market: str | None = None,
        objective: str | None = None,
        source_creative_dna_version_id: UUID | None = None,
        created_by: UUID | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[PatternKitModel]:
        statement = select(PatternKitModel).where(PatternKitModel.workspace_id == workspace_id)
        if status is None:
            statement = statement.where(PatternKitModel.status != "archived")
        else:
            statement = statement.where(PatternKitModel.status == status)
        if kind is not None:
            statement = statement.where(PatternKitModel.kind == kind)
        if category is not None:
            statement = statement.where(PatternKitModel.primary_category == category)
        if platform is not None:
            statement = statement.where(PatternKitModel.target_platforms_json.contains([platform]))
        if market is not None:
            statement = statement.where(PatternKitModel.target_markets_json.contains([market]))
        if objective is not None:
            statement = statement.where(PatternKitModel.objectives_json.contains([objective]))
        if created_by is not None:
            statement = statement.where(PatternKitModel.created_by_user_id == created_by)
        if search is not None:
            statement = statement.where(PatternKitModel.name.ilike(f"%{search}%"))
        if source_creative_dna_version_id is not None:
            statement = (
                statement.join(
                    PatternKitVersionModel,
                    PatternKitVersionModel.pattern_kit_id == PatternKitModel.id,
                )
                .join(
                    PatternKitSourceModel,
                    PatternKitSourceModel.pattern_kit_version_id == PatternKitVersionModel.id,
                )
                .where(
                    PatternKitSourceModel.creative_dna_version_id
                    == source_creative_dna_version_id
                )
                .distinct()
            )
        result = await self._session.execute(
            statement.order_by(PatternKitModel.created_at.desc()).limit(limit)
        )
        return list(result.scalars())

    async def get_kit(self, workspace_id: UUID, pattern_kit_id: UUID) -> PatternKitModel | None:
        result = await self._session.execute(
            select(PatternKitModel).where(
                PatternKitModel.workspace_id == workspace_id,
                PatternKitModel.id == pattern_kit_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version(
        self, workspace_id: UUID, pattern_kit_id: UUID
    ) -> PatternKitVersionModel | None:
        result = await self._session.execute(
            select(PatternKitVersionModel)
            .where(
                PatternKitVersionModel.workspace_id == workspace_id,
                PatternKitVersionModel.pattern_kit_id == pattern_kit_id,
            )
            .order_by(PatternKitVersionModel.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self, workspace_id: UUID, pattern_kit_id: UUID
    ) -> list[PatternKitVersionModel]:
        result = await self._session.execute(
            select(PatternKitVersionModel)
            .where(
                PatternKitVersionModel.workspace_id == workspace_id,
                PatternKitVersionModel.pattern_kit_id == pattern_kit_id,
            )
            .order_by(PatternKitVersionModel.version.desc())
        )
        return list(result.scalars())

    async def get_version(
        self,
        workspace_id: UUID,
        pattern_kit_id: UUID,
        version: int,
    ) -> PatternKitVersionModel | None:
        result = await self._session.execute(
            select(PatternKitVersionModel).where(
                PatternKitVersionModel.workspace_id == workspace_id,
                PatternKitVersionModel.pattern_kit_id == pattern_kit_id,
                PatternKitVersionModel.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def get_version_by_id(
        self,
        workspace_id: UUID,
        pattern_kit_version_id: UUID,
    ) -> PatternKitVersionModel | None:
        result = await self._session.execute(
            select(PatternKitVersionModel).where(
                PatternKitVersionModel.workspace_id == workspace_id,
                PatternKitVersionModel.id == pattern_kit_version_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_sources_for_version(
        self,
        workspace_id: UUID,
        pattern_kit_version_id: UUID,
    ) -> list[PatternKitSourceModel]:
        result = await self._session.execute(
            select(PatternKitSourceModel)
            .where(
                PatternKitSourceModel.workspace_id == workspace_id,
                PatternKitSourceModel.pattern_kit_version_id == pattern_kit_version_id,
            )
            .order_by(PatternKitSourceModel.source_order.asc())
        )
        return list(result.scalars())

    async def create_version(
        self,
        *,
        kit: PatternKitModel,
        user_id: UUID,
        pattern: PatternKitV1,
        parent_version: int,
        change_reason: str,
        source_rows: list[tuple[UUID, UUID]],
        evidence_links: list[tuple[UUID, str]],
    ) -> PatternKitVersionModel:
        kit.latest_version = parent_version + 1
        kit.name = pattern.name
        kit.kind = pattern.kind
        kit.scope = pattern.scope
        kit.status = pattern.status
        kit.primary_category = _first(pattern.applicability.suitable_categories)
        kit.target_platforms_json = list(pattern.applicability.platforms)
        kit.target_markets_json = list(pattern.applicability.markets)
        kit.objectives_json = list(pattern.applicability.objectives)
        version = await self._create_version_row(
            kit=kit,
            user_id=user_id,
            pattern=pattern,
            parent_version=parent_version,
            change_reason=change_reason,
        )
        await self._replace_version_sources(kit.workspace_id, version.id, source_rows)
        await self._replace_version_evidence_links(kit.workspace_id, version.id, evidence_links)
        await self._session.flush()
        return version

    async def record_action(
        self,
        *,
        kit: PatternKitModel,
        version: int,
        action: str,
        reason: str | None,
        actor_user_id: UUID,
    ) -> PatternKitActionModel:
        if action == "archived":
            kit.status = "archived"
            kit.archived_at = utc_now()
        elif action == "restored":
            kit.status = "candidate"
            kit.archived_at = None
        elif action in {"reviewed", "validated", "deprecated"}:
            kit.status = action
        action_row = PatternKitActionModel(
            workspace_id=kit.workspace_id,
            pattern_kit_id=kit.id,
            version=version,
            action=action,
            reason=reason,
            actor_user_id=actor_user_id,
        )
        self._session.add(action_row)
        await self._session.flush()
        return action_row

    async def archive(self, kit: PatternKitModel, actor_user_id: UUID) -> PatternKitActionModel:
        return await self.record_action(
            kit=kit,
            version=kit.latest_version,
            action="archived",
            reason="Deleted by user.",
            actor_user_id=actor_user_id,
        )

    async def _create_version_row(
        self,
        *,
        kit: PatternKitModel,
        user_id: UUID,
        pattern: PatternKitV1,
        parent_version: int | None,
        change_reason: str | None,
    ) -> PatternKitVersionModel:
        version = PatternKitVersionModel(
            pattern_kit_id=kit.id,
            workspace_id=kit.workspace_id,
            version=pattern.version,
            parent_version=parent_version,
            change_reason=change_reason,
            schema_version=pattern.schema_version,
            pattern_json=pattern.model_dump(mode="json"),
            overall_confidence=pattern.overall_confidence,
            model_run_id=pattern.provenance.model_run_id,
            created_by_user_id=user_id,
        )
        self._session.add(version)
        await self._session.flush()
        return version

    async def _replace_version_sources(
        self,
        workspace_id: UUID,
        version_id: UUID,
        source_rows: list[tuple[UUID, UUID]],
    ) -> None:
        for index, (creative_dna_version_id, asset_version_id) in enumerate(source_rows, start=1):
            self._session.add(
                PatternKitSourceModel(
                    workspace_id=workspace_id,
                    pattern_kit_version_id=version_id,
                    creative_dna_version_id=creative_dna_version_id,
                    asset_version_id=asset_version_id,
                    source_order=index,
                )
            )
        await self._session.flush()

    async def _replace_version_evidence_links(
        self,
        workspace_id: UUID,
        version_id: UUID,
        evidence_links: list[tuple[UUID, str]],
    ) -> None:
        seen: set[tuple[UUID, str]] = set()
        for evidence_id, feature_path in evidence_links:
            key = (evidence_id, feature_path)
            if key in seen:
                continue
            seen.add(key)
            self._session.add(
                PatternKitEvidenceLinkModel(
                    workspace_id=workspace_id,
                    pattern_kit_version_id=version_id,
                    evidence_id=evidence_id,
                    feature_path=feature_path,
                )
            )
        await self._session.flush()

    async def count_actions(
        self,
        workspace_id: UUID,
        pattern_kit_id: UUID,
    ) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(PatternKitActionModel)
            .where(
                PatternKitActionModel.workspace_id == workspace_id,
                PatternKitActionModel.pattern_kit_id == pattern_kit_id,
            )
        )
        return int(result.scalar_one())


def _first(values: list[str]) -> str | None:
    return values[0] if values else None
