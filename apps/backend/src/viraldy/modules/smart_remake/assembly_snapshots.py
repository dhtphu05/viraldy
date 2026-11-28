"""Immutable assembly snapshots; callers persist returned metadata atomically."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any
from uuid import uuid4

from viraldy.shared.errors.base import AppError

from .generation_expectations import (
    build_generation_expectations,
    expectations_hash,
    validate_generation_expectations,
)
from .repair_media import now_iso


def content_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def retained_expectations(value: dict[str, Any]) -> dict[str, Any] | None:
    """Read only the snapshot retained with this exact operation/version."""
    metadata = value.get("providerMetadata") or {}
    snapshot = value.get("generationExpectations", metadata.get("generationExpectations"))
    binding = value.get("expectationsHash", metadata.get("expectationsHash"))
    if snapshot is None and binding is None:
        return None
    if snapshot is None or not binding:
        raise AppError(
            "SMART_REMAKE_EXPECTATIONS_REQUIRED", "The retained snapshot is incomplete.", 409
        )
    return validate_generation_expectations(snapshot, binding)


def assembly_expectations(
    timeline: dict[str, Any],
    state: dict[str, Any],
    context: dict[str, Any],
    *,
    historical: bool = False,
) -> dict[str, Any]:
    """Bind selected scene intent to exact versions/ranges without an AI invocation."""
    base: dict[str, Any] | None = None
    selected = []
    try:
        for item in timeline["items"]:
            scene = next(s for s in state["scenes"] if s["id"] == item["renderUnitId"])
            version = next(v for v in scene["versions"] if v["id"] == item["versionId"])
            snapshot = retained_expectations(version)
            if snapshot is None:
                if not historical:
                    raise ValueError("The selected version has no frozen generation snapshot.")
                snapshot = build_generation_expectations(context)
            if any(not s["openingFrame"]["layoutHash"] for s in snapshot["scenes"]):
                raise ValueError("The opening reference is missing.")
            if base is None:
                base = copy.deepcopy(snapshot)
            if any(snapshot[key] != base[key] for key in ("productLock", "references")):
                raise ValueError("Selected clips have incompatible product references.")
            if snapshot.get("productReferenceHashes") != base.get("productReferenceHashes"):
                raise ValueError("Selected clips have incompatible product views.")
            expectation = copy.deepcopy(
                next(s for s in snapshot["scenes"] if s["renderUnitId"] == item["renderUnitId"])
            )
            if expectation["sourceSceneId"] != item["sourceSceneId"]:
                raise ValueError("The selected source scene changed.")
            expectation["selection"] = {
                "versionId": item["versionId"],
                "inFrame": item["inFrame"],
                "outFrame": item["outFrame"],
                "timebase": "raw_group",
            }
            selected.append(expectation)
        if base is None:
            raise ValueError("An assembly needs selected scenes.")
        assets = context.get("p0", {}).get("assets", {})
        if any(
            assets.get(role, {}).get("mediaHash") != ref["mediaHash"]
            for role, ref in base["references"].items()
        ):
            raise ValueError("The product/source references changed.")
        current = build_generation_expectations(context)
        if current.get("productReferenceHashes") != base.get("productReferenceHashes"):
            raise ValueError("The product views changed.")
        if current["productLock"] != base["productLock"]:
            raise AppError(
                "SMART_REMAKE_EXPECTATIONS_REQUIRED",
                "The product facts changed. Update the scene plan before reusing these clips.",
                409,
            )
        return validate_generation_expectations(
            {
                **base,
                "requirements": current["requirements"],
                "requirementsHash": current["requirementsHash"],
                "scenes": selected,
            }
        )
    except (AppError, KeyError, StopIteration, TypeError, ValueError) as exc:
        if isinstance(exc, AppError) and exc.code == "SMART_REMAKE_EXPECTATIONS_REQUIRED":
            raise
        raise AppError(
            "SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED",
            "Assemble a new preview from retained scene snapshots before checking it.",
            409,
        ) from exc


def assembly_manifest(timeline: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Freeze exact selected versions/ranges, including shared raw clip identity."""
    selections = []
    try:
        for item in timeline["items"]:
            scene = next(s for s in state["scenes"] if s["id"] == item["renderUnitId"])
            version = next(v for v in scene["versions"] if v["id"] == item["versionId"])
            selections.append(
                {
                    "renderUnitId": scene["id"],
                    "versionId": version["id"],
                    "mediaHash": version["mediaHash"],
                    "storageKey": version["storageKey"],
                    **(
                        {"expectationsHash": version["expectationsHash"]}
                        if version.get("expectationsHash")
                        else {}
                    ),
                }
            )
        if not selections:
            raise ValueError("Empty selection")
    except (KeyError, StopIteration, TypeError, ValueError) as exc:
        raise AppError(
            "SMART_REMAKE_ASSEMBLY_MANIFEST_INVALID",
            "The assembly must bind retained scene versions.",
        ) from exc
    return copy.deepcopy({"schemaVersion": 1, "timeline": timeline, "selections": selections})


def active_assembly(p0: dict[str, Any]) -> dict[str, Any]:
    assemblies = p0.get("assemblies", {})
    return get_assembly(p0, assemblies.get("activeAssemblyId"))


