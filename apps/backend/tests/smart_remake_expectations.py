"""Explicit canonical metadata for positive, offline Smart Remake test fixtures.

Never use this helper on legacy reconciliation or invalid-input fixtures: it models
a successful source/product analysis and an explicitly mocked opening extractor.
The caller's media double must return the source/product bytes supplied here.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from viraldy.modules.smart_remake.generation_expectations import (
    OPENING_EXTRACTOR_VERSION,
    build_generation_expectations,
    expectations_hash,
)


def fixture_opening_bytes(source_scene_id: str) -> bytes:
    return f"mock-opening:{source_scene_id}".encode()


def install_expectations(
    context: dict[str, Any],
    *,
    state: dict[str, Any] | None = None,
    source_bytes: bytes = b"source",
    product_bytes: bytes = b"product",
) -> dict[str, Any]:
    """Install the explicit successful-analysis state used by fresh-work unit tests."""
    state = state if state is not None else {}
    for role, data in (("source", source_bytes), ("product", product_bytes)):
        digest = hashlib.sha256(data).hexdigest()
        context[f"{role}MediaHash"] = digest
        asset = (context.get("p0", {}).get("assets") or {}).get(role)
        if asset is not None:
            asset["mediaHash"] = digest
    lock = context.setdefault("productLock", {})
    lock.setdefault("productName", "Observed seller bottle")
    lock.setdefault("productType", "bottle")
    if not lock.get("visualIdentity"):
        lock["visualIdentity"] = {"colors": ["blue"], "shape": "cylindrical"}
    context.setdefault("referenceAnalysis", {})
    plan = context.setdefault("renderPlan", {})
    if not plan.get("units"):
        items = state.get("draftTimeline", {}).get("items") or []
        plan["units"] = [
            {
                "id": item["renderUnitId"],
                "sourceSceneId": item["sourceSceneId"],
                "sceneIndex": index,
                "targetDurationFrames": item["targetDurationFrames"],
                "rawDurationFrames": 192,
            }
            for index, item in enumerate(items)
        ]
    units = plan["units"]
    sources = context.setdefault("sourceSceneMap", {}).setdefault("scenes", [])
    by_source = {source["id"]: source for source in sources}
    cursor = 0
    openings = context.setdefault("sourceOpeningFrames", {})
    for index, unit in enumerate(units):
        source_id = unit.setdefault("sourceSceneId", f"source-{index}")
        if source_id not in by_source:
            source = {
                "id": source_id,
                "startFrame": cursor,
                "endFrame": cursor + unit.get("targetDurationFrames", 192),
            }
            sources.append(source)
            by_source[source_id] = source
        source = by_source[source_id]
        cursor = source["endFrame"]
        openings.setdefault(
            source_id,
            {
                "sourceMediaHash": context["sourceMediaHash"],
                "frame": source["startFrame"],
                "layoutHash": hashlib.sha256(fixture_opening_bytes(source_id)).hexdigest(),
                "extractorVersion": OPENING_EXTRACTOR_VERSION,
            },
        )
    if not (context.get("sceneMap") or {}).get("scenes"):
        context["sceneMap"] = {
            "scenes": [
                {
                    **copy.deepcopy(unit),
                    **dict.fromkeys(
                        ("prompt", "imagePrompt", "videoPrompt"),
                        "Keep the observed seller product and source action.",
                    ),
                }
                for unit in units
            ]
        }
    snapshot = build_generation_expectations(context)
    digest = expectations_hash(snapshot)
    context.update(generationExpectations=snapshot, expectationsHash=digest)
    context.pop("expectationsStale", None)
    for scene in state.get("scenes", []):
        for version in scene.get("versions", []):
            version.update(generationExpectations=copy.deepcopy(snapshot), expectationsHash=digest)
            version.setdefault("providerMetadata", {}).update(
                generationExpectations=copy.deepcopy(snapshot), expectationsHash=digest
            )
    return snapshot
