"""Exact edit-clock projections from retained reports and immutable assemblies only.

These edges describe edits, never semantic correspondence between source and output.
Virtual scene clocks have no media URL: callers must resolve their explicit playback
identity and convert the selected local range before using the raw media URL.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from .assembly_snapshots import content_hash


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _bounds(start: Any, end: Any, count: Any) -> bool:
    return (
        type(start) is int and type(end) is int and type(count) is int and 0 <= start < end <= count
    )


def _owned(value: dict[str, Any], prefix: str) -> bool:
    key = value.get("storageKey")
    return isinstance(key, str) and key.startswith(prefix) and _digest(value.get("mediaHash"))


def _version_index(state: dict[str, Any], prefix: str) -> dict[tuple[str, str], dict[str, Any]]:
    versions: dict[tuple[str, str], dict[str, Any]] = {}
    if not isinstance(state, dict) or not isinstance(state.get("scenes", []), list):
        return versions
    for scene in state.get("scenes", []):
        if not isinstance(scene, dict) or not _identifier(scene.get("id")):
            continue
        if not isinstance(scene.get("versions", []), list):
            continue
        for version in scene.get("versions", []):
            if (
                isinstance(version, dict)
                and _identifier(version.get("id"))
                and _owned(version, prefix)
                and type(version.get("frameCount")) is int
                and version["frameCount"] > 0
            ):
                versions[(scene["id"], version["id"])] = version
    return versions


def _retained_versions(row: Any, prefix: str) -> dict[tuple[str, str], dict[str, Any]]:
    p0 = _object(row.context_json.get("p0"))
    states = [row.state_json]
    states.extend(item.get("stateSnapshot", {}) for item in _records(p0.get("planHistory")))
    states.extend(
        item.get("stateSnapshot", {})
        for item in _records(_object(p0.get("assemblies")).get("records"))
    )
    versions: dict[tuple[str, str], dict[str, Any]] = {}
    ambiguous: set[tuple[str, str]] = set()
    for state in states:
        for identity, version in _version_index(state, prefix).items():
            existing = versions.get(identity)
            if existing and any(
                existing[key] != version[key] for key in ("storageKey", "mediaHash", "frameCount")
            ):
                ambiguous.add(identity)
            versions[identity] = version
    return {
        identity: version for identity, version in versions.items() if identity not in ambiguous
    }


def _span(media_id: str, digest: str, clock: str, start: int, end: int) -> dict[str, Any]:
    return {
        "mediaId": media_id,
        "mediaHash": digest,
        "timebase": clock,
        "inFrame": start,
        "outFrame": end,
    }


def _assembly_segments(
    assembly: dict[str, Any], project_id: str, prefix: str
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Require the frozen manifest, selections and decoded raw bounds to agree."""
    try:
        if (
            assembly.get("schemaVersion") != 1
            or assembly.get("projectId") != project_id
            or not _identifier(assembly.get("id"))
            or not _owned(assembly, prefix)
            or not _digest(assembly.get("manifestHash"))
        ):
            return []
        timeline, manifest = _object(assembly.get("timeline")), _object(assembly.get("manifest"))
        if not isinstance(assembly.get("technicalCheck"), dict):
            return []
        if (
            timeline.get("fps") != 24
            or type(timeline.get("fps")) is not int
            or type(timeline.get("totalFrames")) is not int
            or timeline.get("totalFrames") not in (192, 288, 384)
            or manifest["timeline"] != timeline
            or content_hash(manifest) != assembly["manifestHash"]
        ):
            return []
        count = assembly.get("technicalCheck", {}).get("frameCount")
        if count is not None and (type(count) is not int or count != timeline["totalFrames"]):
            return []
        versions = _version_index(assembly["stateSnapshot"], prefix)
        items, selections = timeline["items"], manifest["selections"]
        if not items or len(items) != len(selections):
            return []
        result: list[tuple[dict[str, Any], dict[str, Any]]] = []
        end = 0
        seen: set[str] = set()
        for item, selection in zip(items, selections, strict=True):
            scene, version_id = item["renderUnitId"], item["versionId"]
            version = versions[(scene, version_id)]
            length = item["targetDurationFrames"]
            if (
                not _identifier(item["id"])
                or item["id"] in seen
                or scene in seen
                or type(length) is not int
                or not 0 < length <= 192
                or type(item["targetStartFrame"]) is not int
                or item["targetStartFrame"] != end
                or not _bounds(item["inFrame"], item["outFrame"], version["frameCount"])
                or item["outFrame"] - item["inFrame"] != length
                or selection
                != {
                    "renderUnitId": scene,
                    "versionId": version_id,
                    "mediaHash": version["mediaHash"],
                    "storageKey": version["storageKey"],
                    **(
                        {"expectationsHash": version["expectationsHash"]}
                        if version.get("expectationsHash")
                        else {}
                    ),
                }
            ):
                return []
            seen.update((item["id"], scene))
            end += length
            result.append((item, version))
        return result if end == timeline["totalFrames"] else []
    except (KeyError, TypeError, ValueError):
        return []


