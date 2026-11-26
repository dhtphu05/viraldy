"""Creative scene repair with immutable product, timing and opening-frame bindings."""

from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from viraldy.shared.errors.base import AppError

from .assembly_snapshots import retained_expectations
from .engine.prompt_sanitizer import sanitize_generation_scene, validate_generation_payload
from .generation_expectations import expectations_scene, require_generation_expectations
from .repair_schemas import RepairApiModel, RepairIntent

NORMALIZER_VERSION = "repair-intent-normalizer-v1"
PROMPT_FIELDS = ("prompt", "imagePrompt", "videoPrompt")


class PhysicalActionPatch(RepairApiModel):
    operator: str | None = Field(default=None, max_length=2000)
    targetSurface: str | None = Field(default=None, max_length=2000)
    contactPoint: str | None = Field(default=None, max_length=2000)
    movement: str | None = Field(default=None, max_length=2000)
    visibleEffect: str | None = Field(default=None, max_length=2000)


class RepairShotPatch(RepairApiModel):
    shotIndex: int = Field(ge=0, strict=True)
    action: str = Field(min_length=1, max_length=4000)
    physicalAction: PhysicalActionPatch | None = None
    stateBefore: str | None = Field(default=None, max_length=2000)
    stateAfter: str | None = Field(default=None, max_length=2000)
    cameraAngle: str | None = Field(default=None, max_length=2000)
    cameraMovement: str | None = Field(default=None, max_length=2000)
    framing: str | None = Field(default=None, max_length=2000)
    transitionOut: str | None = Field(default=None, max_length=2000)


class RepairScenePatch(RepairApiModel):
    prompt: str = Field(min_length=1, max_length=12000)
    imagePrompt: str = Field(min_length=1, max_length=12000)
    videoPrompt: str = Field(min_length=1, max_length=12000)
    shots: list[RepairShotPatch] = Field(max_length=32)


class RepairNormalizationResult(RepairApiModel):
    status: Literal["accepted", "conflict", "insufficient_evidence"]
    reason: str = Field(min_length=1, max_length=2000)
    scenePatch: RepairScenePatch | None = None

    @model_validator(mode="after")
    def matching_result(self) -> RepairNormalizationResult:
        if (self.status == "accepted") != (self.scenePatch is not None):
            raise ValueError("Only accepted repairs contain a scene patch.")
        return self


def invalid_intent() -> AppError:
    return AppError(
        "SMART_REMAKE_REPAIR_INTENT_INVALID",
        "Không thể chuẩn hóa yêu cầu sửa cảnh. Hãy mô tả rõ phần cần sửa rồi thử lại.",
        409,
    )


def repair_base_scene(row: Any, scene: dict[str, Any]) -> dict[str, Any]:
    """A second repair starts from its actual active clip, never the original plan."""
    version = next(
        (value for value in scene["versions"] if value["id"] == scene["activeVersionId"]), None
    )
    if version is None:
        raise AppError(
            "SMART_REMAKE_BASE_VERSION_REQUIRED", "Cảnh chưa có video để sửa. Hãy tạo video trước.",
            409,
        )
    current = require_generation_expectations(row.context_json)
    snapshot = retained_expectations(version or {})
    if snapshot is None or any(
        snapshot[key] != current[key] for key in ("productLock", "references")
    ):
        raise AppError(
            "SMART_REMAKE_EXPECTATIONS_REQUIRED",
            "Cần cập nhật kịch bản trước khi sửa phiên bản thiếu thông tin tham chiếu.",
            409,
        )
    retained = expectations_scene(snapshot, scene["id"])
    canonical = expectations_scene(current, scene["id"])
    if any(
        retained[key] != canonical[key] for key in ("sourceSceneId", "sourceRange", "openingFrame")
    ):
        raise AppError(
            "SMART_REMAKE_EXPECTATIONS_REQUIRED", "Phạm vi hoặc khung mở đầu cảnh đã thay đổi.", 409
        )
    compiled: dict[str, Any] = copy.deepcopy(
        row.context_json["sceneMap"]["scenes"][scene["index"]]
    )
    compiled["renderUnitId"] = scene["id"]
    compiled.update(
        {key: copy.deepcopy(retained[key]) for key in (*PROMPT_FIELDS, "shotPlan", "sourceSegment")}
    )
    # Normalized canonical directions are not a manual prompt diff.
    compiled["promptEdited"] = False
    for field in PROMPT_FIELDS:
        compiled.pop(f"original{field[0].upper()}{field[1:]}", None)
    compiled.pop("sourceFrame", None)
    compiled.pop("sourceFrames", None)
    return compiled


def apply_repair_result(
    compiled: dict[str, Any],
    response: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    try:
        result = RepairNormalizationResult.model_validate(response)
    except (ValidationError, TypeError, ValueError):
        raise invalid_intent() from None
    if result.status != "accepted":
        raise AppError(
            "SMART_REMAKE_REPAIR_INTENT_REJECTED",
            result.reason,
            409,
            {"status": result.status, "reason": result.reason},
        )
    assert result.scenePatch is not None
    patch = result.scenePatch
    shots = (compiled.get("shotPlan") or {}).get("shots", [])
    if [shot.shotIndex for shot in patch.shots] != list(range(len(shots))):
        raise invalid_intent()
    if patch.shots and patch.shots[0].stateBefore not in {None, shots[0].get("stateBefore")}:
        raise invalid_intent()
    updated = copy.deepcopy(compiled)
    updated.update({field: getattr(patch, field) for field in PROMPT_FIELDS})
    updated["shotPlan"] = {
        **updated.get("shotPlan", {}),
        "shots": [
            {
                **shot,
                **change.model_dump(exclude_none=True, exclude={"shotIndex"}),
                **(
                    {
                        "physicalAction": {
                            **(shot.get("physicalAction") or {}),
                            **change.physicalAction.model_dump(exclude_none=True),
                        }
                    }
                    if change.physicalAction is not None
                    else {}
                ),
            }
            for shot, change in zip(shots, patch.shots, strict=True)
        ],
    }
    updated["promptEdited"] = False
    clean = sanitize_generation_scene(
        updated, context.get("referenceAnalysis") or {}, context["productLock"]
    )
    validate_generation_payload(
        clean, context.get("referenceAnalysis") or {}, context["productLock"]
    )
    return clean


def fixture_repair_result(compiled: dict[str, Any], intent: RepairIntent) -> dict[str, Any]:
    """Offline deterministic fixture; never substitutes for live semantic validation."""
    suffix = intent.instruction or "Create an alternate take with the same product and opening."
    advanced = intent.advancedEdits.model_dump(exclude_none=True) if intent.advancedEdits else {}
    return {
        "status": "accepted",
        "reason": "Yêu cầu đã được áp dụng trong tư liệu thử offline.",
        "scenePatch": {
            **{
                field: advanced.get(field, f"{compiled[field]}\nRepair direction: {suffix}")
                for field in PROMPT_FIELDS
            },
            "shots": [
                {"shotIndex": index, "action": f"{shot.get('action', '')}. {suffix}"}
                for index, shot in enumerate((compiled.get("shotPlan") or {}).get("shots", []))
            ],
        },
    }
