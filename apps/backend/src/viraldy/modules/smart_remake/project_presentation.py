"""Public project projections never disclose private object keys or provider payloads."""

from __future__ import annotations

import copy
import re
from typing import Any, cast

from .source_audio import normalize_source_audio

_PRIVATE = {
    "storageKey",
    "sourceKey",
    "productKey",
    "characterKey",
    "finalStorageKey",
    "stateSnapshot",
    "contextSnapshot",
    "retainedMediaKeys",
    "generationExpectations",
    "expectations",
    "sourceOpeningFrames",
    "requirementsSnapshot",
}


def without_storage_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: without_storage_keys(item) for key, item in value.items() if key not in _PRIVATE
        }
    if isinstance(value, list):
        return [without_storage_keys(item) for item in value]
    return copy.deepcopy(value)


def _input_media_hashes(context: dict[str, Any]) -> dict[str, Any] | None:
    assets = (context.get("p0") or {}).get("assets") or {}
    result = {}
    for role in ("source", "product", "character"):
        asset = assets.get(role)
        if role == "character" and asset is None:
            continue
        media_hash = asset.get("mediaHash") if isinstance(asset, dict) else None
        if (
            not isinstance(media_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", media_hash) is None
            or context.get(f"{role}MediaHash") != media_hash
        ):
            return None
        result[role] = media_hash
    additional = (context.get("p0") or {}).get("additionalProductReferences") or []
    if additional:
        digests = [asset.get("mediaHash") for asset in additional]
        if any(not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
               for value in digests):
            return None
        return {**result, "additionalProducts": digests}
    return result


def project_policy_fields(context: dict[str, Any]) -> dict[str, Any]:
    p0 = context.get("p0") or {}
    budget = p0.get("budgetPolicy") or {}
    public_budget = (
        {"mode": "unlimited"} if not budget or budget.get("mode") == "unlimited" else budget
    )
    reports = (p0.get("inspections") or {}).get("reports", [])
    summary = p0.get("inspectionSummary") or {}
    analysis = context.get("referenceAnalysis")
    audio = (
        normalize_source_audio(analysis.get("sourceAudio")) if isinstance(analysis, dict) else None
    )
    return cast(
        dict[str, Any],
        without_storage_keys(
            {
                "inputMediaHashes": _input_media_hashes(context),
                "expectationsHash": (
                    None if context.get("expectationsStale") else context.get("expectationsHash")
                ),
                "expectationsVersion": (context.get("generationExpectations") or {}).get(
                    "schemaVersion"
                ),
                "constraintsHash": p0.get("constraintsHash"),
                "requirements": p0.get("requirements", {}),
                "rights": p0.get("rights", {}),
                "budget": {"policy": public_budget},
                "inspectionSummary": {
                    **summary,
                    "reports": reports,
                    "reviews": (p0.get("inspections") or {}).get("reviews", []),
                },
                "assemblies": p0.get("assemblies", {"records": [], "activeAssemblyId": None}),
                "release": p0.get("release", {"activeApprovalId": None}),
                "deletion": p0.get("deletion"),
                **({"sourceAudio": audio} if audio else {}),
            }
        ),
    )
