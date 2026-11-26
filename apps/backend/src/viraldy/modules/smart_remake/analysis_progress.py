"""Small, observed compile checkpoints for the owned project's loading view."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .engine.reference_analyzer import validate_source_analysis
from .models import SmartRemakeOperationModel
from .source_audio import normalize_source_audio

_STAGES = {
    "validating_source",
    "analyzing_source",
    "resolving_scenes",
    "identifying_product",
    "building_storyboard",
    "completed",
    "failed",
}
_PREVIEW_SCENE_LIMIT = 12
_PRELIMINARY_LIMIT = 8


def _text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"https?://\S+", "[liên kết]", " ".join(value.split()))[:500]


def _number(value: Any) -> float | None:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        return None
    return float(value)


def _scene(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    start, end, action = (
        _number(value.get("startSecond")),
        _number(value.get("endSecond")),
        _text(value.get("action")),
    )
    index = value.get("index")
    if (
        start is None
        or end is None
        or end <= start
        or type(index) is not int
        or index < 0
        or not action
    ):
        return None
    return {
        "index": index,
        "startSecond": start,
        "endSecond": end,
        "action": action,
        **{key: text for key in ("camera", "transition") if (text := _text(value.get(key)))},
    }


def _product(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not (name := _text(value.get("name"))):
        return None
    details = value.get("details")
    observed = list(
        dict.fromkeys(
            text for item in (details if isinstance(details, list) else []) if (text := _text(item))
        )
    )[:8]
    return {"name": name, "details": observed} if observed else None


def _identified_product(value: dict[str, Any]) -> dict[str, Any] | None:
    from viraldy.shared.errors.base import AppError

    from .generation_expectations import validate_product_lock

    try:
        lock = validate_product_lock(value)
    except AppError:
        return None
    visual = lock["visualIdentity"]
    return _product(
        {
            "name": lock.get("productName"),
            "details": [
                *(visual.get("colors") or []),
                *(
                    visual.get(field)
                    for field in ("shape", "material", "texture", "pattern", "visibleBranding")
                ),
                *(lock.get("mustPreserve") or []),
            ],
        }
    )


def _quick_summary(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    status = value.get("status")
    if not isinstance(status, str) or status not in {
        "pending",
        "completed",
        "unavailable",
    }:
        return None
    if value["status"] != "completed":
        reason = value.get("reason")
        return {
            "status": value["status"],
            **({"reason": reason} if value["status"] == "unavailable" and isinstance(reason, str)
               and reason in {"timeout", "invalid_response", "unavailable"} else {}),
        }
    summary = _text(value.get("summary"))
    if not summary:
        return {"status": "unavailable"}
    observations = value.get("observations")
    return {
        "status": "completed",
        "summary": summary,
        "observations": [
            {"label": _text(item.get("label"))[:40], "detail": _text(item.get("detail"))[:300]}
            for item in (observations if isinstance(observations, list) else [])[:3]
            if isinstance(item, dict) and _text(item.get("label")) and _text(item.get("detail"))
        ],
        **({"sourceAudio": audio} if (audio := normalize_source_audio(value.get("sourceAudio")))
           else {}),
    }


async def publish_quick_summary(
    session: AsyncSession, operation: SmartRemakeOperationModel, value: dict[str, Any]
) -> bool:
    """Serialize the optional writer with stage updates, without extending a finished compile."""
    await session.refresh(
        operation, attribute_names=["result_json", "status"], with_for_update=True
    )
    if operation.status != "running" or operation.result_json.get("kind") != "compile":
        await session.commit()
        return False
    progress = operation.result_json.get("analysisProgress") or {}
    operation.result_json = {
        **operation.result_json,
        "analysisProgress": {
            **progress,
            "quickSummary": _quick_summary(value),
            "updatedAt": datetime.now(UTC).isoformat(),
        },
    }
    await session.commit()
    return True


def _preliminary_observations(analysis: Any) -> list[dict[str, str]]:
    """Keep heard/seen descriptions independent of unverified scene timestamps."""
    shots = analysis.get("sourceShots") if isinstance(analysis, dict) else None
    if not isinstance(shots, list):
        return []
    generic = {"show product", "show the product", "show the key product action"}
    details = dict.fromkeys(
        text for shot in shots if isinstance(shot, dict)
        and (text := _text(shot.get("action"))[:300]) and text.lower() not in generic
    )
    return [{"label": "Thao tác trong mẫu", "detail": text}
            for text in list(details)[:_PRELIMINARY_LIMIT]]


def _public_preliminary(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    return [
        {"label": label, "detail": detail}
        for item in value[:_PRELIMINARY_LIMIT] if isinstance(item, dict)
        and (label := _text(item.get("label"))[:40])
        and (detail := _text(item.get("detail"))[:300])
    ]


def public_analysis_progress(
    operation: SmartRemakeOperationModel, *, retry_disposition: str | None = None,
) -> dict[str, Any] | None:
    """Read only an allowlisted projection; never return model/receipt/storage payloads."""
    result = operation.result_json or {}
    raw = result.get("analysisProgress")
    if (
        result.get("kind") != "compile"
        or not isinstance(raw, dict)
        or raw.get("schemaVersion") != 1
    ):
        return None
    stage = raw.get("stage")
    if (
        not isinstance(stage, str)
        or stage not in _STAGES
        or operation.status not in {"running", "completed", "failed"}
    ):
        return None
    raw_scenes = raw.get("scenes")
    public: dict[str, Any] = {
        "schemaVersion": 1,
        "operationId": str(operation.id),
        "requestKey": operation.idempotency_key,
        "status": operation.status,
        "stage": operation.status if operation.status != "running" else stage,
        "startedAt": _text(raw.get("startedAt")),
        "updatedAt": _text(raw.get("updatedAt")),
        "scenes": [
            scene
            for item in (raw_scenes if isinstance(raw_scenes, list) else [])[:_PREVIEW_SCENE_LIMIT]
            if (scene := _scene(item))
        ],
    }
    duration = _number(raw.get("sourceDurationSeconds"))
    if duration is not None and duration > 0:
        public["sourceDurationSeconds"] = duration
    count = raw.get("sceneCount")
    if type(count) is int and count > 0:
        public["sceneCount"] = count
    if product := _product(raw.get("product")):
        public["product"] = product
    if summary := _quick_summary(raw.get("quickSummary")):
        public["quickSummary"] = summary
    if audio := normalize_source_audio(raw.get("sourceAudio")):
        public["sourceAudio"] = audio
    if not public["scenes"]:
        preliminary = _public_preliminary(raw.get("preliminaryObservations"))
        checkpoint = result.get("sourceAnalysisCheckpoint")
        if not preliminary and isinstance(checkpoint, dict):
            preliminary = _preliminary_observations(checkpoint.get("analysis"))
        if preliminary:
            public["preliminaryObservations"] = preliminary
    error = _text(raw.get("errorCode") or result.get("errorCode"))
    if re.fullmatch(r"[A-Z][A-Z0-9_]*", error):
        public["errorCode"] = error
    if operation.status == "failed":
        public["retryDisposition"] = (
            "new_analysis" if retry_disposition == "new_analysis" else "reconcile"
        )
    return public


def _observations(
    analysis: dict[str, Any], duration: float | None, source_scenes: list[dict[str, Any]] | None
) -> dict[str, Any]:
    from viraldy.shared.errors.base import AppError

    try:
        validate_source_analysis(analysis, target_duration=duration)
    except AppError:
        return {"scenes": []}
    shots = analysis["sourceShots"]
    ranges = (
        [(scene["startFrame"] / 24, scene["endFrame"] / 24) for scene in source_scenes]
        if source_scenes
        else [(shot["startSecond"], shot["endSecond"]) for shot in shots]
    )
    scenes = []
    for index, (start, end) in enumerate(ranges[:_PREVIEW_SCENE_LIMIT]):
        observed = [
            shot for shot in shots if shot["startSecond"] < end and shot["endSecond"] > start
        ]
        if (
            not observed
            or observed[0]["startSecond"] < start - 1 / 24
            or observed[-1]["endSecond"] > end + 1 / 24
        ):
            return {"scenes": []}
        first, last = observed[0], observed[-1]
        scenes.append(
            {
                "index": index,
                "startSecond": start,
                "endSecond": end,
                "action": " → ".join(dict.fromkeys(shot["action"] for shot in observed)),
                "camera": " · ".join(
                    filter(None, (first.get("cameraAngle"), first.get("cameraMovement")))
                ),
                "transition": last.get("transitionOut"),
            }
        )
    return {"sceneCount": len(ranges), "scenes": scenes}


async def checkpoint_analysis(
    session: AsyncSession,
    operation: SmartRemakeOperationModel | None,
    stage: str,
    *,
    request_key: str | None,
    source_duration: float | None = None,
    analysis: dict[str, Any] | None = None,
    source_scenes: list[dict[str, Any]] | None = None,
    product: dict[str, Any] | None = None,
    error_code: str | None = None,
    result_updates: dict[str, Any] | None = None,
) -> None:
    """Commit completed facts and the next actual stage without starting any model work."""
    if operation is None:
        return
    await session.refresh(
        operation, attribute_names=["result_json", "status"], with_for_update=True
    )
    now = datetime.now(UTC).isoformat()
    previous = (operation.result_json or {}).get("analysisProgress") or {}
    created = getattr(operation, "created_at", None)
    progress: dict[str, Any] = {
        **previous,
        "schemaVersion": 1,
        "stage": stage,
        "requestKey": request_key,
        "startedAt": previous.get("startedAt") or (created.isoformat() if created else now),
        "updatedAt": now,
        "scenes": previous.get("scenes", []),
    }
    if source_duration is not None:
        progress["sourceDurationSeconds"] = source_duration
    if analysis is not None:
        progress.pop("sceneCount", None)
        progress.update(_observations(analysis, source_duration, source_scenes))
        if preliminary := _preliminary_observations(analysis):
            progress["preliminaryObservations"] = preliminary
        if audio := normalize_source_audio(analysis.get("sourceAudio")):
            progress["sourceAudio"] = audio
    if product is not None:
        progress.pop("product", None)
        if observed_product := _identified_product(product):
            progress["product"] = observed_product
    if error_code:
        progress["errorCode"] = error_code
    if stage in {"completed", "failed"}:
        operation.status = stage
        if (progress.get("quickSummary") or {}).get("status") == "pending":
            progress["quickSummary"] = {"status": "unavailable"}
    # Both writers reload under the operation lock. Preserve optional observations,
    # request receipts and the source checkpoint when advancing the main stage.
    operation.result_json = {
        **(operation.result_json or {}),
        **(result_updates or {}),
        "kind": "compile",
        "analysisProgress": progress,
    }
    await session.commit()
