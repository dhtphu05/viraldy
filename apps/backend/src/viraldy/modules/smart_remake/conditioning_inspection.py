"""Inspect retained conditioning images against original identity before Veo submission."""

from __future__ import annotations

import copy
import hashlib
import importlib
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID, uuid5

from starlette.concurrency import run_in_threadpool

from viraldy.shared.errors.base import AppError

from .budgeted_analysis import inspection_invoke
from .generation_budget import require_generation_policy
from .generation_expectations import expectations_hash, validate_generation_expectations
from .project_policy import constraints_hash, policy_hash, stable_hash
from .repair_media import now_iso
from .timeline_media import probe_timeline_media

# These errors are raised before the ledger submission marker/provider HTTP.
PREFLIGHT_ERRORS = frozenset(
    {
        "SMART_REMAKE_STAGE_BOUND_REQUIRED",
        "SMART_REMAKE_BUDGET_INVALID",
        "SMART_REMAKE_MODEL_NOT_CONFIGURED",
        "SMART_REMAKE_INSPECTION_MODEL_INPUT_INVALID",
        "SMART_REMAKE_MODEL_MEDIA_INVALID",
        "SMART_REMAKE_ATTEMPT_INVALID",
        "SMART_REMAKE_BUDGET_REQUIRED",
        "SMART_REMAKE_ATTEMPT_LIMIT",
        "SMART_REMAKE_BUDGET_EXPIRED",
        "SMART_REMAKE_BUDGET_EXCEEDED",
    }
)


def _error(code: str, message: str) -> AppError:
    return AppError(f"SMART_REMAKE_CONDITIONING_{code}", message, 409)


