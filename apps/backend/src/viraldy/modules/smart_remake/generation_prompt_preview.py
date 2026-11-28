"""Read-only KIE prompt previews for the current local script draft."""

from __future__ import annotations

import copy
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError

from .engine.window_continuity import build_window_context
from .generation_expectations import build_generation_expectations
from .project_contracts import SmartRemakeRequirements
from .provider_group_planning import freeze_provider_groups
from .provider_group_request import conditioned_group_request
from .scene_prompt_drafts import apply_scene_prompt_drafts


class ScenePromptDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    renderUnitId: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=12000)
    imagePrompt: str = Field(min_length=1, max_length=12000)
    videoPrompt: str = Field(min_length=1, max_length=12000)


class GenerationPromptPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expectedRevision: int = Field(ge=1)
    scenePrompts: list[ScenePromptDraft] | None = Field(default=None, min_length=1, max_length=384)
    requirements: SmartRemakeRequirements | None = None


async def preview_generation_prompts(
    repository: Any,
    workspace_id: UUID,
    project_id: UUID,
    payload: GenerationPromptPreviewRequest,
) -> dict[str, Any]:
    row = await repository.project(workspace_id, project_id)
    if row.workspace_id != workspace_id or row.id != project_id:
        raise NotFoundError("SMART_REMAKE_PROJECT_NOT_FOUND", "Project was not found.")
    if row.revision != payload.expectedRevision:
        raise ConflictError("SMART_REMAKE_REVISION_CONFLICT", "Refresh the saved project first.")
    context, state = copy.deepcopy(row.context_json), copy.deepcopy(row.state_json)
    policy = context.get("p0") or {}
    if policy.get("status") in {"suspended", "deleted"} or (policy.get("deletion") or {}).get(
        "status"
    ) not in {None, "cancelled"}:
        raise AppError(
            "SMART_REMAKE_USE_STOPPED", "This project's assets are no longer in use.", 403
        )
    plan = context.get("renderPlan") or {}
    if payload.scenePrompts is not None:
        if [draft.renderUnitId for draft in payload.scenePrompts] != [
            unit["id"] for unit in plan.get("units", [])
        ]:
            raise AppError("SMART_REMAKE_TIMELINE_INVALID", "The saved scene order cannot change.")
        context, state = apply_scene_prompt_drafts(
            context,
            state,
            [draft.model_dump(exclude={"renderUnitId"}) for draft in payload.scenePrompts],
        )
    if payload.requirements is not None:
        context["p0"] = {**policy, "requirements": payload.requirements.model_dump(mode="json")}
    snapshot = build_generation_expectations(context)
    context["generationExpectations"] = snapshot
    plan = freeze_provider_groups(context)
    scenes = {scene["renderUnitId"]: scene for scene in snapshot["scenes"]}
    units = {unit["id"]: unit for unit in plan["units"]}
    groups = []
    for group in plan.get("groups") or []:
        request = conditioned_group_request(
            context=context,
            plan=plan,
            snapshot=snapshot,
            scenes=[{**units[identity], **scenes[identity]} for identity in group["renderUnitIds"]],
            segments=group["segments"],
            has_character_reference=bool(context.get("characterKey")),
            duration_seconds=group["rawDurationFrames"] // 24,
            window_context=build_window_context(plan, group, snapshot),
        )
        groups.append(
            {
                "groupId": group["id"],
                "model": request["model"],
                "prompt": request["input"]["prompt"],
            }
        )
    if not groups:
        raise AppError(
            "SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED", "A saved clip plan is required.", 409
        )
    return {"projectId": str(project_id), "revision": row.revision, "groups": groups}
