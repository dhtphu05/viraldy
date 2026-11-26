"""Short-transaction retention of known outputs without overwriting concurrent rights changes."""

from __future__ import annotations

import copy
from typing import Any
from uuid import UUID

from viraldy.shared.errors.base import AppError

from .project_policy import invalidate_context
from .repair_service import RepairService


def _invalidate_current(row: Any, state: dict[str, Any], reason: str) -> None:
    if row.context_json.get("p0"):
        row.context_json = invalidate_context(row.context_json, reason=reason)
        state["assemblyCheck"] = {"status": "stale", "reason": reason}


async def _release_reads(service: RepairService) -> None:
    session = getattr(service.repository, "session", None)
    if session is not None:
        await session.commit()


def _remember_media(row: Any, key: str) -> None:
    if row.context_json.get("p0"):
        context = copy.deepcopy(row.context_json)
        retained = context["p0"].get("retainedMediaKeys", [])
        context["p0"]["retainedMediaKeys"] = list(dict.fromkeys([*retained, key]))
        row.context_json = context


async def _finish_retention(
    service: RepairService,
    project_id: UUID,
    before: dict[str, Any],
    staged: dict[str, Any],
    key: str,
    metadata: dict[str, Any],
) -> None:
    current = await service.repository.project(service.workspace_id, project_id, lock=True)
    state = copy.deepcopy(current.state_json)
    _remember_media(current, key)
    if any(
        state[field] != before[field]
        for field in ("scenes", "draftTimeline", "renderPlan", "sourceSceneMap")
    ):
        task_id = metadata.get("providerRequestId")
        additions = [
            (scene["id"], v)
            for scene, old in zip(staged["scenes"], before["scenes"], strict=True)
            for v in scene["versions"]
            if v not in old["versions"]
        ]
        replay = bool(task_id and additions) and all(
            any(
                v.get("providerMetadata", {}).get("providerRequestId") == task_id
                and v.get("mediaHash") == added.get("mediaHash")
                for scene in state["scenes"]
                if scene["id"] == scene_id
                for v in scene["versions"]
            )
            for scene_id, added in additions
        )
        await service.repository.save(current, state)
        if replay:
            return
        raise AppError(
            "SMART_REMAKE_REVISION_CONFLICT", "Scene bindings changed during retention.", 409
        )
    state.update(scenes=staged["scenes"], draftTimeline=staged["draftTimeline"])
    _invalidate_current(current, state, "scene_clip_retained")
    if current.context_json.get("p0"):
        current.context_json = {
            **current.context_json,
            "p0": {**current.context_json["p0"], "phase": "rendered"},
        }
        state["phase"] = "rendered"
    state["revision"] += 1
    await service.repository.save(current, state)
