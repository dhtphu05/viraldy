from __future__ import annotations

import copy
import hashlib
import subprocess
from io import BytesIO

import pytest
from PIL import Image
from pydantic import ValidationError

from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path
from viraldy.modules.smart_remake.inspection.contracts import InspectionConstraints
from viraldy.modules.smart_remake.inspection.public import inspect_subject, validate_report_binding


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def inputs(tmp_path_factory):
    path = tmp_path_factory.mktemp("inspection-anchors") / "owned.mp4"
    subprocess.run(  # noqa: S603 - fixed encoder with self-authored synthetic media
        [
            ffmpeg_path(),
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=90x160:rate=24:duration=8",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    video = path.read_bytes()
    stream = BytesIO()
    Image.new("RGB", (90, 160), "red").save(stream, format="PNG")
    product = stream.getvalue()
    media = {
        "id": "output",
        "bytes": video,
        "mediaHash": digest(video),
        "mimeType": "video/mp4",
        "frameCount": 192,
        "fps": 24,
    }
    subject = {
        "kind": "scene",
        "projectId": "project",
        "sceneId": "scene",
        "versionId": "version",
        "mediaHash": media["mediaHash"],
        "range": {"inFrame": 24, "outFrame": 96, "fps": 24, "timebase": "raw_group"},
        "neighborVersionIds": [],
    }
    references = [
        {
            "id": "product",
            "bytes": product,
            "mediaHash": digest(product),
            "mimeType": "image/png",
            "role": "product",
        },
        {
            **media,
            "id": "source",
            "role": "source",
            "range": {"inFrame": 48, "outFrame": 120, "fps": 24, "timebase": "source"},
        },
    ]
    constraints = {
        "constraintsHash": digest(b"constraints"),
        "manifestHash": digest(b"manifest"),
        "requirements": {"intent": "Show the red product", "requiresCharacter": False},
        "manifest": {"selection": {"sourceSceneId": "source-scene"}},
        "sourceSceneMap": {"scenes": [{"id": "source-scene", "startFrame": 48, "endFrame": 120}]},
        "technicalCheck": {"status": "passed"},
        "observationAnchors": [],
    }
    return subject, media, references, constraints


def anchor(media, frame=60, timebase="raw_group"):
    return {
        "mediaId": media["id"],
        "mediaHash": media["mediaHash"],
        "timebase": timebase,
        "frame": frame,
    }


async def passing_model(request):
    return {
        "output": {
            "findings": [
                {
                    "requirementId": rule.id,
                    "status": "passed",
                    "observed": "Matches the supplied observations.",
                    "observationIds": [item.id for item in request.observations],
                }
                for rule in request.requirements
            ]
        },
        "modelProfile": {"provider": "fixture", "model": "scripted", "mode": "offline"},
    }


def test_optional_anchor_contract_is_strict_and_defaults_empty(inputs):
    constraints = copy.deepcopy(inputs[3])
    constraints.pop("observationAnchors")
    assert InspectionConstraints.model_validate(constraints).observationAnchors == []
    for invalid in [True, 1.5, -1, "60"]:
        constraints["observationAnchors"] = [anchor(inputs[1], frame=invalid)]
        with pytest.raises(ValidationError):
            InspectionConstraints.model_validate(constraints)


@pytest.mark.asyncio
async def test_known_output_and_source_markers_are_observed_with_endpoints_and_fixed_caps(inputs):
    subject, media, refs, constraints = copy.deepcopy(inputs)
    constraints["observationAnchors"] = [
        anchor(media, 61),
        anchor(media, 62),
        anchor(refs[1], 83, "source"),
    ]
    calls = []

    async def invoke(request):
        calls.append(request)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    output_frames = {item.inFrame for item in report.observations if item.mediaId == "output"}
    source_frames = {item.inFrame for item in report.observations if item.mediaId == "source"}
    assert {24, 61, 62, 95} <= output_frames
    assert source_frames == {48, 83, 119}
    assert len(output_frames) == 6
    assert len(calls) == 1
    assert report.checkerVersion == "smart-remake-inspection-p0-v1.3"
    assert (
        next(item for item in report.findings if item.requirementId == "action").status
        == "needs_review"
    )
    assert all(item.unobservedFrames == 66 for item in report.coverage)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    ["hash", "id", "clock", "out_of_media", "before_trim", "at_trim_end", "image", "source_range"],
)
async def test_invalid_anchor_bindings_fail_before_any_model_call(inputs, change):
    subject, media, refs, constraints = copy.deepcopy(inputs)
    marker = anchor(media)
    if change == "hash":
        marker["mediaHash"] = digest(b"different")
    elif change == "id":
        marker["mediaId"] = "missing"
    elif change == "clock":
        marker["timebase"] = "source"
    elif change == "out_of_media":
        marker["frame"] = 192
    elif change == "before_trim":
        marker["frame"] = 23
    elif change == "at_trim_end":
        marker["frame"] = 96
    elif change == "image":
        marker = anchor(refs[0])
    else:
        marker = anchor(refs[1], 120, "source")
    constraints["observationAnchors"] = [marker]
    calls = []

    async def invoke(request):
        calls.append(request)
        return await passing_model(request)

    with pytest.raises(ValueError, match="anchor"):
        await inspect_subject(subject, media, refs, constraints, invoke)
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("role,frames", [("output", [30, 40, 50, 60, 70]), ("source", [60, 70])])
async def test_endpoints_and_known_markers_never_exceed_sampling_capacity(inputs, role, frames):
    subject, media, refs, constraints = copy.deepcopy(inputs)
    asset = media if role == "output" else refs[1]
    constraints["observationAnchors"] = [
        anchor(asset, frame, "raw_group" if role == "output" else "source") for frame in frames
    ]
    calls = []

    async def invoke(request):
        calls.append(request)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert report.status == "insufficient_evidence"
    assert all(
        finding.status == "insufficient_evidence"
        for finding in report.findings
        if finding.category != "technical"
    )
    assert calls == []


@pytest.mark.asyncio
async def test_a_marker_outside_all_selected_source_windows_remains_unobserved(inputs):
    subject, media, refs, constraints = copy.deepcopy(inputs)
    constraints["sourceSceneMap"]["scenes"][0]["endFrame"] = 80
    constraints["observationAnchors"] = [anchor(refs[1], 83, "source")]
    calls = []

    async def invoke(request):
        calls.append(request)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert report.status == "insufficient_evidence"
    assert calls == []
    assert all(83 not in item.sampledFrames for item in report.coverage)


@pytest.mark.asyncio
async def test_a_later_scene_anchor_overflow_is_checked_before_any_model_call(inputs):
    subject, media, refs, constraints = copy.deepcopy(inputs)
    subject.pop("sceneId")
    subject.pop("versionId")
    subject.update(kind="assembly", assemblyId="assembly")
    subject["range"] = {"inFrame": 0, "outFrame": 192, "fps": 24, "timebase": "final"}
    constraints["timeline"] = {
        "items": [
            {"targetStartFrame": 0, "targetDurationFrames": 96, "sourceSceneId": "first"},
            {"targetStartFrame": 96, "targetDurationFrames": 96, "sourceSceneId": "second"},
        ]
    }
    constraints["observationAnchors"] = [
        anchor(media, frame, "final") for frame in (100, 110, 120, 130, 140)
    ]
    calls = []

    async def invoke(request):
        calls.append(request)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert report.status == "insufficient_evidence"
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("timebase", ["raw_group", "scene_local", "final"])
async def test_duplicate_endpoint_markers_do_not_spend_extra_capacity(inputs, timebase):
    subject, media, refs, constraints = copy.deepcopy(inputs)
    subject["range"]["timebase"] = timebase
    constraints["observationAnchors"] = [
        anchor(media, 24, timebase),
        anchor(media, 95, timebase),
        anchor(media, 24, timebase),
    ]
    report = await inspect_subject(subject, media, refs, constraints, passing_model)
    assert len([item for item in report.observations if item.mediaId == "output"]) == 6


@pytest.mark.asyncio
async def test_missing_required_observation_cannot_be_relabelled_as_covered(inputs):
    subject, media, refs, constraints = copy.deepcopy(inputs)
    report = await inspect_subject(subject, media, refs, constraints, passing_model)
    actual = {item.inFrame for item in report.observations if item.mediaId == "output"}
    missing = next(frame for frame in range(24, 96) if frame not in actual)
    constraints["observationAnchors"] = [anchor(media, missing)]
    with pytest.raises(ValueError, match="anchor"):
        validate_report_binding(report, subject, media, refs, constraints)


@pytest.mark.asyncio
async def test_decoder_omission_of_known_marker_cannot_be_reported_as_observed(inputs, monkeypatch):
    from viraldy.modules.smart_remake.inspection import core

    subject, media, refs, constraints = copy.deepcopy(inputs)
    constraints["observationAnchors"] = [anchor(media, 61)]
    decode = core.video_observations

    def missing_marker(asset, frames, **kwargs):
        observations, images = decode(asset, frames, **kwargs)
        omitted = {
            item.id for item in observations if item.mediaId == "output" and item.inFrame == 61
        }
        return (
            [item for item in observations if item.id not in omitted],
            [item for item in images if item.observationId not in omitted],
        )

    monkeypatch.setattr(core, "video_observations", missing_marker)
    calls = []

    async def invoke(request):
        calls.append(request)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert report.status == "insufficient_evidence"
    assert calls == []
    assert all(
        finding.status == "insufficient_evidence"
        for finding in report.findings
        if finding.category != "technical"
    )
