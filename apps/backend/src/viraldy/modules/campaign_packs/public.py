from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1
from viraldy.modules.campaign_packs.repository import (
    CampaignPackRepository,
    SyncCampaignPackRepository,
)
from viraldy.modules.campaign_packs.requirements import (
    CompiledRequirementsSnapshotV2,
    CompiledRequirementV2,
    compile_campaign_requirements,
    compiled_requirements_to_json,
    parse_compiled_requirements_snapshot,
)
from viraldy.modules.campaign_packs.schemas import (
    CampaignPackResponse,
    CampaignPackVersionResponse,
)
from viraldy.shared.errors.base import AppError


@dataclass(frozen=True, slots=True)
class CampaignPackCreationResult:
    campaign_pack_id: UUID
    campaign_pack_version_id: UUID
    compiled_requirements_schema_version: str
    response: CampaignPackResponse


class CampaignPackCreator:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = CampaignPackRepository(session)

    async def create_from_brief(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        product_id: UUID,
        brief: CampaignPackBriefV1,
        source_model_run_id: UUID | None,
        source_prompt_version: str | None,
        source_schema_version: str | None,
    ) -> CampaignPackCreationResult:
        compiled = compile_campaign_requirements(brief.model_dump(mode="json"))
        compiled_payload = compiled_requirements_to_json(compiled)
        compiled_schema_version = str(compiled_payload["schema_version"])
        pack, version = await self._repository.create(
            workspace_id=workspace_id,
            user_id=user_id,
            product_id=product_id,
            adaptation_run_id=brief.source_adaptation_run_id,
            brief_json=brief.model_dump(mode="json"),
            source_model_run_id=source_model_run_id,
            source_prompt_version=source_prompt_version,
            source_schema_version=source_schema_version,
            product_snapshot_json=brief.product_snapshot.model_dump(mode="json"),
            compiled_requirements_json=compiled_payload,
            requirements_schema_version=compiled_schema_version,
        )
        version_response = CampaignPackVersionResponse.model_validate(version)
        return CampaignPackCreationResult(
            campaign_pack_id=pack.id,
            campaign_pack_version_id=version.id,
            compiled_requirements_schema_version=compiled_schema_version,
            response=CampaignPackResponse.model_validate(
                {
                    "id": pack.id,
                    "workspace_id": pack.workspace_id,
                    "product_id": pack.product_id,
                    "adaptation_run_id": pack.adaptation_run_id,
                    "status": pack.status,
                    "current_version_id": pack.current_version_id,
                    "created_at": pack.created_at,
                    "updated_at": pack.updated_at,
                    "current_version": version_response,
                }
            ),
        )


def get_compiled_requirements(pack_version: Any) -> list[CompiledRequirementV2]:
    payload = getattr(pack_version, "compiled_requirements_json", None)
    if not isinstance(payload, dict) or not isinstance(payload.get("requirements"), list):
        raise AppError(
            "CAMPAIGN_PACK_REQUIREMENTS_INVALID",
            "Campaign Pack version does not contain compiled requirements.",
        )
    try:
        return parse_compiled_requirements_snapshot(payload)
    except Exception as exc:
        raise AppError(
            "CAMPAIGN_PACK_REQUIREMENTS_INVALID",
            "Campaign Pack version does not contain valid compiled requirements.",
        ) from exc


def get_pack_version_snapshot(pack_version: Any) -> dict[str, object]:
    return {
        "id": str(pack_version.id),
        "brief_schema_version": pack_version.brief_schema_version,
        "brief_json": pack_version.brief_json,
        "product_snapshot_json": pack_version.product_snapshot_json,
        "compiled_requirements_json": pack_version.compiled_requirements_json,
        "requirements_schema_version": pack_version.requirements_schema_version,
    }


__all__ = [
    "CampaignPackRepository",
    "CampaignPackCreationResult",
    "CampaignPackCreator",
    "CompiledRequirementV2",
    "CompiledRequirementsSnapshotV2",
    "SyncCampaignPackRepository",
    "compile_campaign_requirements",
    "compiled_requirements_to_json",
    "get_compiled_requirements",
    "get_pack_version_snapshot",
    "parse_compiled_requirements_snapshot",
]