def inspection_mapping_projection(row: Any, workspace_id: UUID) -> dict[str, list[dict[str, Any]]]:
    """Return edit edges plus URL-free virtual descriptors for authorized preview joining.

    ``reportId`` identifies a saved scene report's exact old range. ``assemblyId``
    identifies a frozen final edit. No edge inherits a newer draft's trim. Overlapping
    shared raw clips still have separate virtual IDs for every scene/context/version.
    The optional metadata on each edge lets consumers select that precise context.
    """
    projection: dict[str, list[dict[str, Any]]] = {"inspectionMappings": [], "virtualMedia": []}
    if getattr(row, "workspace_id", None) != workspace_id or getattr(row, "id", None) is None:
        return projection
    p0 = _object(row.context_json.get("p0"))
    if p0.get("status") in {"suspended", "deleted"}:
        return projection
    prefix = f"workspaces/{workspace_id}/smart-remake/"
    project_id = str(row.id)
    versions = _retained_versions(row, prefix)
    reports = _records(_object(p0.get("inspections")).get("reports"))
    descriptors: dict[str, dict[str, Any]] = {}

    def selected(version: dict[str, Any], start: int, end: int, metadata: dict[str, Any]) -> None:
        digest = version["mediaHash"]
        physical = _span("subject", digest, "raw_group", start, end)
        local_id = "scene-local:" + content_hash({"selection": physical, **metadata})
        local = _span(local_id, digest, "scene_local", 0, end - start)
        descriptors[local_id] = {
            "mediaId": local_id,
            "mediaHash": digest,
            "timebase": "scene_local",
            "frameCount": end - start,
            "playbackTimebase": "raw_group",
            "playbackMediaId": "subject",
            "playbackMediaHash": digest,
            **metadata,
        }
        for media_id in ("subject", "neighbor-" + metadata["sceneId"]):
            projection["inspectionMappings"].append(
                {"from": dict(local), "to": {**physical, "mediaId": media_id}, **metadata}
            )

    for report in reports:
        if not isinstance(report, dict) or not isinstance(report.get("subject"), dict):
            continue
        subject = report["subject"]
        bounds = subject.get("range") or {}
        if not isinstance(bounds, dict):
            continue
        if (
            report.get("schemaVersion") != 1
            or report.get("stage") == "conditioning"
            or subject.get("kind") != "scene"
            or subject.get("projectId") != project_id
            or not _identifier(report.get("id"))
            or not _digest(report.get("contextHash"))
            or not _digest(report.get("manifestHash"))
            or bounds.get("timebase") != "raw_group"
            or type(bounds.get("fps")) is not int
            or bounds.get("fps") != 24
            or not _identifier(subject.get("sceneId"))
            or not _identifier(subject.get("versionId"))
        ):
            continue
        identity = (subject.get("sceneId"), subject.get("versionId"))
        version = versions.get(identity)
        if (
            version is None
            or subject.get("mediaHash") != version["mediaHash"]
            or not _bounds(bounds.get("inFrame"), bounds.get("outFrame"), version["frameCount"])
        ):
            continue
        selected(
            version,
            bounds["inFrame"],
            bounds["outFrame"],
            {
                "reportId": report["id"],
                "contextHash": report["contextHash"],
                "manifestHash": report["manifestHash"],
                "sceneId": identity[0],
                "versionId": identity[1],
            },
        )

    for assembly in _records(_object(p0.get("assemblies")).get("records")):
        segments = _assembly_segments(assembly, project_id, prefix)
        for item, version in segments:
            metadata = {
                "assemblyId": assembly["id"],
                "manifestHash": assembly["manifestHash"],
                "sceneId": item["renderUnitId"],
                "versionId": item["versionId"],
            }
            if _digest(assembly.get("contextHash")):
                metadata["contextHash"] = assembly["contextHash"]
            selected(version, item["inFrame"], item["outFrame"], metadata)
            projection["inspectionMappings"].append(
                {
                    "from": _span(
                        "subject",
                        assembly["mediaHash"],
                        "final",
                        item["targetStartFrame"],
                        item["targetStartFrame"] + item["targetDurationFrames"],
                    ),
                    "to": _span(
                        "subject",
                        version["mediaHash"],
                        "raw_group",
                        item["inFrame"],
                        item["outFrame"],
                    ),
                    **metadata,
                }
            )
    projection["virtualMedia"] = list(descriptors.values())
    return projection
