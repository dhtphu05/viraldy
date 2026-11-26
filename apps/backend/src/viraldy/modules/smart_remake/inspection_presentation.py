"""Current report bindings and authorized evidence previews for the Inspector UI."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from viraldy.shared.errors.base import AppError

from .inspection_service import InspectionSubjectRequest, _context_hash, _snapshot


def inspection_clock_fields(
    row: Any, workspace_id: UUID, previews: list[dict[str, Any]]
) -> dict[str, Any]:
    from .inspection_mappings import inspection_mapping_projection

    projection = inspection_mapping_projection(row, workspace_id)
    media = list(previews)
    for virtual in projection["virtualMedia"]:
        raw = next(
            (item for item in previews
             if item["mediaId"] == virtual["playbackMediaId"]
             and item["mediaHash"] == virtual["playbackMediaHash"]
             and item["timebase"] == virtual["playbackTimebase"]
             and item.get("url")),
            None,
        )
        if raw:
            media.append({**virtual, "url": raw["url"]})
    bindings = {(item["mediaId"], item["mediaHash"], item["timebase"]) for item in media}
    mappings = [
        mapping for mapping in projection["inspectionMappings"]
        if all((mapping[end]["mediaId"], mapping[end]["mediaHash"], mapping[end]["timebase"])
               in bindings for end in ("from", "to"))
    ]
    return {"inspectionMedia": media, "inspectionMappings": mappings}


def current_report_ids(row: Any, workspace_id: UUID) -> list[str]:
    p0 = row.context_json["p0"]
    active = p0.get("assemblies", {}).get("activeAssemblyId")
    current = []
    for report in p0.get("inspections", {}).get("reports", []):
        try:
            request = InspectionSubjectRequest.model_validate(report.get("subjectRequest"))
            if request.kind == "assembly" and request.assemblyId != active:
                continue
            snapshot = _snapshot(row, request, workspace_id)
            if report.get("contextHash") == _context_hash(snapshot):
                current.append(report["id"])
        except (AppError, ValueError, TypeError):
            continue
    return current


async def evidence_previews(row: Any, media: Any, workspace_id: UUID) -> list[dict[str, Any]]:
    p0 = row.context_json["p0"]
    prefix = f"workspaces/{workspace_id}/smart-remake/"
    candidates: list[tuple[str, dict[str, Any], str, int | None]] = []
    for role, asset in p0.get("assets", {}).items():
        candidates.append(
            (
                role,
                asset,
                "source" if role == "source" else "image",
                row.context_json.get("sourceFrameCount") if role == "source" else None,
            )
        )
        if role in {"product", "character"}:
            candidates.append(("subject", asset, "image", None))
    states = [row.state_json]
    states.extend(record.get("stateSnapshot", {}) for record in p0.get("planHistory", []))
    for assembly in p0.get("assemblies", {}).get("records", []):
        frame_count = (assembly.get("timeline") or {}).get("totalFrames")
        if type(frame_count) is int and frame_count > 0:
            candidates.append(("subject", assembly, "final", frame_count))
        states.append(assembly.get("stateSnapshot", {}))
    for state in states:
        for scene in state.get("scenes", []):
            for version in scene.get("versions", []):
                for identity in ("subject", f"neighbor-{scene['id']}"):
                    candidates.append((identity, version, "raw_group", version.get("frameCount")))
    result, seen, urls = [], set(), {}
    for identity, asset, clock, frame_count in candidates:
        key, digest = asset.get("storageKey"), asset.get("mediaHash")
        binding = (identity, digest, clock)
        if (
            binding in seen
            or not isinstance(key, str)
            or not key.startswith(prefix)
            or not isinstance(digest, str)
        ):
            continue
        seen.add(binding)
        if key not in urls:
            urls[key] = await media.url(key)
        result.append(
            {
                "mediaId": identity,
                "mediaHash": digest,
                "timebase": clock,
                "frameCount": frame_count,
                "url": urls[key],
            }
        )
    return result
