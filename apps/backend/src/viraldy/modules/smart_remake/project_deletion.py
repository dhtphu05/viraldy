"""Project-owned deletion inventory and verifiable private storage removal."""

from __future__ import annotations

import copy
import hashlib
from pathlib import PurePosixPath
from typing import Any, TypeGuard

from starlette.concurrency import run_in_threadpool

from viraldy.platform.storage.ports import StoragePort
from viraldy.shared.errors.base import AppError

from .repair_media import now_iso


def _owned(key: Any, prefix: str) -> TypeGuard[str]:
    return (
        isinstance(key, str)
        and bool(prefix)
        and key.startswith(prefix.rstrip("/") + "/")
        and not any(part in {"..", "."} for part in key.split("/"))
        and not PurePosixPath(key).is_absolute()
        and "://" not in key
        and "?" not in key
        and "#" not in key
    )


def _snapshot_keys(state: dict[str, Any], context: dict[str, Any]) -> list[Any]:
    keys: list[Any] = [state.get("finalStorageKey")]
    keys += [context.get(key) for key in ("sourceKey", "productKey", "characterKey", "musicKey")]
    keys += list(context.get("sourceThumbnailKeys", {}).values())
    keys += [v.get("storageKey") for s in state.get("scenes", []) for v in s.get("versions", [])]
    keys += [v.get("storageKey") for v in context.get("imageAssets", {}).values()]
    return keys


def deletion_inventory(
    state: dict[str, Any], context: dict[str, Any], *, owned_prefix: str
) -> list[dict[str, Any]]:
    """Collect only server-defined media fields, never arbitrary nested client JSON."""
    keys = _snapshot_keys(state, context)
    p0 = context.get("p0", {})
    keys += p0.get("retainedMediaKeys", [])
    keys += [a.get("storageKey") for a in p0.get("conditioningAssets", {}).values()]
    for historical in p0.get("planHistory", []):
        keys += _snapshot_keys(
            historical.get("stateSnapshot", {}), historical.get("contextSnapshot", {})
        )
    keys += [a.get("storageKey") for a in p0.get("assets", {}).values()]
    for assembly in p0.get("assemblies", {}).get("records", []):
        keys.append(assembly.get("storageKey"))
        keys += [
            item.get("storageKey") for item in assembly.get("manifest", {}).get("selections", [])
        ]
        keys += [
            version.get("storageKey")
            for scene in assembly.get("stateSnapshot", {}).get("scenes", [])
            for version in scene.get("versions", [])
        ]
        keys += list(assembly.get("contextSnapshot", {}).get("sourceThumbnailKeys", {}).values())
    keys += [a.get("storageKey") for a in p0.get("release", {}).get("exports", [])]
    result = []
    for key in dict.fromkeys(k for k in keys if isinstance(k, str) and k):
        owned = _owned(key, owned_prefix)
        result.append(
            {
                "keyHash": hashlib.sha256(key.encode()).hexdigest(),
                "status": "pending" if owned else "retained_unowned",
                **({"storageKey": key} if owned else {}),
            }
        )
    return result


def suspend_project(p0: dict[str, Any], *, actor_id: str, reason: str) -> dict[str, Any]:
    result = copy.deepcopy(p0)
    result["status"] = "suspended"
    result["deletion"] = {
        "status": "suspended",
        "actorId": str(actor_id),
        "reason": reason,
        "requestedAt": now_iso(),
        "providerDeletion": "unverified",
    }
    result.setdefault("release", {})["activeApprovalId"] = None
    return result


async def delete_inventory(
    storage: StoragePort,
    inventory: list[dict[str, Any]],
    *,
    owned_prefix: str,
    suspended: bool,
    shared_keys: set[str],
    running_jobs: bool = False,
    retention_required: bool = False,
) -> dict[str, Any]:
    """Caller must commit suspension and resolve cross-project references first."""
    if suspended is not True:
        raise AppError(
            "SMART_REMAKE_DELETION_NOT_SUSPENDED", "Suspend the project before deletion.", 409
        )
    objects = copy.deepcopy(inventory)
    report = {
        "status": "blocked",
        "objects": objects,
        "checkedAt": now_iso(),
        "providerDeletion": "unverified",
    }
    if running_jobs or retention_required:
        report["reason"] = "running_jobs" if running_jobs else "evidence_retention"
        return report
    for item in objects:
        if item["status"] != "pending":
            continue
        key = item.get("storageKey")
        if not _owned(key, owned_prefix):
            item.pop("storageKey", None)
            item["status"] = "retained_unowned"
            continue
        if key in shared_keys:
            item["status"] = "retained_shared"
            continue
        try:
            await run_in_threadpool(storage.delete_object, key)
            exists = await run_in_threadpool(storage.object_exists, key)
            item["status"] = "failed" if exists else "deleted"
            if exists:
                item["errorCode"] = "OBJECT_STILL_EXISTS"
        except Exception as exc:
            item.update(status="failed", errorCode=type(exc).__name__)
    statuses = {item["status"] for item in objects}
    report["status"] = (
        "failed" if "failed" in statuses else "partial" if statuses - {"deleted"} else "completed"
    )
    return report
