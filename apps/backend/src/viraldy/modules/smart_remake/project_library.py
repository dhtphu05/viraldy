"""Workspace gallery of retained Smart Remake output videos."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import cast, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONPATH
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings

from .analysis_progress import public_analysis_progress
from .budget_models import SmartRemakeAttemptModel
from .generation_progress import generation_progress
from .intake_router import service_for
from .models import SmartRemakeOperationModel, SmartRemakeProjectModel
from .repair_media import RepairMediaStore

router = APIRouter()
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def _project_videos(state: dict[str, Any], media: RepairMediaStore) -> list[dict[str, Any]]:
    videos = []
    retained_keys: set[str] = set()
    final_key = state.get("finalStorageKey")
    if final_key:
        videos.append(
            {
                "id": "final",
                "label": "Video hoàn chỉnh",
                "kind": "final",
                "url": await media.url(final_key),
                "durationSeconds": state["targetDuration"],
            }
        )
        retained_keys.add(final_key)
    clip_count = 0
    for scene in state.get("scenes", []):
        for version in scene.get("versions", []):
            key = version.get("storageKey")
            if not isinstance(key, str) or not key or key in retained_keys:
                continue
            clip_count += 1
            frames = version.get("frameCount") or version.get("rawDurationFrames") or 192
            videos.append(
                {
                    "id": version["id"],
                    "label": f"Clip {clip_count}",
                    "kind": "clip",
                    "url": await media.url(key),
                    "durationSeconds": frames / 24,
                }
            )
            retained_keys.add(key)
    return videos


def _project_activity(
    row: Any, operations: Sequence[Any], attempts: Sequence[Any]
) -> dict[str, Any]:
    owned = [operation for operation in operations if operation.project_id == row.id]
    operation = next((value for value in owned if value.status == "running"), None)
    if operation is None:
        operation = next(
            (
                value
                for value in owned
                if value.result_json.get("kind")
                in {
                    "compile",
                    "render",
                    "repair",
                    "inspection",
                    "compose",
                }
            ),
            None,
        )
    if operation is None:
        return {"status": "not_started", "kind": "project"}
    result = operation.result_json or {}
    activity: dict[str, Any] = {
        "operationId": str(operation.id),
        "kind": result.get("kind"),
        "status": operation.status,
        "needsReconciliation": bool(result.get("needsReconciliation")),
    }
    if isinstance(result.get("errorCode"), str):
        code = result["errorCode"]
        if len(code) <= 120 and code.replace("_", "").isalnum():
            activity["errorCode"] = code
    if analysis := public_analysis_progress(operation):
        activity["stage"] = analysis["stage"]
    if progress := generation_progress(
        row,
        operation,
        workspace_id=row.workspace_id,
        attempts=list(attempts),
    ):
        groups = progress["groups"]
        current = next(
            (
                group
                for group in groups
                if group["stage"]
                not in {
                    "completed",
                    "queued",
                }
            ),
            groups[0],
        )
        activity.update(
            {
                "stage": current["stage"],
                "plannedVideoCount": len(groups),
                "submittedVideoCount": (
                    sum(group["videoSubmitted"] is True for group in groups)
                    if all(group["videoSubmitted"] is not None for group in groups)
                    else None
                ),
                "completedVideoCount": sum(group["stage"] == "completed" for group in groups),
            }
        )
    activity["completedImageCount"] = sum(
        isinstance(image, dict) and image.get("status") == "completed"
        for image in (result.get("images") or {}).values()
    )
    return activity


async def _project_activities(
    db: AsyncSession,
    workspace_id: UUID,
    rows: list[Any],
) -> dict[UUID, dict[str, Any]]:
    identities = [row.id for row in rows]
    operations = (
        (
            await db.execute(
                select(SmartRemakeOperationModel)
                .where(SmartRemakeOperationModel.project_id.in_(identities))
                .order_by(
                    SmartRemakeOperationModel.created_at.desc(), SmartRemakeOperationModel.id.desc()
                )
            )
        )
        .scalars()
        .all()
    )
    attempts = (
        (
            await db.execute(
                select(SmartRemakeAttemptModel).where(
                    SmartRemakeAttemptModel.project_id.in_(identities),
                    SmartRemakeAttemptModel.workspace_id == workspace_id,
                )
            )
        )
        .scalars()
        .all()
    )
    return {row.id: _project_activity(row, operations, attempts) for row in rows}


async def list_project_library(
    db: AsyncSession,
    workspace_id: UUID,
    settings: Settings,
    *,
    limit: int,
    offset: int,
    include_unfinished: bool = False,
) -> dict[str, Any]:
    model = SmartRemakeProjectModel
    policy = model.context_json["p0"]
    conditions = [
        model.workspace_id == workspace_id,
        *(
            []
            if include_unfinished
            else [
                or_(
                    func.coalesce(model.state_json["finalStorageKey"].as_string(), "") != "",
                    func.jsonb_path_exists(
                        model.state_json,
                        cast(
                            literal(
                                "$.scenes[*].versions[*].storageKey "
                                '? (@.type() == "string" && @ != "")'
                            ),
                            JSONPATH,
                        ),
                    ),
                )
            ]
        ),
        func.coalesce(policy["status"].as_string(), "").not_in(("suspended", "deleted")),
        func.coalesce(policy["deletion"]["status"].as_string(), "").in_(("", "cancelled")),
        *[
            func.coalesce(policy["rights"][role]["revoked"].as_boolean(), False).is_(False)
            for role in ("source", "product", "character", "characterConsent", "attestation")
        ],
    ]
    total = int(await db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)
    rows = (
        (
            await db.execute(
                select(model)
                .where(*conditions)
                .order_by(model.created_at.desc(), model.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    items = []
    if rows:
        activities = (
            await _project_activities(db, workspace_id, list(rows)) if include_unfinished else {}
        )
        media = service_for(db, settings, workspace_id).media
        fixture = settings.ai_mode.strip().lower() in {"fixture", "mock"}
        for row in rows:
            state, context = row.state_json, row.context_json
            videos = await _project_videos(state, media)
            created_at = row.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            item = {
                "id": str(row.id),
                "projectName": context.get("projectName") or "Smart Remake",
                "createdAt": created_at.isoformat(),
                "status": state["status"],
                "targetDuration": state["targetDuration"],
                "provider": state["provider"],
                "finalVideoUrl": next(
                    (video["url"] for video in videos if video["kind"] == "final"), ""
                ),
                "videos": videos,
            }
            if context.get("productKey"):
                item["productImageUrl"] = await media.url(context["productKey"])
            if include_unfinished:
                item["activity"] = activities[row.id]
                item["phase"] = state.get("phase")
            if state.get("finalStorageKey") and not context.get("p0") and fixture:
                item["downloadUrl"] = await media.download_url(
                    state["finalStorageKey"], f"smart-remake-{row.id}.mp4"
                )
            items.append(item)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/projects", response_model=Envelope)
async def list_smart_remake_projects(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_unfinished: Annotated[bool, Query(alias="includeUnfinished")] = False,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    return success(
        await list_project_library(
            db,
            workspace_id,
            settings,
            limit=limit,
            offset=offset,
            **({"include_unfinished": True} if include_unfinished else {}),
        ),
        request_id,
    )
