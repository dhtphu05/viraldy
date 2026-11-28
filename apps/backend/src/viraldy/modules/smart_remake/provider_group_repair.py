"""Frozen provider-window repairs with atomic logical-scene candidate bindings."""

from __future__ import annotations

import copy
from typing import Any
from uuid import uuid4

from viraldy.shared.errors.base import AppError


def stale_group() -> AppError:
    return AppError(
        "SMART_REMAKE_GROUP_REPAIR_STALE",
        "Clip hoặc đoạn đang dùng đã thay đổi. Hãy mở lại yêu cầu sửa clip.",
        409,
    )


def freeze_repair_group(row: Any, scene_id: str) -> dict[str, Any]:
    from .timeline_media import validate_trim
    from .timeline_service import validate_manifest

    plan, state = row.context_json.get("renderPlan", {}), row.state_json
    validate_manifest(row)
    group = next(
        (value for value in plan.get("groups", []) if scene_id in value["renderUnitIds"]), None
    )
    if (
        state.get("schemaVersion") != 2
        or state.get("targetDuration") != 12
        or plan.get("videoModel") != "wan/3-0-video"
        or group is None
        or group["rawDurationFrames"] != 144
        or group["targetDurationFrames"] != 144
        or plan.get("audioRequired") is not True
    ):
        raise AppError(
            "SMART_REMAKE_GROUP_REPAIR_UNAVAILABLE",
            "Sửa clip cần kịch bản Wan 12 giây với hai clip 6 giây có âm thanh.",
            409,
        )
    if scene_id != group["renderUnitIds"][0]:
        raise AppError(
            "SMART_REMAKE_GROUP_REPAIR_ANCHOR_REQUIRED",
            "Chọn cảnh đầu của clip để mở yêu cầu sửa clip.",
            409,
        )
    bases = []
    for scene_id in group["renderUnitIds"]:
        scene = next(value for value in state["scenes"] if value["id"] == scene_id)
        version = next(
            (value for value in scene["versions"] if value["id"] == scene["activeVersionId"]), None
        )
        item = next(
            value for value in state["draftTimeline"]["items"] if value["renderUnitId"] == scene_id
        )
        if (
            version is None
            or item.get("versionId") != version["id"]
            or version.get("technicalCheck", {}).get("status") != "passed"
        ):
            raise stale_group()
        validate_trim(item, version.get("frameCount", 144))
        bases.append(
            {
                "sceneId": scene_id,
                "baseVersionId": version["id"],
                "inFrame": item["inFrame"],
                "outFrame": item["outFrame"],
                "mediaHash": version["mediaHash"],
                "storageKey": version["storageKey"],
                "expectationsHash": version.get("expectationsHash"),
            }
        )
    return {
        "group": copy.deepcopy(group),
        "baseVersions": bases,
        "anchorSceneId": group["renderUnitIds"][0],
    }


def validate_repair_group(row: Any, binding: dict[str, Any], *, active: bool = True) -> None:
    """Check every saved version, not merely the representative scene in the route."""
    try:
        group = binding["group"]
        saved = next(
            value
            for value in row.context_json["renderPlan"]["groups"]
            if value["id"] == group["id"]
        )
        if (
            saved != group
            or [value["sceneId"] for value in binding["baseVersions"]] != (group["renderUnitIds"])
        ):
            raise stale_group()
        if active:
            if freeze_repair_group(row, binding["anchorSceneId"]) != binding:
                raise stale_group()
            return
        for base in binding["baseVersions"]:
            scene = next(
                value for value in row.state_json["scenes"] if value["id"] == base["sceneId"]
            )
            version = next(
                value for value in scene["versions"] if value["id"] == base["baseVersionId"]
            )
            if any(
                version.get(field) != base.get(field)
                for field in ("storageKey", "mediaHash", "expectationsHash")
            ):
                raise stale_group()
    except (AppError, KeyError, StopIteration, TypeError, ValueError):
        raise stale_group() from None


def group_repair_generation_scenes(row: Any, result: dict[str, Any]) -> list[dict[str, Any]]:
    """Neighbor handoffs also use accepted repairs, never the original scene map."""
    from .repair_intent import repair_base_scene

    scenes: list[dict[str, Any]] = copy.deepcopy(row.context_json["sceneMap"]["scenes"])
    for scene in row.state_json["scenes"]:
        if scene.get("activeVersionId"):
            scenes[scene["index"]] = repair_base_scene(row, scene)
    patches = {value["renderUnitId"]: value for value in result.get("compiledScenes", [])}
    for index, unit in enumerate(row.context_json["renderPlan"]["units"]):
        if unit["id"] in patches:
            scenes[index] = copy.deepcopy(patches[unit["id"]])
    return scenes


