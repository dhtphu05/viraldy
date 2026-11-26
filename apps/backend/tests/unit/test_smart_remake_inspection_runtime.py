from __future__ import annotations

import hashlib
import json
import subprocess
from io import BytesIO

import pytest
from PIL import Image

from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path
from viraldy.modules.smart_remake.inspection.contracts import InspectionModelResult
from viraldy.modules.smart_remake.inspection.media import select_frames
from viraldy.modules.smart_remake.inspection.public import inspect_subject


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    path = tmp_path_factory.mktemp("inspector") / "self-authored.mp4"
    subprocess.run(  # noqa: S603 - fixed executable and self-authored synthetic input
        [
            ffmpeg_path(),
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",  # noqa: S603
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
    return path.read_bytes()


def image():
    output = BytesIO()
    Image.new("RGB", (90, 160), "red").save(output, format="PNG")
    return output.getvalue()


def inputs(video, kind="scene", *, character=False):
    media = {
        "id": "subject",
        "bytes": video,
        "mediaHash": digest(video),
        "mimeType": "video/mp4",
        "frameCount": 192,
        "fps": 24,
    }
    subject = {
        "kind": kind,
        "projectId": "p1",
        "mediaHash": media["mediaHash"],
        "range": {
            "inFrame": 24,
            "outFrame": 96,
            "fps": 24,
            "timebase": "final" if kind == "assembly" else "raw_group",
        },
        **({"assemblyId": "a1"} if kind == "assembly" else {"sceneId": "s1", "versionId": "v1"}),
        "neighborVersionIds": [],
    }
    refs = [
        {
            "id": "product",
            "role": "product",
            "bytes": image(),
            "mediaHash": digest(image()),
            "mimeType": "image/png",
        },
        {**media, "id": "source", "role": "source"},
    ]
    if character:
        refs.append({**refs[0], "id": "character", "role": "character"})
    constraints = {
        "constraintsHash": digest(b"constraints"),
        "manifestHash": digest(b"manifest"),
        "requirements": {"intent": "Use red product", "requiresCharacter": character},
        "timeline": {"fps": 24, "totalFrames": 192, "items": []},
        "manifest": {},
        "fps": 24,
        "frameCount": 192,
        "technicalCheck": {"status": "passed", "mediaHash": media["mediaHash"]},
    }
    return subject, media, refs, constraints


async def passing_model(payload):
    prompt = json.loads(payload.prompt)
    observations = prompt["observations"]
    ids = [item["id"] for item in observations]
    return {
        "output": {
            "findings": [
                {
                    "requirementId": item["id"],
                    "status": "passed",
                    "observed": "All supplied references match the sampled output.",
                    "observationIds": ids,
                }
                for item in prompt["requirements"]
            ]
        },
        "modelProfile": {"provider": "offline", "model": "scripted", "mode": "fixture"},
    }


def test_sampling_is_exact_bounded_and_keeps_real_last_frame():
    assert select_frames(0, 192, 6) == [0, 38, 76, 114, 152, 191]
    assert select_frames(24, 26, 6) == [24, 25]
    assert select_frames(24, 96, 4, mandatory=[30, 70]) == [24, 30, 70, 95]
    with pytest.raises(ValueError):
        select_frames(24, 24, 6)
    with pytest.raises(ValueError):
        select_frames(0, 192, 2, mandatory=[20, 30])


@pytest.mark.asyncio
async def test_real_media_has_truthful_coverage_and_action_requires_review(video):
    subject, media, refs, constraints = inputs(video)
    calls = []

    async def invoke(payload):
        calls.append(payload)
        return await passing_model(payload)

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert report.status == "needs_review"
    assert len(calls) == 1
    output = [o for o in report.observations if o.mediaId == "subject"]
    assert [o.inFrame for o in output] == select_frames(24, 96, 6)
    assert all(o.outFrame == o.inFrame + 1 for o in output)
    assert any(c.unobservedFrames == 66 for c in report.coverage)
    assert report.notApplicableRequirements[0].requirementId == "character"
    findings = {f.requirementId: f for f in report.findings}
    assert findings["product"].status == "passed"
    assert findings["action"].status == "needs_review"
    assert not findings["action"].hardBlocking and not findings["action"].blocking
    prompt = json.loads(calls[0].prompt)
    assert len(calls[0].images) == len(prompt["observations"])
    for item, observation in zip(calls[0].images, prompt["observations"], strict=True):
        assert digest(item.data) == observation["imageHash"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["empty", "malformed", "unknown", "unobserved", "no_refs"])
async def test_model_never_promotes_unobserved_or_missing_checks_to_pass(video, mode):
    subject, media, refs, constraints = inputs(video, character=True)
    if mode == "no_refs":
        refs = []
    calls = []

    async def invoke(payload):
        calls.append(1)
        result = await passing_model(payload)
        if mode == "empty":
            result["output"]["findings"] = []
        elif mode == "malformed":
            return {"untrusted": True}
        elif mode == "unknown":
            result["output"]["findings"][0]["observationIds"] = ["fake"]
        elif mode == "unobserved":
            result["output"]["findings"][0]["observationIds"] = ["ref-product"]
        return result

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert report.status in {"needs_review", "insufficient_evidence"}
    assert len(calls) <= 1
    assert all(not f.blocking for f in report.findings if f.category != "technical")


@pytest.mark.asyncio
async def test_timeout_does_not_retry_or_hide_ambiguous_submission(video):
    subject, media, refs, constraints = inputs(video)
    calls = []

    async def invoke(payload):
        calls.append(1)
        raise TimeoutError("submitted")

    with pytest.raises(TimeoutError):
        await inspect_subject(subject, media, refs, constraints, invoke)
    assert calls == [1]


@pytest.mark.asyncio
async def test_technical_failure_and_hash_tampering_stop_model(video):
    subject, media, refs, constraints = inputs(video)
    calls = []

    async def invoke(payload):
        calls.append(1)

    with pytest.raises(ValueError):
        await inspect_subject(subject, {**media, "bytes": b"changed"}, refs, constraints, invoke)
    constraints["technicalCheck"]["status"] = "failed"
    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert report.status == "failed" and not calls
    assert any(f.hardBlocking for f in report.findings)


@pytest.mark.asyncio
async def test_conditioning_image_keeps_original_reference_and_no_fake_time(video):
    subject, media, refs, constraints = inputs(video)
    media = {**refs[0], "id": "conditioning", "role": "conditioning"}
    subject = {
        "kind": "image",
        "projectId": "p1",
        "imageRole": "conditioning",
        "mediaHash": media["mediaHash"],
    }
    constraints["frameCount"] = None
    report = await inspect_subject(subject, media, refs, constraints, passing_model)
    assert all(o.inFrame is None for o in report.observations if o.mediaId == "conditioning")
    assert any(o.mediaId == "product" for o in report.observations)
    assert not any(f.requirementId == "action" for f in report.findings)


@pytest.mark.asyncio
async def test_final_2_plus_6_inspects_actual_join_and_original_source_ranges(video):
    subject, media, refs, constraints = inputs(video, kind="assembly")
    subject["range"].update(inFrame=0, outFrame=192)
    subject["neighborVersionIds"] = ["v1", "v2"]
    constraints["timeline"]["items"] = [
        {
            "renderUnitId": "s1",
            "sourceSceneId": "src1",
            "versionId": "v1",
            "targetStartFrame": 0,
            "targetDurationFrames": 48,
            "inFrame": 0,
            "outFrame": 48,
        },
        {
            "renderUnitId": "s2",
            "sourceSceneId": "src2",
            "versionId": "v2",
            "targetStartFrame": 48,
            "targetDurationFrames": 144,
            "inFrame": 48,
            "outFrame": 192,
        },
    ]
    constraints["sourceSceneMap"] = {
        "scenes": [
            {"id": "src1", "startFrame": 0, "endFrame": 48},
            {"id": "src2", "startFrame": 48, "endFrame": 192},
        ]
    }
    calls = []

    async def invoke(request):
        calls.append(request)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert len(calls) == 3
    assert all(json.loads(call.prompt)["sourceMapped"] for call in calls[:2])
    join = calls[-1]
    assert [o.inFrame for o in join.observations if o.mediaId == "subject"] == [46, 47, 48, 49]
    assert all(o.timebase == "final" for o in join.observations if o.mediaId == "subject")
    continuity = next(f for f in report.findings if f.requirementId == "continuity")
    assert continuity.status == "needs_review" and not continuity.blocking
    assert {e.inFrame for e in continuity.evidence if e.mediaId == "subject"} == {46, 47, 48, 49}


@pytest.mark.asyncio
async def test_scene_continuity_requires_resolved_bound_neighbor(video):
    subject, media, refs, constraints = inputs(video)
    subject["neighborVersionIds"] = ["v2"]
    constraints["timeline"]["items"] = [
        {"renderUnitId": "s1", "versionId": "v1", "inFrame": 24, "outFrame": 96},
        {"renderUnitId": "s2", "versionId": "v2", "inFrame": 96, "outFrame": 192},
    ]
    report = await inspect_subject(subject, media, refs, constraints, passing_model)
    finding = next(f for f in report.findings if f.requirementId == "continuity")
    assert finding.status == "needs_review" and "neighbor" in finding.observed.lower()
    refs.append({**media, "id": "neighbor-v2", "versionId": "v2", "role": "neighbor"})
    calls = []

    async def invoke(request):
        calls.append(request)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert len(calls) == 2
    assert [o.inFrame for o in calls[-1].observations if o.mediaId == "subject"] == [94, 95]
    assert [o.inFrame for o in calls[-1].observations if o.mediaId == "neighbor-v2"] == [96, 97]


@pytest.mark.asyncio
async def test_final_3_5_4_4_keeps_all_scenes_and_three_actual_joins(tmp_path):
    path = tmp_path / "authored-16-seconds.mp4"
    subprocess.run(  # noqa: S603 - fixed binary and synthetic local source
        [
            ffmpeg_path(),
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=90x160:rate=24:duration=16",
            "-c:v",
            "libx264",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    subject, media, refs, constraints = inputs(path.read_bytes(), kind="assembly")
    media["frameCount"] = 384
    refs[1]["frameCount"] = 384
    subject["range"].update(inFrame=0, outFrame=384)
    subject["neighborVersionIds"] = [f"v{index}" for index in range(4)]
    constraints["frameCount"] = constraints["timeline"]["totalFrames"] = 384
    cursor, scenes, items = 0, [], []
    for index, length in enumerate([72, 120, 96, 96]):
        scenes.append({"id": f"src{index}", "startFrame": cursor, "endFrame": cursor + length})
        items.append(
            {
                "renderUnitId": f"s{index}",
                "sourceSceneId": f"src{index}",
                "versionId": f"v{index}",
                "targetStartFrame": cursor,
                "targetDurationFrames": length,
                "inFrame": 0,
                "outFrame": length,
            }
        )
        cursor += length
    constraints["timeline"]["items"] = items
    constraints["sourceSceneMap"] = {"scenes": scenes}
    calls = []

    async def invoke(request):
        calls.append(request)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert len(calls) == 7
    assert [json.loads(call.prompt)["window"] for call in calls[:4]] == [
        [0, 72, "src0"],
        [72, 192, "src1"],
        [192, 288, "src2"],
        [288, 384, "src3"],
    ]
    assert [
        [o.inFrame for o in call.observations if o.mediaId == "subject"] for call in calls[4:]
    ] == [[70, 71, 72, 73], [190, 191, 192, 193], [286, 287, 288, 289]]
    assert report.status == "needs_review"
    assert all(len(call.images) <= 12 for call in calls)


@pytest.mark.asyncio
async def test_trim_removed_action_is_failed_not_inferred_from_source(video):
    subject, media, refs, constraints = inputs(video)

    async def omitted_action(request):
        result = await passing_model(request)
        for finding in result["output"]["findings"]:
            if finding["requirementId"] == "action":
                finding.update(
                    status="failed", observed="The selected trim omits the wiping action."
                )
        return result

    report = await inspect_subject(subject, media, refs, constraints, omitted_action)
    action = next(f for f in report.findings if f.requirementId == "action")
    assert report.status == action.status == "failed"
    assert not action.blocking and not action.hardBlocking
    assert all(
        24 <= e.inFrame < e.outFrame <= 96 for e in action.evidence if e.mediaId == "subject"
    )


@pytest.mark.asyncio
async def test_gapped_final_manifest_blocks_before_model(video):
    subject, media, refs, constraints = inputs(video, kind="assembly")
    subject["range"].update(inFrame=0, outFrame=192)
    constraints["timeline"]["items"] = [
        {"targetStartFrame": 0, "targetDurationFrames": 48},
        {"targetStartFrame": 49, "targetDurationFrames": 143},
    ]
    calls = []

    async def invoke(request):
        calls.append(request)

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert not calls and report.status == "failed"
    assert report.findings[0].hardBlocking


@pytest.mark.asyncio
async def test_wrapper_output_validation_error_is_explicit_missing_evidence(video):
    subject, media, refs, constraints = inputs(video)
    calls = []

    async def invoke(request):
        calls.append(request)
        InspectionModelResult.model_validate(
            {"output": {"findings": "invalid"}, "modelProfile": {}}
        )

    report = await inspect_subject(subject, media, refs, constraints, invoke)
    assert report.status == "insufficient_evidence"
    assert len(calls) == 1