def _snapshot(row: Any, image: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    from .inspection.public import inspection_profile

    p0 = row.context_json["p0"]
    value = validate_generation_expectations(
        binding.get("expectations"), binding.get("expectationsHash")
    )
    scene_id = binding.get("imageSceneId")
    scene = next((s for s in value["scenes"] if s["renderUnitId"] == scene_id), None)
    if (
        scene is None
        or image.get("renderUnitId") != scene_id
        or image.get("sourceSceneId") != scene["sourceSceneId"]
        or image.get("openingFrame") != scene["openingFrame"]
        or image.get("expectationsHash") != binding["expectationsHash"]
        or value["requirementsHash"] != expectations_hash(p0["requirements"])
    ):
        raise _error("CONTEXT_INVALID", "Conditioning needs its exact frozen scene expectations.")
    manifest = {"protocolVersion": "conditioning-p0-v2", "image": image, "binding": binding}
    return {
        "subject": {
            "kind": "image",
            "projectId": str(row.id),
            "imageRole": "conditioning",
            "mediaHash": image["mediaHash"],
        },
        "constraintsHash": constraints_hash(row.context_json),
        "manifestHash": stable_hash(manifest),
        "policyHash": policy_hash(row.context_json),
        "requirements": copy.deepcopy(value["requirements"]),
        "requirementsHash": value["requirementsHash"],
        "expectations": value,
        "expectationsHash": binding["expectationsHash"],
        "sceneIds": [scene_id],
        "checkerProfile": inspection_profile(),
        "timeline": {},
        "manifest": manifest,
        "references": {
            role: copy.deepcopy(p0["assets"][role])
            for role in ("source", "product", "character")
            if role in p0["assets"]
        },
    }


async def _read_owned(
    repair: Any, value: dict[str, Any], identity: str, role: str
) -> dict[str, Any]:
    key = value.get("storageKey")
    if not isinstance(key, str) or not key.startswith(
        f"workspaces/{repair.workspace_id}/smart-remake/"
    ):
        raise _error("MEDIA_CHANGED", "Conditioning inspection requires owned private media.")
    try:
        data = await repair.media.read(key)
    except Exception as exc:
        raise _error("MEDIA_CHANGED", "Conditioning inspection media is unavailable.") from exc
    if hashlib.sha256(data).hexdigest() != value.get("mediaHash"):
        raise _error("MEDIA_CHANGED", "Conditioning inspection media changed.")
    result = {
        "id": identity,
        "role": role,
        "bytes": data,
        "mediaHash": value["mediaHash"],
        "mimeType": value["mimeType"],
    }
    if role == "source":
        info = await run_in_threadpool(probe_timeline_media, data)
        result.update(frameCount=info["frameCount"], fps=24)
    return result


async def _persist(
    repair: Any,
    project_id: UUID,
    image: dict[str, Any],
    binding: dict[str, Any],
    context_hash: str,
    check: dict[str, Any],
    report: dict[str, Any] | None = None,
) -> bool:
    current = await repair.repository.project(repair.workspace_id, project_id, lock=True)
    try:
        stale = stable_hash(_snapshot(current, image, binding)) != context_hash
    except AppError:
        stale = True
    p0 = copy.deepcopy(current.context_json["p0"])
    p0["conditioningAssets"] = {**p0.get("conditioningAssets", {}), image["requestHash"]: image}
    p0["conditioningChecks"] = {
        **p0.get("conditioningChecks", {}),
        context_hash: {**check, "stale": stale},
    }
    if report is not None:
        inspections = p0.setdefault("inspections", {"reports": [], "reviews": []})
        if any(existing["id"] == report["id"] for existing in inspections["reports"]):
            raise _error("REPORT_INVALID", "The checker reused a report identity.")
        inspections["reports"].append({**report, "stale": stale})
    await repair.repository.merge_context(current, {"p0": p0})
    return stale


def _validate(
    report: Any,
    snapshot: dict[str, Any],
    media: dict[str, Any],
    references: list[dict[str, Any]],
    constraints: dict[str, Any],
) -> dict[str, Any]:
    from .inspection_service import validate_report

    try:
        validator = importlib.import_module(".inspection.validation", package=__package__)
        typed = validator.validate_report_binding(
            report, snapshot["subject"], media, references, constraints
        )
        if any(getattr(typed, key) != value for key, value in snapshot["checkerProfile"].items()):
            raise ValueError("The conditioning checker profile is stale.")
        return validate_report(typed, snapshot, media, references)
    except (ValueError, TypeError, AppError) as exc:
        raise _error(
            "REPORT_INVALID", "The conditioning report does not bind the retained image."
        ) from exc


async def check_conditioning_images(
    repair: Any,
    row: Any,
    operation: Any,
    images: list[dict[str, Any]],
    *,
    binding: dict[str, Any],
    inspector: Callable[..., Awaitable[Any]] | None = None,
    invoke_model: Callable[..., Awaitable[Any]] | None = None,
) -> list[dict[str, Any]]:
    """Only exact, observed passing reports permit these images to condition video."""
    if row.context_json.get("p0") is None:
        await require_generation_policy(repair, row)
        return copy.deepcopy(images)
    from .inspection_service import _model_adapter, _public_inspector

    project_id, operation_id = row.id, operation.id
    actor_id = operation.result_json.get("actorId") or row.context_json["p0"].get("actorId")
    value = validate_generation_expectations(
        binding.get("expectations"), binding.get("expectationsHash")
    )
    indices = binding.get("imageSceneIndices")
    if (
        not binding.get("expectationsHash")
        or not isinstance(indices, list)
        or len(indices) != len(images)
        or any(type(index) is not int for index in indices)
        or len(set(indices)) != len(indices)
    ):
        raise _error("CONTEXT_INVALID", "Every conditioning image needs one exact scene binding.")
    scenes = {scene["sceneIndex"]: scene for scene in value["scenes"]}
    if any(index not in scenes for index in indices):
        raise _error("CONTEXT_INVALID", "A conditioning scene is outside the frozen plan.")
    results = []
    for image, index in zip(images, indices, strict=True):
        image_binding = {**binding, "imageSceneId": scenes[index]["renderUnitId"]}
        await require_generation_policy(repair, row)
        row = await repair.repository.project(repair.workspace_id, row.id)
        if any(
            isinstance(check, dict)
            and check.get("operationId") == str(operation_id)
            and check.get("phase") in {"invoking", "unknown"}
            for check in row.context_json["p0"].get("conditioningChecks", {}).values()
        ):
            raise _error(
                "RECONCILIATION_REQUIRED", "Reconcile the existing conditioning check first."
            )
        if row.context_json.get("imageAssets", {}).get(image.get("requestHash")) != image:
            raise _error(
                "MEDIA_CHANGED", "The conditioning image is not a retained generated asset."
            )
        snapshot = _snapshot(row, image, image_binding)
        context_hash = stable_hash(snapshot)
        media = await _read_owned(
            repair, image, "conditioning-" + image["requestHash"], "conditioning"
        )
        references = [
            await _read_owned(repair, value, role, role)
            for role, value in snapshot["references"].items()
        ]
        constraints = {
            key: snapshot[key]
            for key in (
                "constraintsHash",
                "manifestHash",
                "requirements",
                "timeline",
                "manifest",
                "expectations",
                "expectationsHash",
                "sceneIds",
                "requirementsHash",
            )
        }
        constraints.update(fps=24, frameCount=None)
        saved = row.context_json["p0"].get("conditioningChecks", {}).get(context_hash)
        if saved and saved.get("phase") not in {"completed", "retryable"}:
            raise _error(
                "RECONCILIATION_REQUIRED", "Reconcile the existing conditioning check first."
            )
        if saved and saved.get("phase") == "completed":
            report = next(
                (
                    report
                    for report in row.context_json["p0"].get("inspections", {}).get("reports", [])
                    if report["id"] == saved.get("reportId")
                ),
                None,
            )
            # Persisted reports carry server provenance fields outside B's typed schema.
            public_fields = importlib.import_module(
                ".inspection.contracts", package=__package__
            ).InspectionReport.model_fields
            public_report = {
                key: value for key, value in (report or {}).items() if key in public_fields
            }
            report = _validate(public_report, snapshot, media, references, constraints)
        else:
            inspect = inspector or _public_inspector()
            invoke = invoke_model
            if invoke is None:
                invoke = inspection_invoke(
                    repair.repository.session,
                    repair.workspace_id,
                    row.id,
                    uuid5(operation_id, "conditioning:" + context_hash),
                    UUID(actor_id) if actor_id else None,
                    metadata={
                        "parentOperationId": str(operation_id),
                        "contextHash": context_hash,
                        "subject": snapshot["subject"],
                        "stage": "conditioning",
                    },
                )
            check = {
                "phase": "invoking",
                "startedAt": now_iso(),
                "contextHash": context_hash,
                "operationId": str(operation_id),
                "subject": snapshot["subject"],
            }
            await _persist(repair, project_id, image, image_binding, context_hash, check)
            try:
                output = await inspect(
                    subject=copy.deepcopy(snapshot["subject"]),
                    media=media,
                    references=references,
                    constraints=constraints,
                    invoke_model=_model_adapter(invoke),
                )
                report = _validate(output, snapshot, media, references, constraints)
            except Exception as exc:
                code = getattr(exc, "code", "SMART_REMAKE_CONDITIONING_RECONCILIATION_REQUIRED")
                await _persist(
                    repair,
                    project_id,
                    image,
                    image_binding,
                    context_hash,
                    {
                        **check,
                        "phase": "retryable" if code in PREFLIGHT_ERRORS else "unknown",
                        "errorCode": code,
                    },
                )
                if isinstance(exc, AppError) and code in PREFLIGHT_ERRORS:
                    raise
                if (
                    isinstance(exc, AppError)
                    and exc.code == "SMART_REMAKE_CONDITIONING_REPORT_INVALID"
                ):
                    raise
                raise _error(
                    "RECONCILIATION_REQUIRED", "The conditioning check needs reconciliation."
                ) from exc
            report = {
                **report,
                "stage": "conditioning",
                "operationId": str(operation_id),
                "actorId": actor_id,
                "contextHash": context_hash,
                "conditioningImageRequestHash": image["requestHash"],
            }
            stale = await _persist(
                repair,
                project_id,
                image,
                image_binding,
                context_hash,
                {
                    **check,
                    "phase": "completed",
                    "reportId": report["id"],
                    "status": report["status"],
                    "completedAt": now_iso(),
                },
                report,
            )
            if stale:
                raise _error("STALE", "The saved conditioning context changed while checking.")
        if report["status"] != "passed":
            raise _error("BLOCKED", "Repair the conditioning image before generating video.")
        # Recheck stop-use/rights and close the cached-report read transaction
        # before the caller uploads provider references.
        await require_generation_policy(repair, row)
        results.append(
            {**image, "conditioningReportId": report["id"], "conditioningContextHash": context_hash}
        )
    return results
