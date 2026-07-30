from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.deletion.public import DeletionResourceType, DeletionService
from viraldy.modules.viral_kits.contracts import (
    ViralKitObjectiveV1,
    ViralKitPlatformV1,
    ViralKitStatusV1,
)
from viraldy.modules.viral_kits.schemas import (
    CreateViralKitCampaignPackRequest,
    CreateViralKitFeedbackRequest,
    CreateViralKitRequest,
    CreateViralKitVersionRequest,
    ViralKitConceptActionRequest,
)
from viraldy.modules.viral_kits.service import ViralKitService
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.storage.s3 import S3StorageAdapter

router = APIRouter(prefix="/workspaces/{workspace_id}/viral-kits", tags=["viral-kits"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_viral_kit(
    workspace_id: UUID,
    payload: CreateViralKitRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.VIRAL_KIT_WRITE, current_user, db)
    kit = await ViralKitService(db, settings).create(
        workspace_id=workspace_id,
        user_id=current_user.id,
        data=payload,
    )
    return success(kit.model_dump(mode="json"), request_id)


@router.get("", response_model=Envelope)
async def list_viral_kits(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    status_filter: Annotated[ViralKitStatusV1 | None, Query(alias="status")] = None,
    product_id: UUID | None = None,
    objective: ViralKitObjectiveV1 | None = None,
    platform: ViralKitPlatformV1 | None = None,
    target_market: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    created_by: UUID | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    kits = await ViralKitService(db, settings).list_kits(
        workspace_id=workspace_id,
        status=status_filter,
        product_id=product_id,
        objective=objective,
        platform=platform,
        target_market=target_market,
        created_by=created_by,
        search=search,
        limit=limit,
    )
    return success([kit.model_dump(mode="json") for kit in kits], request_id)


@router.get("/{viral_kit_id}", response_model=Envelope)
async def get_viral_kit(
    workspace_id: UUID,
    viral_kit_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    kit = await ViralKitService(db, settings).get(workspace_id, viral_kit_id)
    return success(kit.model_dump(mode="json"), request_id)


@router.get("/{viral_kit_id}/versions", response_model=Envelope)
async def list_viral_kit_versions(
    workspace_id: UUID,
    viral_kit_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    versions = await ViralKitService(db, settings).list_versions(workspace_id, viral_kit_id)
    return success([version.model_dump(mode="json") for version in versions], request_id)


@router.get("/{viral_kit_id}/versions/{version}", response_model=Envelope)
async def get_viral_kit_version(
    workspace_id: UUID,
    viral_kit_id: UUID,
    version: int,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    viral_version = await ViralKitService(db, settings).get_version(
        workspace_id,
        viral_kit_id,
        version,
    )
    return success(viral_version.model_dump(mode="json"), request_id)


@router.post(
    "/{viral_kit_id}/versions",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def create_viral_kit_version(
    workspace_id: UUID,
    viral_kit_id: UUID,
    payload: CreateViralKitVersionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.VIRAL_KIT_WRITE, current_user, db)
    version = await ViralKitService(db, settings).create_version(
        workspace_id=workspace_id,
        viral_kit_id=viral_kit_id,
        user_id=current_user.id,
        data=payload,
    )
    return success(version.model_dump(mode="json"), request_id)


@router.post(
    "/{viral_kit_id}/concept-actions",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def record_viral_kit_concept_action(
    workspace_id: UUID,
    viral_kit_id: UUID,
    payload: ViralKitConceptActionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.VIRAL_KIT_WRITE, current_user, db)
    action = await ViralKitService(db, settings).record_concept_action(
        workspace_id=workspace_id,
        viral_kit_id=viral_kit_id,
        user_id=current_user.id,
        data=payload,
    )
    return success(action.model_dump(mode="json"), request_id)


@router.post(
    "/{viral_kit_id}/concepts/{concept_id}/campaign-pack",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def create_campaign_pack_from_viral_kit_concept(
    workspace_id: UUID,
    viral_kit_id: UUID,
    concept_id: str,
    payload: CreateViralKitCampaignPackRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.CAMPAIGN_PACK_WRITE,
        current_user,
        db,
    )
    pack = await ViralKitService(db, settings).create_campaign_pack_from_concept(
        workspace_id=workspace_id,
        viral_kit_id=viral_kit_id,
        user_id=current_user.id,
        concept_id=concept_id,
        data=payload,
    )
    return success(pack.model_dump(mode="json"), request_id)


@router.post(
    "/{viral_kit_id}/feedback",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def create_viral_kit_feedback(
    workspace_id: UUID,
    viral_kit_id: UUID,
    payload: CreateViralKitFeedbackRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.FEEDBACK_WRITE, current_user, db)
    feedback = await ViralKitService(db, settings).create_feedback(
        workspace_id=workspace_id,
        viral_kit_id=viral_kit_id,
        user_id=current_user.id,
        data=payload,
    )
    return success(feedback.model_dump(mode="json"), request_id)


@router.delete("/{viral_kit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_viral_kit(
    workspace_id: UUID,
    viral_kit_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
) -> Response:
    await require_workspace_permission(workspace_id, Permission.DATA_DELETE, current_user, db)
    await DeletionService(db, S3StorageAdapter(settings)).delete(
        workspace_id=workspace_id,
        resource_type=DeletionResourceType.VIRAL_KIT,
        resource_id=viral_kit_id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
