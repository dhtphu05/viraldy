"""Read durable repair acknowledgements without reconciling or submitting provider work."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import StringConstraints
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.platform.auth.policy import Permission

from .models import SmartRemakeOperationModel
from .repair_repository import RepairRepository

router = APIRouter()
RequestKey = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def _is_repair(result: dict[str, Any]) -> bool:
    if result.get("kind") == "repair":
        return True
    # Before durable KIE workflows, scene repair manifests did not retain kind.
    request = result.get("request")
    return (
        "kind" not in result
        and isinstance(result.get("sceneId"), str)
        and isinstance(request, dict)
        and "baseVersionId" in request
        and all(
            isinstance(request.get(field), str)
            for field in ("prompt", "imagePrompt", "videoPrompt")
        )
    )


def _candidate_id(
    state: dict[str, Any],
    operation: SmartRemakeOperationModel,
    scene_id: str | None,
    base_id: str | None,
) -> str | None:
    candidate_id = operation.result_json.get("candidateVersionId")
    if not isinstance(candidate_id, str) or scene_id is None:
        return None
    for scene in state.get("scenes", []):
        if scene.get("id") != scene_id:
            continue
        for version in scene.get("versions", []):
            if version.get("id") != candidate_id or version.get("parentVersionId") != base_id:
                continue
            metadata = version.get("providerMetadata") or {}
            source_operation = version.get("sourceOperationId", metadata.get("sourceOperationId"))
            if source_operation is None or source_operation == str(operation.id):
                return candidate_id
    return None


async def repair_receipt(
    db: AsyncSession,
    workspace_id: UUID,
    project_id: UUID,
    request_key: str,
) -> dict[str, Any]:
    row = await RepairRepository(db).project(workspace_id, project_id)
    operation = (
        await db.execute(
            select(SmartRemakeOperationModel)
            .where(
                SmartRemakeOperationModel.project_id == project_id,
                SmartRemakeOperationModel.idempotency_key == request_key,
            )
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if operation is None or not _is_repair(operation.result_json):
        return {"receipt": None}
    result = operation.result_json
    request = result.get("request") or {}
    scene_id = result.get("sceneId")
    base_id = request.get("baseVersionId")
    receipt = {
        "operationId": str(operation.id),
        "sceneId": scene_id if isinstance(scene_id, str) else None,
        "baseVersionId": base_id if isinstance(base_id, str) else None,
        "candidateVersionId": _candidate_id(row.state_json, operation, scene_id, base_id),
        "status": operation.status,
        "errorCode": result.get("errorCode"),
        "needsReconciliation": bool(result.get("needsReconciliation")),
    }
    normalization = result.get("repairNormalization")
    if isinstance(normalization, dict) and isinstance(normalization.get("reason"), str):
        receipt["normalizationReason"] = normalization["reason"]
    return {"receipt": receipt}


@router.get("/projects/{project_id}/repair-receipts", response_model=Envelope)
async def get_smart_remake_repair_receipt(
    workspace_id: UUID,
    project_id: UUID,
    request_key: Annotated[RequestKey, Query(alias="requestKey")],
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    return success(await repair_receipt(db, workspace_id, project_id, request_key), request_id)