def affected_group_versions(state: dict[str, Any], operation: Any) -> list[dict[str, str]] | None:
    """A public receipt exists only when the whole candidate set matches retained versions."""
    result = operation.result_json
    binding, affected = result.get("repairGroup"), result.get("affectedVersions")
    if not isinstance(binding, dict) or not isinstance(affected, list) or not affected:
        return None
    try:
        group = binding["group"]
        task = result.get("tasks", {}).get(f"group:{group['id']}", {})
        if not task.get("taskId") or not result.get("candidateMediaHash"):
            return None
        if [value["sceneId"] for value in affected] != group["renderUnitIds"]:
            return None
        media = set()
        for item, base, segment in zip(
            affected, binding["baseVersions"], group["segments"], strict=True
        ):
            scene = next(value for value in state["scenes"] if value["id"] == item["sceneId"])
            version = next(
                value for value in scene["versions"] if value["id"] == item["candidateVersionId"]
            )
            metadata = version.get("providerMetadata", {})
            if (
                item["baseVersionId"] != base["baseVersionId"]
                or version.get("parentVersionId") != base["baseVersionId"]
                or metadata.get("repairScope") != "provider_group"
                or metadata.get("repairOperationId") != str(operation.id)
                or metadata.get("renderGroupId") != group["id"]
                or metadata.get("repairAffectedVersions") != affected
                or metadata.get("repairBaseTimeline") != repair_base_timeline(binding)
                or metadata.get("providerRequestId") != task["taskId"]
                or version.get("mediaHash") != result["candidateMediaHash"]
                or version.get("suggestedInFrame") != segment["inFrame"]
                or version.get("suggestedOutFrame") != segment["outFrame"]
                or version.get("expectationsHash") != result.get("expectationsHash")
                or version.get("generationExpectations") != result.get("generationExpectations")
            ):
                return None
            media.add(
                (version["storageKey"], version["mediaHash"], metadata.get("providerRequestId"))
            )
        return copy.deepcopy(affected) if len(media) == 1 else None
    except (KeyError, StopIteration, TypeError, ValueError):
        return None


def repair_base_timeline(binding: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "renderUnitId": value["sceneId"],
            "versionId": value["baseVersionId"],
            "inFrame": value["inFrame"],
            "outFrame": value["outFrame"],
        }
        for value in binding["baseVersions"]
    ]


def group_repair_public_fields(state: dict[str, Any], operation: Any) -> dict[str, Any]:
    binding = operation.result_json.get("repairGroup")
    if not isinstance(binding, dict):
        return {}
    affected = affected_group_versions(state, operation)
    public_affected: list[dict[str, Any]] = (
        [dict(value) for value in affected]
        if affected
        else [
            {
                "sceneId": value["sceneId"],
                "baseVersionId": value["baseVersionId"],
                "candidateVersionId": None,
            }
            for value in binding["baseVersions"]
        ]
    )
    return {
        "repairScope": "provider_group",
        "renderGroupId": binding["group"]["id"],
        "candidateVersionId": affected[0]["candidateVersionId"] if affected else None,
        "affectedVersions": public_affected,
    }


async def retain_group_repair(
    service: Any,
    row: Any,
    operation: Any,
    task: dict[str, Any],
    client: Any,
    *,
    ensure_active: Any = lambda: None,
) -> None:
    import hashlib

    from starlette.concurrency import run_in_threadpool

    from .generation_expectations import expectations_scene, validate_generation_expectations
    from .repair_service import _new_version
    from .timeline_media import probe_timeline_media
    from .timeline_retention import _release_reads, _remember_media

    binding = operation.result_json["repairGroup"]
    group = binding["group"]
    if task.get("group") != group or not task.get("taskId") or not task.get("url"):
        raise stale_group()
    snapshot = validate_generation_expectations(
        operation.result_json.get("generationExpectations"),
        operation.result_json.get("expectationsHash"),
    )
    current = await service.repository.project(service.workspace_id, row.id, lock=True)
    validate_repair_group(current, binding, active=False)
    if affected_group_versions(current.state_json, operation):
        return
    await _release_reads(service)
    data = await client.download_file(task["url"])
    ensure_active()
    info = await run_in_threadpool(probe_timeline_media, data)
    key = await service.media.put(
        f"workspaces/{service.workspace_id}/smart-remake/{row.id}",
        data,
        "video/mp4",
    )
    candidates = []
    template = None
    for base, segment in zip(binding["baseVersions"], group["segments"], strict=True):
        prompts = expectations_scene(snapshot, base["sceneId"])
        metadata = {
            "provider": "kie",
            "providerRequestId": task["taskId"],
            "sourceOperationId": str(operation.id),
            "repairOperationId": str(operation.id),
            "repairScope": "provider_group",
            "renderGroupId": group["id"],
            "repairBaseTimeline": repair_base_timeline(binding),
            "generationExpectations": copy.deepcopy(snapshot),
            "expectationsHash": operation.result_json["expectationsHash"],
            "repairIntent": copy.deepcopy(operation.result_json["request"]["repairIntent"]),
            "repairNormalizerVersion": operation.result_json["repairNormalization"]["version"],
            **{
                field: copy.deepcopy(task[field])
                for field in (
                    "model",
                    "requestHash",
                    "imageReferences",
                )
                if field in task
            },
        }
        if template is None:
            template = await run_in_threadpool(
                _new_version,
                data,
                key,
                prompts,
                base["baseVersionId"],
                metadata,
                source="regenerated",
                audio_required=True,
                expected_duration=group["rawDurationFrames"] // 24,
            )
        version = {
            **copy.deepcopy(template),
            "id": str(uuid4()),
            "parentVersionId": base["baseVersionId"],
            "providerMetadata": metadata,
            **{field: prompts[field] for field in ("prompt", "imagePrompt", "videoPrompt")},
        }
        version.update(
            rawDurationFrames=group["rawDurationFrames"],
            frameCount=info["frameCount"],
            suggestedInFrame=segment["inFrame"],
            suggestedOutFrame=segment["outFrame"],
        )
        if info["frameCount"] < segment["outFrame"]:
            version["technicalCheck"] = {
                "status": "failed",
                "findings": [
                    "The planned scene range exceeds the clip.",
                ],
            }
        candidates.append(version)
    affected = [
        {
            "sceneId": base["sceneId"],
            "baseVersionId": base["baseVersionId"],
            "candidateVersionId": candidate["id"],
        }
        for base, candidate in zip(binding["baseVersions"], candidates, strict=True)
    ]
    ensure_active()
    current = await service.repository.project(service.workspace_id, row.id, lock=True)
    validate_repair_group(current, binding, active=False)
    state = copy.deepcopy(current.state_json)
    for base, version in zip(binding["baseVersions"], candidates, strict=True):
        version["providerMetadata"]["repairAffectedVersions"] = copy.deepcopy(affected)
        scene = next(value for value in state["scenes"] if value["id"] == base["sceneId"])
        scene["versions"] = [*scene["versions"], version]
    _remember_media(current, key)
    await service.repository.complete(
        current,
        state,
        operation,
        {
            **operation.result_json,
            "repairScope": "provider_group",
            "renderGroupId": group["id"],
            "needsReconciliation": False,
            "candidateVersionId": candidates[0]["id"],
            "affectedVersions": affected,
            "candidateMediaHash": hashlib.sha256(data).hexdigest(),
        },
    )


