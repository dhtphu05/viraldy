"""Retain real offline integration bytes/provenance before disposable services exit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


async def retain_browser_capture(journey: Any, case: str) -> Path:
    root = journey.stack.root / f"capture-{case}"
    root.mkdir(exist_ok=True)
    response = await journey.page.context.request.get(
        f"{journey.root}/projects/{journey.project_id}/provenance"
    )
    assert response.status == 200
    provenance = (await response.json())["data"]
    project = await journey.project()
    (root / "server-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    artifacts: dict[str, dict[str, Any]] = {}
    for role in ("source", "product"):
        source = journey.stack.media[role]
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        target = root / f"{role}-{digest}{source.suffix}"
        target.write_bytes(data)
        artifacts[digest] = {"role": role, "path": target.name, "mediaHash": digest}
    for item in project.get("inspectionMedia", []):
        digest = item["mediaHash"]
        if digest in artifacts:
            continue
        response = await journey.page.context.request.get(item["url"])
        assert response.status == 200, "Authorized capture media was unavailable"
        data = await response.body()
        assert hashlib.sha256(data).hexdigest() == digest, "Capture bytes changed"
        clock = item["timebase"]
        suffix = ".png" if clock == "image" else ".mp4"
        target = root / f"{clock}-{digest}{suffix}"
        target.write_bytes(data)
        artifacts[digest] = {
            "role": {"raw_group": "raw", "final": "final"}.get(clock, clock),
            "path": target.name,
            "mediaHash": digest,
            "frameCount": item.get("frameCount"),
            "timebase": clock,
        }
    manifest = {
        "mode": "mock",
        "providerBoundary": "offline constructors",
        "case": case,
        "projectId": journey.project_id,
        "artifacts": list(artifacts.values()),
        "requirements": provenance["requirements"],
        "timeline": provenance["timeline"],
        "sourceRightsManifest": json.loads(journey.stack.media["manifest"].read_text()),
    }
    (root / "browser-capture.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return root
