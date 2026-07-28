from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.assets.public import AssetRepository
from viraldy.modules.media_analysis.repository import MediaAnalysisRepository
from viraldy.modules.media_analysis.schemas import EvidenceItemResponse, MediaArtifactResponse
from viraldy.platform.auth.policy import Permission
from viraldy.shared.errors.base import AppError, NotFoundError

router = APIRouter(
    prefix="/workspaces/{workspace_id}/assets/{asset_id}/media-analysis", tags=["media-analysis"]
)


@router.get("", response_model=Envelope)
async def get_media_analysis(
    workspace_id: UUID,
    asset_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.READ, current_user, db)
    asset = await AssetRepository(db).get(workspace_id, asset_id)
    if asset is None:
        raise NotFoundError("ASSET_NOT_FOUND", "Asset was not found.")
    version = await AssetRepository(db).get_current_version(asset_id)
    if version is None:
        raise AppError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
    repository = MediaAnalysisRepository(db)
    artifacts = await repository.list_artifacts(workspace_id, version.id)
    evidence = await repository.list_evidence(workspace_id, version.id)
    return success(
        {
            "asset_version_id": str(version.id),
            "artifacts": [
                MediaArtifactResponse.model_validate(artifact).model_dump(mode="json")
                for artifact in artifacts
            ],
            "evidence": [
                EvidenceItemResponse.model_validate(item).model_dump(mode="json")
                for item in evidence
            ],
        },
        request_id,
    )
