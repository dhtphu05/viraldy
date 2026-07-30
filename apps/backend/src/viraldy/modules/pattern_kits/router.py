from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.deletion.public import DeletionResourceType, DeletionService
from viraldy.modules.pattern_kits.contracts import PatternKitKindV1, PatternKitStatusV1
from viraldy.modules.pattern_kits.schemas import (
    CreatePatternKitFeedbackRequest,
    CreatePatternKitRequest,
    CreatePatternKitVersionRequest,
    PatternKitActionRequest,
)
from viraldy.modules.pattern_kits.service import PatternKitService
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.storage.s3 import S3StorageAdapter

router = APIRouter(prefix="/workspaces/{workspace_id}/pattern-kits", tags=["pattern-kits"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_pattern_kit(
    workspace_id: UUID,
    payload: CreatePatternKitRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.PATTERN_KIT_WRITE, current_user, db)
    kit = await PatternKitService(db, settings).create(
        workspace_id=workspace_id,
        user_id=current_user.id,
        data=payload,
    )
    return success(kit.model_dump(mode="json"), request_id)


@router.get("", response_model=Envelope)
async def list_pattern_kits(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    status_filter: Annotated[PatternKitStatusV1 | None, Query(alias="status")] = None,
    kind: PatternKitKindV1 | None = None,
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    platform: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    market: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    objective: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    source_creative_dna_version_id: UUID | None = None,
    created_by: UUID | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    kits = await PatternKitService(db, settings).list_kits(
        workspace_id=workspace_id,
        status=status_filter,
        kind=kind,
        category=category,
        platform=platform,
        market=market,
        objective=objective,
        source_creative_dna_version_id=source_creative_dna_version_id,
        created_by=created_by,
        search=search,
        limit=limit,
    )
    return success([kit.model_dump(mode="json") for kit in kits], request_id)


@router.get("/{pattern_kit_id}", response_model=Envelope)
async def get_pattern_kit(
    workspace_id: UUID,
    pattern_kit_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    kit = await PatternKitService(db, settings).get(workspace_id, pattern_kit_id)
    return success(kit.model_dump(mode="json"), request_id)


@router.get("/{pattern_kit_id}/versions", response_model=Envelope)
async def list_pattern_kit_versions(
    workspace_id: UUID,
    pattern_kit_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    versions = await PatternKitService(db, settings).list_versions(workspace_id, pattern_kit_id)
    return success([version.model_dump(mode="json") for version in versions], request_id)


@router.get("/{pattern_kit_id}/versions/{version}", response_model=Envelope)
async def get_pattern_kit_version(
    workspace_id: UUID,
    pattern_kit_id: UUID,
    version: int,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    pattern_version = await PatternKitService(db, settings).get_version(
        workspace_id,
        pattern_kit_id,
        version,
    )
    return success(pattern_version.model_dump(mode="json"), request_id)


@router.post(
    "/{pattern_kit_id}/versions",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def create_pattern_kit_version(
    workspace_id: UUID,
    pattern_kit_id: UUID,
    payload: CreatePatternKitVersionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.PATTERN_KIT_WRITE, current_user, db)
    version = await PatternKitService(db, settings).create_version(
        workspace_id=workspace_id,
        pattern_kit_id=pattern_kit_id,
        user_id=current_user.id,
        data=payload,
    )
    return success(version.model_dump(mode="json"), request_id)


@router.post(
    "/{pattern_kit_id}/actions",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def record_pattern_kit_action(
    workspace_id: UUID,
    pattern_kit_id: UUID,
    payload: PatternKitActionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.PATTERN_KIT_WRITE, current_user, db)
    action = await PatternKitService(db, settings).record_action(
        workspace_id=workspace_id,
        pattern_kit_id=pattern_kit_id,
        user_id=current_user.id,
        data=payload,
    )
    return success(action.model_dump(mode="json"), request_id)


@router.post(
    "/{pattern_kit_id}/feedback",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def create_pattern_kit_feedback(
    workspace_id: UUID,
    pattern_kit_id: UUID,
    payload: CreatePatternKitFeedbackRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.FEEDBACK_WRITE, current_user, db)
    feedback = await PatternKitService(db, settings).create_feedback(
        workspace_id=workspace_id,
        pattern_kit_id=pattern_kit_id,
        user_id=current_user.id,
        data=payload,
    )
    return success(feedback.model_dump(mode="json"), request_id)


@router.delete("/{pattern_kit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pattern_kit(
    workspace_id: UUID,
    pattern_kit_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
) -> Response:
    await require_workspace_permission(workspace_id, Permission.DATA_DELETE, current_user, db)
    await DeletionService(db, S3StorageAdapter(settings)).delete(
        workspace_id=workspace_id,
        resource_type=DeletionResourceType.PATTERN_KIT,
        resource_id=pattern_kit_id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
