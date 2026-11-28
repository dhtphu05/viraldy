"""Validate and apply local scene prose identically before preview or submission."""

from __future__ import annotations

import copy
from typing import Any

from viraldy.shared.errors.base import AppError

from .engine.prompt_sanitizer import validate_sanitized_compiler_prompts


def apply_scene_prompt_drafts(
    context: dict[str, Any],
    state: dict[str, Any],
    drafts: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return new copies; prompt bytes and the saved timing stay intact."""
    context, state = copy.deepcopy(context), copy.deepcopy(state)
    if len(drafts) != len(state["scenes"]):
        raise AppError("SMART_REMAKE_TIMELINE_INVALID", "The saved scene order cannot change.")
    for index, draft in enumerate(drafts):
        compiled = context["sceneMap"]["scenes"][index]
        prompts = {name: draft[name] for name in ("prompt", "imagePrompt", "videoPrompt")}
        if any(
            not isinstance(value, str) or not value.strip() or len(value) > 12000
            for value in prompts.values()
        ):
            raise AppError("SMART_REMAKE_PROMPT_INVALID", "Every scene needs valid prompts.")
        validate_sanitized_compiler_prompts(
            prompt=prompts["prompt"],
            image_prompt=prompts["imagePrompt"],
            video_prompt=prompts["videoPrompt"],
            analysis=context["referenceAnalysis"] or {},
            product_lock=context["productLock"],
            timeline=compiled.get("shotPlan") or {},
        )
        if all(compiled[field] == prompts[field] for field in prompts):
            continue
        for field in prompts:
            compiled[f"original{field[0].upper()}{field[1:]}"] = compiled[field]
        compiled.update(prompts)
        compiled["promptEdited"] = True
        state["scenes"][index].update(prompts)
        state["renderPlan"]["units"][index].update(prompts)
        context["renderPlan"]["units"][index].update(prompts)
    return context, state
