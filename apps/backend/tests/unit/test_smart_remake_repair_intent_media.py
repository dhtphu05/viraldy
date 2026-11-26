from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.smart_remake_expectations import fixture_opening_bytes
from tests.unit.test_smart_remake_repair_intent import prepared
from viraldy.modules.smart_remake import repair_intent_media
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.shared.errors.base import AppError


@pytest.mark.asyncio
@pytest.mark.parametrize("selected", [True, False])
async def test_evidence_binds_owned_references_and_exact_active_clip_range(monkeypatch, selected):
    row, scene = prepared()
    clip = b"active-owned-clip"
    version = scene["versions"][0]
    version.update(storageKey="active", mediaHash=hashlib.sha256(clip).hexdigest())
    if not selected:
        row.state_json["draftTimeline"]["items"] = []
        version.update(suggestedInFrame=48, suggestedOutFrame=120)
    trimmed = []

    async def references(*args):
        return UploadedMedia(bytes=b"product", mime_type="image/png"), UploadedMedia(
            bytes=fixture_opening_bytes("source"), mime_type="image/png"
        )

    async def read(key):
        assert key == "active"
        return clip

    def trim(data, start, end):
        trimmed.append((data, start, end))
        return b"exact-excerpt"

    monkeypatch.setattr(repair_intent_media, "_references", references)
    monkeypatch.setattr(repair_intent_media, "probe_timeline_media", lambda _: {"frameCount": 192})
    monkeypatch.setattr(repair_intent_media, "trim_repair_evidence", trim)
    media, binding = await repair_intent_media.repair_evidence(
        SimpleNamespace(media=SimpleNamespace(read=read)), row, scene
    )
    start, end = (24, 96) if selected else (48, 120)
    assert trimmed == [(clip, start, end)]
    assert binding["inFrame"] == start and binding["outFrame"] == end
    assert media[-1] == {"bytes": b"exact-excerpt", "mime_type": "video/mp4"}
    assert binding["evidenceHashes"] == [
        hashlib.sha256(item["bytes"]).hexdigest() for item in media
    ]


@pytest.mark.asyncio
async def test_changed_owned_clip_is_rejected_before_evidence_decode(monkeypatch):
    row, scene = prepared()
    scene["versions"][0].update(storageKey="active", mediaHash="a" * 64)

    async def references(*args):
        return UploadedMedia(bytes=b"product", mime_type="image/png"), UploadedMedia(
            bytes=fixture_opening_bytes("source"), mime_type="image/png"
        )

    async def read(key):
        return b"changed"

    monkeypatch.setattr(repair_intent_media, "_references", references)
    with pytest.raises(AppError, match="SMART_REMAKE_MEDIA_CHANGED"):
        await repair_intent_media.repair_evidence(
            SimpleNamespace(media=SimpleNamespace(read=read)), row, scene
        )


@pytest.mark.asyncio
async def test_product_evidence_must_match_snapshot_even_if_context_digest_is_missing(monkeypatch):
    row, scene = prepared()
    row.context_json.pop("productMediaHash", None)
    row.context_json.setdefault("p0", {}).setdefault("assets", {})["product"] = {
        "mediaHash": hashlib.sha256(b"product").hexdigest(),
    }

    async def references(*args):
        return UploadedMedia(bytes=b"changed product", mime_type="image/png"), UploadedMedia(
            bytes=fixture_opening_bytes("source"), mime_type="image/png"
        )

    monkeypatch.setattr(repair_intent_media, "_references", references)
    with pytest.raises(AppError, match="SMART_REMAKE_INPUT_CHANGED"):
        await repair_intent_media.repair_evidence(SimpleNamespace(), row, scene)


def test_trim_evidence_uses_exact_canonical_frames_without_shell(monkeypatch):
    observed = []

    def run(argv, **kwargs):
        observed.append((argv, kwargs))
        Path(argv[-1]).write_bytes(b"trimmed")

    monkeypatch.setattr(repair_intent_media.subprocess, "run", run)
    assert repair_intent_media.trim_repair_evidence(b"raw", 24, 96) == b"trimmed"
    argv, kwargs = observed[0]
    assert "fps=24,trim=start_frame=24:end_frame=96,setpts=PTS-STARTPTS" in argv
    assert argv[argv.index("-frames:v") + 1] == "72"
    assert "shell" not in kwargs
