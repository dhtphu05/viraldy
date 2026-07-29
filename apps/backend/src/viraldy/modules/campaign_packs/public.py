from __future__ import annotations

from typing import Any

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
from viraldy.shared.errors.base import AppError


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
    "CompiledRequirementV2",
    "CompiledRequirementsSnapshotV2",
    "SyncCampaignPackRepository",
    "compile_campaign_requirements",
    "compiled_requirements_to_json",
    "get_compiled_requirements",
    "get_pack_version_snapshot",
    "parse_compiled_requirements_snapshot",
]
