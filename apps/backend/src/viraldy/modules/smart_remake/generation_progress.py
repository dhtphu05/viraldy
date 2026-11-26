"""Read-only progress from frozen provider groups and retained execution receipts."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from viraldy.shared.errors.base import AppError

from .generation_expectations import (
    require_generation_expectations,
    validate_generation_expectations,
)
from .provider_execution import safe_provider_identifier, validated_execution_evidence

logger = logging.getLogger(__name__)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _time(value: Any) -> str | None:
    try:
        instant = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        return instant.isoformat() if instant.utcoffset() is not None else None
    except (TypeError, ValueError):
        return None


def _code(value: Any) -> str | None:
    return (
        value if isinstance(value, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", value) else None
    )


def _plan(row: Any, operation: Any, workspace_id: Any) -> dict[str, Any] | None:
    result, context = operation.result_json or {}, row.context_json
    plan = result.get("renderPlan")
    if (
        getattr(row, "workspace_id", None) != workspace_id
        or operation.project_id != row.id
        or result.get("kind") != "render"
        or operation.status not in {"running", "completed", "failed"}
        or context.get("p0", {}).get("status") in {"suspended", "deleted"}
        or not isinstance(plan, dict)
        or not plan.get("groups")
        or result.get("renderPlanHash") != _hash(plan)
        or _hash(context.get("renderPlan")) != _hash(plan)
        or (
            row.state_json.get("renderPlan") is not None
            and _hash(row.state_json["renderPlan"]) != _hash(plan)
        )
        or result.get("expectationsHash") != context.get("expectationsHash")
    ):
        return None
    try:
        require_generation_expectations(context)
        validate_generation_expectations(
            result.get("generationExpectations"), result.get("expectationsHash")
        )
    except (AppError, TypeError, ValueError):
        return None
    groups, units = plan["groups"], plan.get("units", [])
    if row.state_json.get("targetDuration") not in {8, 16}:
        return None
    if len(groups) != row.state_json["targetDuration"] // 8:
        return None
    unit_ids = [unit.get("id") for unit in units]
    selected = []
    for group in groups:
        cursor = 0
        if (
            not safe_provider_identifier(group.get("id"))
            or group.get("rawDurationFrames") != 192
            or group.get("targetDurationFrames") != 192
            or not group.get("renderUnitIds")
        ):
            return None
        segments = group.get("segments", [])
        if [segment.get("renderUnitId") for segment in segments] != group["renderUnitIds"]:
            return None
        for segment in segments:
            end = segment.get("outFrame")
            if (
                type(end) is not int
                or type(segment.get("inFrame")) is not int
                or segment["inFrame"] != cursor
                or not cursor < end <= 192
            ):
                return None
            cursor = end
        if cursor != 192:
            return None
        selected.extend(group["renderUnitIds"])
    return plan if selected == unit_ids and len(set(selected)) == len(selected) else None


def _images(row: Any, operation: Any, group: dict[str, Any]) -> list[dict[str, Any]]:
    result = operation.result_json
    units = {unit["id"]: unit for unit in result["renderPlan"]["units"]}
    indices = [units[identity]["sceneIndex"] for identity in group["renderUnitIds"]]
    offsets = (
        [0] if row.context_json.get("characterKey") else list(dict.fromkeys([0, len(indices) - 1]))
    )
    images = []
    for offset in offsets:
        image = result.get("images", {}).get(str(indices[offset]), {})
        expected = group["renderUnitIds"][offset]
        if image.get("renderUnitId") not in {None, expected} or (
            image.get("status") == "completed" and image.get("renderUnitId") != expected
        ):
            image = {}
        images.append(image)
    return images


def _checks(row: Any, operation: Any, images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hashes = {image.get("mediaHash") for image in images if image.get("mediaHash")}
    checks = row.context_json.get("p0", {}).get("conditioningChecks", {})
    return [
        check
        for key, check in checks.items()
        if check.get("operationId") == str(operation.id)
        and check.get("contextHash") == key
        and check.get("subject", {}).get("projectId") == str(row.id)
        and check.get("subject", {}).get("mediaHash") in hashes
        and not check.get("stale")
    ]


def _report_id(row: Any, operation: Any, checks: list[Any], images: list[Any]) -> str | None:
    for check in checks:
        for report in row.context_json.get("p0", {}).get("inspections", {}).get("reports", []):
            if (
                report.get("id") != check.get("reportId")
                or report.get("stage") != "conditioning"
                or report.get("operationId") != str(operation.id)
                or report.get("stale")
                or report.get("contextHash") != check.get("contextHash")
                or report.get("expectationsHash") != operation.result_json.get("expectationsHash")
                or report.get("subject") != check.get("subject")
                or not any(
                    image.get("requestHash") == report.get("conditioningImageRequestHash")
                    and image.get("mediaHash") == report.get("subject", {}).get("mediaHash")
                    for image in images
                )
            ):
                continue
            try:
                return str(UUID(report["id"]))
            except (ValueError, TypeError):
                continue
    return None


def _video(
    operation: Any,
    group: dict[str, Any],
    attempts: list[Any] | None,
) -> tuple[dict[str, Any], Any, bool | None]:
    result = operation.result_json
    task = result.get("tasks", {}).get(f"group:{group['id']}", {})
    if (
        task.get("renderGroupId", group["id"]) != group["id"]
        or task.get("group", group) != group
        or task.get("expectationsHash", result["expectationsHash"]) != result["expectationsHash"]
    ):
        return {}, None, None
    slot = f"video:group:{group['id']}"
    matched = next((a for a in attempts or [] if a.metadata_json.get("slot") == slot), None)
    if matched is not None and (
        task.get("attemptId") == str(matched.id)
        and task.get("requestHash") == matched.request_hash
        and safe_provider_identifier(task.get("taskId"))
        and task["taskId"] == matched.provider_task_id
    ):
        proof = validated_execution_evidence(
            {
                "id": str(matched.id),
                "requestHash": matched.request_hash,
                "provider": matched.provider,
                "model": matched.model,
                "providerTaskId": matched.provider_task_id,
                "receipt": matched.receipt_json,
            }
        )
        if (
            proof
            and proof["operation"] == "kie.tasks.create"
            and proof.get("taskId") == task["taskId"]
        ):
            return task, matched, True
    slots = {f"video:group:{g['id']}" for g in result["renderPlan"]["groups"]}
    task_keys = {f"group:{g['id']}" for g in result["renderPlan"]["groups"]}
    unmapped = any(a.metadata_json.get("slot") not in slots for a in attempts or []) or any(
        key not in task_keys and value for key, value in result.get("tasks", {}).items()
    )
    return (
        task,
        matched,
        False if attempts is not None and not task and not matched and not unmapped else None,
    )


def _versions(row: Any, operation: Any, group: dict[str, Any], task: dict[str, Any]) -> list[Any]:
    if not safe_provider_identifier(task.get("taskId")):
        return []
    scenes = {scene["id"]: scene for scene in row.state_json.get("scenes", [])}
    versions = []
    for identity in group["renderUnitIds"]:
        version = next(
            (
                v
                for v in scenes.get(identity, {}).get("versions", [])
                if v.get("providerMetadata", {}).get("renderGroupId") == group["id"]
                and v.get("providerMetadata", {}).get("providerRequestId") == task["taskId"]
                and v.get("expectationsHash") == operation.result_json["expectationsHash"]
            ),
            None,
        )
        if version is None:
            return []
        versions.append(version)
    return versions


def _group(
    row: Any, operation: Any, group: dict[str, Any], attempts: list[Any] | None
) -> dict[str, Any]:
    images = _images(row, operation, group)
    checks = _checks(row, operation, images)
    task, attempt, submitted = _video(operation, group, attempts)
    versions = _versions(row, operation, group, task)
    stage = "queued"
    if versions:
        stage = (
            "completed"
            if all(v.get("technicalCheck", {}).get("status") == "passed" for v in versions)
            else "blocked"
        )
    elif task.get("taskId"):
        stage = "checking" if attempt and attempt.status == "completed" else "generating"
    elif task or attempt:
        stage = "submitting_video" if task.get("status") == "submitting" else "unknown"
    elif any(
        image.get("status") in {"failed", "rejected", "preflight_rejected"} for image in images
    ):
        stage = "blocked"
    elif operation.result_json.get("referencePreparation") == "direct" and any(images):
        stage = "submitting_video" if all(
            image.get("status") == "completed" for image in images
        ) else "preparing_image"
    elif any(c.get("phase") == "unknown" for c in checks):
        stage = "unknown"
    elif any(c.get("phase") == "completed" and c.get("status") != "passed" for c in checks):
        stage = "blocked"
    elif checks or any(image.get("status") == "completed" for image in images) and all(images):
        stage = "checking_image"
    elif any(images):
        stage = "preparing_image"
    report_id = _report_id(row, operation, checks, images)
    image_error = next((code for image in images if (code := _code(image.get("errorCode")))), None)
    return {
        "groupId": group["id"],
        "stage": stage,
        "videoSubmitted": submitted,
        **({"inspectionReportId": report_id} if report_id else {}),
        **({"errorCode": image_error} if stage == "blocked" and image_error else {}),
    }


def _failure_groups(
    row: Any, operation: Any, plan: Any, groups: list[Any], attempts: Any
) -> list[Any]:
    result = operation.result_json
    if operation.status != "failed" and not result.get("needsReconciliation"):
        return groups
    active = [
        i
        for i, group in enumerate(plan["groups"])
        if any(_images(row, operation, group))
        or result.get("tasks", {}).get(f"group:{group['id']}")
        or any(a.metadata_json.get("slot") == f"video:group:{group['id']}" for a in attempts or [])
    ]
    index = max(active, default=-1)
    if index < 0:
        index = next((i for i, group in enumerate(groups) if group["stage"] != "completed"), -1)
    if index < 0:
        return groups
    current = groups[index]
    updated = {
        **current,
        "stage": "unknown" if result.get("needsReconciliation") else "blocked",
        **({"errorCode": error} if (error := _code(result.get("errorCode"))) else {}),
    }
    return [updated if i == index else group for i, group in enumerate(groups)]


def generation_progress(
    row: Any,
    operation: Any,
    *,
    workspace_id: Any,
    attempts: list[Any] | None = None,
) -> dict[str, Any] | None:
    """Pure projection: an omitted ledger means unknown counts, never zero submissions."""
    plan = _plan(row, operation, workspace_id)
    if plan is None or not (started := _time(getattr(operation, "created_at", None))):
        return None
    owned = (
        None
        if attempts is None
        else [
            a
            for a in attempts
            if getattr(a, "project_id", None) == row.id
            and getattr(a, "workspace_id", None) == workspace_id
            and (getattr(a, "metadata_json", None) or {}).get("operationId") == str(operation.id)
        ]
    )
    video_attempts = (
        None if owned is None else [a for a in owned if a.stage == "video" and a.provider == "kie"]
    )
    groups = [_group(row, operation, group, video_attempts) for group in plan["groups"]]
    groups = _failure_groups(row, operation, plan, groups, video_attempts)
    instants = [started]
    for attempt in owned or []:
        instants.extend(
            value
            for key in ("created_at", "submitted_at", "completed_at")
            if (value := _time(getattr(attempt, key, None)))
        )
    for group in plan["groups"]:
        for check in _checks(row, operation, _images(row, operation, group)):
            instants.extend(
                value for key in ("startedAt", "completedAt") if (value := _time(check.get(key)))
            )
    return {
        "operationId": str(operation.id),
        "status": operation.status,
        "startedAt": started,
        "updatedAt": max(instants, key=datetime.fromisoformat),
        "groups": groups,
    }


def _image_key(row: Any, operation: Any, image: dict[str, Any]) -> str | None:
    key, digest = image.get("storageKey"), image.get("requestHash")
    asset = row.context_json.get("imageAssets", {}).get(digest)
    prefix = f"workspaces/{row.workspace_id}/smart-remake/{row.id}/images/"
    scene = next(
        (
            s
            for s in operation.result_json["generationExpectations"]["scenes"]
            if s["renderUnitId"] == image.get("renderUnitId")
        ),
        None,
    )
    if (
        image.get("status") != "completed"
        or not isinstance(asset, dict)
        or {k: v for k, v in image.items() if k != "status"} != asset
        or not scene
        or image.get("expectationsHash") != operation.result_json["expectationsHash"]
        or image.get("sourceSceneId") != scene["sourceSceneId"]
        or image.get("openingFrame") != scene["openingFrame"]
        or not isinstance(key, str)
        or not key.startswith(prefix)
        or re.fullmatch(r"[a-f0-9]{32}", key[len(prefix) :]) is None
    ):
        return None
    return key


def _video_key(
    row: Any, operation: Any, group: dict[str, Any], submitted: bool | None
) -> str | None:
    if submitted is not True:
        return None
    task = operation.result_json.get("tasks", {}).get(f"group:{group['id']}", {})
    versions = _versions(row, operation, group, task)
    if not versions:
        return None
    prefix = f"workspaces/{row.workspace_id}/smart-remake/{row.id}/"
    key, digest = versions[0].get("storageKey"), versions[0].get("mediaHash")
    frame_count = versions[0].get("frameCount")
    if (
        not isinstance(key, str)
        or not key.startswith(prefix)
        or re.fullmatch(r"[a-f0-9]{32}", key[len(prefix) :]) is None
        or not isinstance(digest, str)
        or re.fullmatch(r"[a-f0-9]{64}", digest) is None
        or type(frame_count) is not int
        or frame_count < 192
    ):
        return None
    for version, segment in zip(versions, group["segments"], strict=True):
        if (
            version.get("storageKey") != key
            or version.get("mediaHash") != digest
            or version.get("frameCount") != frame_count
            or version.get("rawDurationFrames") != 192
            or version.get("suggestedInFrame") != segment["inFrame"]
            or version.get("suggestedOutFrame") != segment["outFrame"]
            or version.get("technicalCheck", {}).get("status") != "passed"
            or version.get("providerMetadata", {}).get("requestHash") != task.get("requestHash")
        ):
            return None
    return key


async def _preview_url(media: Any, key: str) -> str | None:
    try:
        return str(await media.url(key))
    except Exception:
        logger.warning("Smart Remake retained preview could not be signed.")
        return None


async def present_generation_progress(
    row: Any,
    operation: Any,
    *,
    workspace_id: Any,
    attempts: list[Any] | None,
    media: Any,
) -> dict[str, Any] | None:
    """Sign only bound private assets; this never fetches storage or invokes a provider."""
    progress = generation_progress(row, operation, workspace_id=workspace_id, attempts=attempts)
    if progress is None:
        return None
    groups = []
    for public, group in zip(
        progress["groups"], operation.result_json["renderPlan"]["groups"], strict=True
    ):
        images = []
        for image in _images(row, operation, group):
            if key := _image_key(row, operation, image):
                if url := await _preview_url(media, key):
                    images.append({"renderUnitId": image["renderUnitId"], "url": url})
        video_url = None
        if key := _video_key(row, operation, group, public["videoSubmitted"]):
            video_url = await _preview_url(media, key)
        groups.append(
            {
                **public,
                **(
                    {"conditioningImageUrl": images[0]["url"], "conditioningImages": images}
                    if images
                    else {}
                ),
                **({"videoUrl": video_url} if video_url else {}),
            }
        )
    return {**progress, "groups": groups}