async def accept_group_repair(
    service: Any,
    row: Any,
    state: dict[str, Any],
    operation: Any,
    version: dict[str, Any],
) -> None:
    import hashlib
    from uuid import UUID

    from .generation_expectations import validate_generation_expectations
    from .project_preview import mark_accepted_group_preview, queue_automatic_preview
    from .repair_service import _revision
    from .timeline_media import validate_trim
    from .timeline_retention import _invalidate_current
    from .timeline_service import _assert_in_use

    metadata = version["providerMetadata"]
    source = await service.repository.operation(
        service.workspace_id,
        row.id,
        UUID(metadata["repairOperationId"]),
    )
    binding = source.result_json.get("repairGroup")
    affected = affected_group_versions(state, source)
    if source.status != "completed" or not binding or not affected:
        raise stale_group()
    if version["id"] not in {item["candidateVersionId"] for item in affected}:
        raise stale_group()
    validate_generation_expectations(
        source.result_json.get("generationExpectations"), source.result_json.get("expectationsHash")
    )
    data = await service.media.read(version["storageKey"])
    if hashlib.sha256(data).hexdigest() != source.result_json["candidateMediaHash"]:
        raise AppError("SMART_REMAKE_MEDIA_CHANGED", "Video clip mới đã thay đổi.", 409)
    current = await service.repository.project(service.workspace_id, row.id, lock=True)
    _revision(current.state_json, state["revision"])
    _assert_in_use(current)
    validate_repair_group(current, binding)
    state = copy.deepcopy(current.state_json)
    for item in affected:
        scene = next(value for value in state["scenes"] if value["id"] == item["sceneId"])
        candidate = next(
            value for value in scene["versions"] if value["id"] == item["candidateVersionId"]
        )
        if candidate["technicalCheck"]["status"] != "passed":
            raise AppError(
                "SMART_REMAKE_TECHNICAL_CHECK_FAILED", "Clip mới chưa đạt kiểm tra kỹ thuật.", 409
            )
        selection = next(
            value
            for value in state["draftTimeline"]["items"]
            if value["renderUnitId"] == scene["id"]
        )
        updated = {
            **selection,
            "versionId": candidate["id"],
            "inFrame": candidate["suggestedInFrame"],
            "outFrame": candidate["suggestedOutFrame"],
            "reviewed": False,
        }
        validate_trim(updated, candidate["frameCount"])
        selection.update(updated)
        scene["activeVersionId"] = candidate["id"]
        candidate["usedByRevision"] = state["revision"] + 1
    _invalidate_current(current, state, "provider_group_accepted")
    state["revision"] += 1
    mark_accepted_group_preview(current, state, operation)
    await service.repository.complete(
        current,
        state,
        operation,
        {
            "kind": "accept",
            "repairScope": "provider_group",
            "renderGroupId": binding["group"]["id"],
            "repairOperationId": str(source.id),
            "affectedVersions": affected,
        },
    )
    await queue_automatic_preview(service, current, operation)