def get_assembly(p0: dict[str, Any], assembly_id: str | None) -> dict[str, Any]:
    for record in p0.get("assemblies", {}).get("records", []):
        if record["id"] == assembly_id:
            return copy.deepcopy(record)
    raise AppError("SMART_REMAKE_ASSEMBLY_NOT_FOUND", "The requested assembly was not found.", 404)


def invalidate_release(p0: dict[str, Any], reason: str) -> dict[str, Any]:
    result = copy.deepcopy(p0)
    release = result.setdefault("release", {"approvals": [], "exports": []})
    release.update(activeApprovalId=None, invalidatedAt=now_iso(), invalidationReason=reason)
    return result


def _append(p0: dict[str, Any], record: dict[str, Any], action: str) -> dict[str, Any]:
    result = invalidate_release(p0, action)
    assemblies = result.setdefault("assemblies", {"schemaVersion": 1, "records": [], "history": []})
    assemblies["records"].append(record)
    assemblies["activeAssemblyId"] = record["id"]
    assemblies["history"].append(
        {
            "id": str(uuid4()),
            "action": action,
            **{
                key: record[key]
                for key in (
                    "parentAssemblyId",
                    "operationId",
                    "actorId",
                    "revision",
                    "createdAt",
                )
            },
            "assemblyId": record["id"],
        }
    )
    return result


def record_assembly(
    p0: dict[str, Any],
    *,
    project_id: str,
    timeline: dict[str, Any],
    state: dict[str, Any],
    storage_key: str,
    media_hash: str,
    technical_check: dict[str, Any],
    constraints_hash: str,
    context_hash: str,
    revision: int,
    actor_id: str,
    operation_id: str,
    context: dict[str, Any] | None = None,
    review_mode: str | None = None,
) -> dict[str, Any]:
    manifest = assembly_manifest(timeline, state)
    expectations = (
        assembly_expectations(timeline, state, context)
        if context and context.get("generationExpectations")
        else None
    )
    for record in p0.get("assemblies", {}).get("records", []):
        if record["operationId"] == operation_id:
            if (
                record["mediaHash"] != media_hash
                or record["manifestHash"] != content_hash(manifest)
                or (
                    expectations is not None
                    and record.get("expectationsHash") != expectations_hash(expectations)
                )
            ):
                raise AppError(
                    "SMART_REMAKE_ASSEMBLY_OPERATION_CONFLICT", "This operation changed.", 409
                )
            return copy.deepcopy(p0)
    record = {
        "id": str(uuid4()),
        "projectId": str(project_id),
        "schemaVersion": 1,
        "parentAssemblyId": p0.get("assemblies", {}).get("activeAssemblyId"),
        "manifest": manifest,
        "manifestHash": content_hash(manifest),
        "timeline": copy.deepcopy(timeline),
        "stateSnapshot": copy.deepcopy(
            {key: state[key] for key in ("scenes", "sourceSceneMap", "renderPlan") if key in state}
        ),
        "contextSnapshot": copy.deepcopy(
            {
                "requirementsSnapshot": (context or {}).get("p0", {}).get("requirements"),
                **{
                    key: (context or {})[key]
                    for key in (
                        "sceneMap",
                        "productLock",
                        "referenceAnalysis",
                        "sourceSceneMap",
                        "renderPlan",
                        "compileResult",
                        "sourceThumbnailKeys",
                        "sourceOpeningFrames",
                        "generationExpectations",
                        "expectationsHash",
                        "sourceMediaHash",
                        "productMediaHash",
                        "characterMediaHash",
                        "expectationsStale",
                    )
                    if key in (context or {})
                },
            }
        ),
        "storageKey": storage_key,
        "mediaHash": media_hash,
        "technicalCheck": copy.deepcopy(technical_check),
        "constraintsHash": constraints_hash,
        "contextHash": context_hash,
        "revision": revision,
        "actorId": str(actor_id),
        "operationId": str(operation_id),
        "createdAt": now_iso(),
        **({"reviewMode": review_mode} if review_mode == "whole_video" else {}),
        **(
            {
                "generationExpectations": expectations,
                "expectationsHash": expectations_hash(expectations),
            }
            if expectations
            else {}
        ),
    }
    return _append(p0, record, "compose")


def restore_assembly(
    p0: dict[str, Any], *, assembly_id: str, actor_id: str, revision: int, operation_id: str
) -> dict[str, Any]:
    for existing in p0.get("assemblies", {}).get("records", []):
        if existing["operationId"] == operation_id:
            if existing.get("restoredFromAssemblyId") != assembly_id:
                raise AppError(
                    "SMART_REMAKE_ASSEMBLY_OPERATION_CONFLICT", "This operation changed.", 409
                )
            return copy.deepcopy(p0)
    record = get_assembly(p0, assembly_id)
    record.update(
        id=str(uuid4()),
        restoredFromAssemblyId=assembly_id,
        parentAssemblyId=p0["assemblies"]["activeAssemblyId"],
        actorId=str(actor_id),
        revision=revision,
        operationId=operation_id,
        createdAt=now_iso(),
    )
    return _append(p0, record, "restore")
