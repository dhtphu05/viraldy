"""Durable, provider-free whole-video previews after retained generation completes."""

from __future__ import annotations

import copy
import logging
import re
from typing import Any
from uuid import UUID

from viraldy.shared.errors.base import AppError

from .assembly_snapshots import assembly_manifest, content_hash
from .project_policy import constraints_hash, policy_hash
from .repair_schemas import PublishTimelineRequest

logger = logging.getLogger(__name__)


def preview_snapshot_hash(row: Any) -> str:
    from .timeline_media import validate_trim

    state = row.state_json
    timeline = state["draftTimeline"]
    for item in timeline["items"]:
        scene = next(value for value in state["scenes"] if value["id"] == item["renderUnitId"])
        version = next(value for value in scene["versions"] if value["id"] == item["versionId"])
        if (
            scene["activeVersionId"] != version["id"]
            or version["technicalCheck"]["status"] != "passed"
        ):
            raise AppError(
                "SMART_REMAKE_TECHNICAL_CHECK_FAILED", "Preview needs accepted ready clips."
            )
        validate_trim(item, version.get("frameCount", version.get("rawDurationFrames", 192)))
    return content_hash(
        {
            "manifest": assembly_manifest(timeline, state),
            "constraintsHash": constraints_hash(row.context_json),
            "policyHash": policy_hash(row.context_json),
        }
    )


def update_project_preview(row: Any, **updates: Any) -> None:
    """Caller commits this copied context with its existing operation transaction."""
    if not row.context_json.get("p0"):
        return
    context = copy.deepcopy(row.context_json)
    context["p0"]["preview"] = {**context["p0"].get("preview", {}), **updates}
    row.context_json = context


def mark_automatic_preview(row: Any, operation: Any) -> bool:
    plan, p0 = row.context_json.get("renderPlan", {}), row.context_json.get("p0", {})
    groups = plan.get("groups", [])
    if (
        not p0.get("inputHash")
        or row.state_json.get("targetDuration") != 12
        or plan.get("videoModel") != "wan/3-0-video"
        or plan.get("audioRequired") is not True
        or len(groups) != 2
        or any(group.get("rawDurationFrames") != 144 for group in groups)
    ):
        return False
    tasks = operation.result_json.get("tasks", {})
    try:
        snapshot_hash = preview_snapshot_hash(row)
        for scene in row.state_json["scenes"]:
            version = next(
                value for value in scene["versions"] if value["id"] == scene["activeVersionId"]
            )
            metadata = version.get("providerMetadata", {})
            task = tasks[f"group:{metadata['renderGroupId']}"]
            if not task.get("taskId") or metadata.get("providerRequestId") != task["taskId"]:
                return False
    except (AppError, KeyError, StopIteration, TypeError, ValueError):
        return False
    current = p0.get("preview", {})
    if (
        current.get("sourceRenderOperationId") == str(operation.id)
        and current.get("snapshotHash") == snapshot_hash
    ):
        return False
    update_project_preview(
        row,
        schemaVersion=1,
        status="pending",
        sourceRenderOperationId=str(operation.id),
        snapshotHash=snapshot_hash,
        requestKey=f"preview:{operation.id}:{snapshot_hash}",
        revision=row.state_json["revision"],
        operationId=None,
        assemblyId=None,
        errorCode=None,
    )
    return True


def mark_accepted_group_preview(row: Any, state: dict[str, Any], operation: Any) -> bool:
    """Commit the free recomposition intent with the atomic candidate acceptance."""
    from types import SimpleNamespace

    if not row.context_json.get("p0", {}).get("inputHash"):
        return False
    try:
        snapshot_hash = preview_snapshot_hash(SimpleNamespace(
            state_json=state, context_json=row.context_json,
        ))
    except (AppError, KeyError, StopIteration, TypeError, ValueError):
        # Accepting a good candidate does not depend on the other clip being ready.
        return False
    update_project_preview(
        row, schemaVersion=1, status="pending",
        # This persisted key identifies the source mutation, including group acceptance.
        sourceRenderOperationId=str(operation.id), snapshotHash=snapshot_hash,
        requestKey=f"preview:{operation.id}:{snapshot_hash}", revision=state["revision"],
        operationId=None, assemblyId=None, errorCode=None,
    )
    return True


async def queue_automatic_preview(service: Any, row: Any, operation: Any) -> None:
    """Worker-only handoff; reads and polling never call this function."""
    marker = (row.context_json.get("p0") or {}).get("preview", {})
    if (
        operation.status != "completed"
        or marker.get("status") not in {"pending", "processing"}
        or marker.get("sourceRenderOperationId") != str(operation.id)
    ):
        return
    try:
        current = await service.repository.project(service.workspace_id, row.id, lock=True)
        saved = (current.context_json.get("p0") or {}).get("preview", {})
        if saved.get("requestKey") != marker.get("requestKey") or saved.get("status") not in {
            "pending",
            "processing",
        }:
            return
        if preview_snapshot_hash(current) != marker["snapshotHash"]:
            update_project_preview(current, status="stale")
            await service.repository.finish(operation, "completed", operation.result_json)
            return
        actor_id = operation.result_json.get("actorId") or current.context_json["p0"]["actorId"]
        from .timeline_service import enqueue_publish

        await enqueue_publish(
            service.repository.session,
            service.settings,
            service.workspace_id,
            row.id,
            PublishTimelineRequest(
                expectedRevision=marker["revision"],
                idempotencyKey=marker["requestKey"],
                reviewMode="whole_video",
            ),
            actor_id=UUID(actor_id),
        )
    except Exception as exc:
        try:
            current = await service.repository.project(service.workspace_id, row.id, lock=True)
            saved = (current.context_json.get("p0") or {}).get("preview", {})
            if (
                saved.get("snapshotHash") == marker.get("snapshotHash")
                and saved.get("status") != "ready"
            ):
                update_project_preview(
                    current,
                    status="failed",
                    errorCode=getattr(exc, "code", "SMART_REMAKE_PREVIEW_FAILED"),
                )
                # A local failure never turns completed, billed generation into a retry.
                await service.repository.finish(operation, "completed", operation.result_json)
        except Exception:
            logger.exception(
                "Local preview status could not be retained; paid generation is complete"
            )


def public_project_preview(row: Any) -> dict[str, Any] | None:
    marker = (row.context_json.get("p0") or {}).get("preview")
    if not isinstance(marker, dict):
        return None
    status = marker.get("status", "failed")
    if status not in {"pending", "processing", "ready", "failed", "stale"}:
        status = "failed"
    try:
        if marker.get("snapshotHash") != preview_snapshot_hash(row):
            status = "stale"
        if status == "ready" and marker.get("assemblyId") != (
            row.context_json.get("p0", {}).get("assemblies", {}).get("activeAssemblyId")
        ):
            status = "stale"
    except (AppError, KeyError, StopIteration, TypeError, ValueError):
        status = "stale"
    return {
        "schemaVersion": 1,
        "status": status,
        **{
            key: marker[key]
            for key in (
                "operationId",
                "sourceRenderOperationId",
                "snapshotHash",
                "assemblyId",
            )
            if marker.get(key) is not None
        },
        **(
            {"errorCode": marker["errorCode"]}
            if isinstance(marker.get("errorCode"), str)
            and re.fullmatch(r"[A-Z][A-Z0-9_]{1,99}", marker["errorCode"])
            else {}
        ),
        "retryable": status in {"pending", "failed", "stale"},
    }
