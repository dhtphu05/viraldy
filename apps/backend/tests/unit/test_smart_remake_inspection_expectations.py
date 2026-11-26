# ruff: noqa: F811 -- pytest imports the shared offline fixture by name.
from __future__ import annotations

import copy
import json

import pytest
from test_smart_remake_inspection_runtime import inputs, passing_model, video  # noqa: F401

from viraldy.modules.smart_remake.inspection.public import (
    InspectionConstraints,
    inspect_subject,
    validate_report_binding,
)


def canonical(subject, refs, requirements):
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash

    references = {ref["role"]: {"mediaHash": ref["mediaHash"]} for ref in refs}
    return {
        "schemaVersion": 1,
        "version": "smart-remake-generation-expectations-v1",
        "fps": 24,
        "productLock": {
            "productName": "Seller red bottle",
            "productType": "bottle",
            "visualIdentity": {"colors": ["red"], "shape": "cylinder", "visibleBranding": "SELLER"},
            "productUsage": {"contactPoints": ["hand on lid"]},
            "mustPreserve": ["red body", "SELLER marking"],
            "canChange": ["background"],
            "forbiddenErrors": ["blue source bottle"],
        },
        "requirements": copy.deepcopy(requirements),
        "requirementsHash": expectations_hash(requirements),
        "references": references,
        "sourceContext": {
            "cameraStyle": {"angle": "front", "framing": "close", "movement": "static"}
        },
        "scenes": [
            {
                "sceneIndex": 0,
                "renderUnitId": subject.get("sceneId", "s1"),
                "sourceSceneId": "src1",
                "sourceRange": {"startFrame": 0, "endFrame": 72},
                "openingFrame": {
                    "sourceMediaHash": references["source"]["mediaHash"],
                    "frame": 0,
                    "layoutHash": "c" * 64,
                    "extractorVersion": "source-opening-v1",
                },
                "shotPlan": {
                    "shots": [
                        {
                            "startSecond": 0,
                            "endSecond": 3,
                            "action": "Open the seller bottle lid",
                            "stateBefore": "lid closed",
                            "stateAfter": "lid open",
                            "framing": "close-up",
                            "physicalAction": {
                                "contactPoint": "hand on lid",
                                "movement": "twist upward",
                            },
                        }
                    ]
                },
                "sourceSegment": {"segmentOrder": 1},
                "prompt": "Seller bottle scene",
                "imagePrompt": "Closed red bottle with hand on lid",
                "videoPrompt": "Open the lid",
                "userEdits": (
                    "Use a lower camera angle; " "preserve product identity and saved requirements."
                ),
            }
        ],
    }


def with_expectations(subject, refs, constraints):
    from viraldy.modules.smart_remake.generation_expectations import (
        expectations_hash,
        validate_generation_expectations,
    )

    value = validate_generation_expectations(canonical(subject, refs, constraints["requirements"]))
    constraints.update(expectations=value, expectationsHash=expectations_hash(value))
    constraints["sourceSceneMap"] = {"scenes": [{"id": "src1", "startFrame": 0, "endFrame": 72}]}
    constraints["manifest"] = {"selection": {"sourceSceneId": "src1", "renderUnitId": "s1"}}
    return value


@pytest.mark.asyncio
async def test_checker_sees_same_product_scene_and_creative_edits_and_binds_hash(video):
    subject, media, refs, constraints = inputs(video)
    value = with_expectations(subject, refs, constraints)
    calls = []

    async def model(request):
        calls.append(json.loads(request.prompt))
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, model)
    assert calls[0]["expectations"] == value
    assert "SELLER" in next(f.expected for f in report.findings if f.requirementId == "product")
    assert {f.requirementId for f in report.findings} >= {
        "scene:s1:opening",
        "scene:s1:presentation",
        "scene:s1:action",
    }
    assert "lower camera angle" in next(
        f.expected for f in report.findings if f.requirementId == "scene:s1:presentation"
    )
    assert report.expectationsHash == constraints["expectationsHash"]
    bad = report.model_dump(mode="json")
    bad["expectationsHash"] = "f" * 64
    with pytest.raises(ValueError, match="expectations"):
        validate_report_binding(bad, subject, media, refs, constraints)


def test_expectations_hash_and_global_requirements_must_match(video):
    subject, _, refs, constraints = inputs(video)
    with_expectations(subject, refs, constraints)
    InspectionConstraints.model_validate(constraints)
    for change in ("hash", "requirements", "missing_hash"):
        changed = copy.deepcopy(constraints)
        if change == "hash":
            changed["expectationsHash"] = "f" * 64
        elif change == "requirements":
            changed["requirements"]["forbid"] = ["No unsupported claims"]
        else:
            changed.pop("expectationsHash")
        with pytest.raises(ValueError):
            InspectionConstraints.model_validate(changed)


@pytest.mark.asyncio
async def test_normalized_global_requirements_keep_raw_hash_without_leaking_source_identity(video):
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash

    subject, media, refs, constraints = inputs(video)
    constraints["requirements"]["forbid"] = ["Copy ACME product identity"]
    value = with_expectations(subject, refs, constraints)
    value["requirements"]["forbid"] = ["Copy source product identity"]
    constraints["requirements"] = copy.deepcopy(value["requirements"])
    constraints["requirementsHash"] = value["requirementsHash"]
    constraints["expectationsHash"] = expectations_hash(value)
    seen = []

    async def model(request):
        seen.append(request.prompt)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, model)
    assert report.expectationsHash == constraints["expectationsHash"]
    assert all("ACME" not in prompt for prompt in seen)
    assert any("Copy source product identity" in prompt for prompt in seen)
    wrong = {**constraints, "requirementsHash": expectations_hash(value["requirements"])}
    with pytest.raises(ValueError, match="global requirements"):
        InspectionConstraints.model_validate(wrong)


@pytest.mark.asyncio
async def test_conditioning_requires_actual_source_opening_evidence(video):
    subject, _, refs, constraints = inputs(video)
    value = with_expectations(subject, refs, constraints)
    product = refs[0]
    media = {**product, "id": "generated", "role": "conditioning"}
    subject = {
        "kind": "image",
        "projectId": "p1",
        "imageRole": "conditioning",
        "mediaHash": media["mediaHash"],
    }
    constraints["sceneIds"] = ["s1"]
    calls = []

    async def model(request):
        calls.append(request)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, model)
    source_observations = [o for o in report.observations if o.mediaId == "source"]
    assert [(o.inFrame, o.outFrame, o.timebase) for o in source_observations] == [(0, 1, "source")]
    opening = next(f for f in report.findings if f.requirementId == "scene:s1:opening")
    assert opening.status == "passed"
    assert {e.mediaId for e in opening.evidence} >= {"source", "product", "generated"}
    assert json.loads(calls[0].prompt)["expectations"] == value
    forged = report.model_dump(mode="json")
    for collection in (forged["findings"], forged["coverage"]):
        entry = next(item for item in collection if item["requirementId"] == "scene:s1:opening")
        entry["evidence"] = [item for item in entry["evidence"] if item["mediaId"] != "source"]
    with pytest.raises(ValueError, match="Opening-state"):
        validate_report_binding(forged, subject, media, refs, constraints)

    async def no_source_citation(request):
        result = await passing_model(request)
        for finding in result["output"]["findings"]:
            finding["observationIds"] = [
                i for i in finding["observationIds"] if not i.startswith("source-")
            ]
        return result

    missing = await inspect_subject(subject, media, refs, constraints, no_source_citation)
    assert (
        next(f for f in missing.findings if f.requirementId == "scene:s1:opening").status
        == "insufficient_evidence"
    )
    assert missing.status != "passed"


@pytest.mark.asyncio
async def test_missing_source_opening_stops_before_model(video):
    subject, _, refs, constraints = inputs(video)
    with_expectations(subject, refs, constraints)
    media = {**refs[0], "id": "generated", "role": "conditioning"}
    subject = {
        "kind": "image",
        "projectId": "p1",
        "imageRole": "conditioning",
        "mediaHash": media["mediaHash"],
    }
    constraints["sceneIds"] = ["s1"]

    async def unexpected(request):
        pytest.fail("Missing source must not invoke the model")

    with pytest.raises(ValueError, match="original references"):
        await inspect_subject(subject, media, refs[:1], constraints, unexpected)


@pytest.mark.asyncio
async def test_final_scene_checks_are_scoped_to_their_own_windows(video, monkeypatch):
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash

    subject, media, refs, constraints = inputs(video, kind="assembly")
    subject["range"].update(inFrame=0, outFrame=192)
    subject["neighborVersionIds"] = ["v1", "v2"]
    value = with_expectations(subject, refs, constraints)
    value["scenes"][0]["sourceRange"]["endFrame"] = 96
    second = copy.deepcopy(value["scenes"][0])
    second.update(
        renderUnitId="s2",
        sourceSceneId="src2",
        sceneIndex=1,
        sourceRange={"startFrame": 96, "endFrame": 192},
    )
    second["openingFrame"]["frame"] = 96
    second["userEdits"] = "Static overhead view"
    value["scenes"].append(second)
    constraints["expectationsHash"] = expectations_hash(value)
    constraints["timeline"]["items"] = [
        {
            "renderUnitId": name,
            "sourceSceneId": source,
            "targetStartFrame": index * 96,
            "targetDurationFrames": 96,
        }
        for index, (name, source) in enumerate((("s1", "src1"), ("s2", "src2")))
    ]
    seen = []

    async def model(request):
        seen.append(json.loads(request.prompt))
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, model)
    assert len(seen) == 3
    for index, payload in enumerate(seen[:2]):
        own = f"scene:s{index + 1}:"
        other = f"scene:s{2 - index}:"
        ids = [rule["id"] for rule in payload["requirements"]]
        assert any(rule.startswith(own) for rule in ids)
        assert not any(rule.startswith(other) for rule in ids)
    assert {finding.requirementId for finding in report.findings} >= {
        "scene:s1:opening",
        "scene:s2:opening",
        "scene:s1:action",
        "scene:s2:action",
    }
    scoped = {item.requirementId: item for item in report.coverage}
    for index in range(2):
        start, end = index * 96, (index + 1) * 96
        for name in ("opening", "presentation", "action"):
            coverage = scoped[f"scene:s{index + 1}:{name}"]
            assert len(coverage.sampledFrames) == 6
            assert all(start <= frame < end for frame in coverage.sampledFrames)
            assert coverage.unobservedFrames == 90
    assert len(scoped["product"].sampledFrames) == 14
    forged = report.model_dump(mode="json")
    forged_scene = next(
        item for item in forged["coverage"] if item["requirementId"] == "scene:s1:opening"
    )
    forged_scene["sampledFrames"] = scoped["product"].sampledFrames
    forged_scene["unobservedFrames"] = 178
    with pytest.raises(ValueError, match="Coverage"):
        validate_report_binding(forged, subject, media, refs, constraints)
    forged = report.model_dump(mode="json")
    other = next(
        item for item in report.observations if item.mediaId == media["id"] and item.inFrame == 96
    )
    out_of_window = {
        "mediaId": other.mediaId,
        "mediaHash": other.mediaHash,
        "inFrame": other.inFrame,
        "outFrame": other.outFrame,
        "timebase": other.timebase,
        "sampleId": other.id,
    }
    for collection in (forged["findings"], forged["coverage"]):
        entry = next(item for item in collection if item["requirementId"] == "scene:s1:opening")
        entry["evidence"].append(out_of_window)
    with pytest.raises(ValueError, match="Scene evidence"):
        validate_report_binding(forged, subject, media, refs, constraints)
    from viraldy.modules.smart_remake.inspection import core

    decode = core.video_observations

    def missing_first_source(asset, frames, **kwargs):
        if asset.id == "source" and frames[0] < 96:
            raise ValueError("First source scene unavailable")
        return decode(asset, frames, **kwargs)

    monkeypatch.setattr(core, "video_observations", missing_first_source)
    partial = await inspect_subject(subject, media, refs, constraints, model)
    statuses = {finding.requirementId: finding.status for finding in partial.findings}
    assert statuses["scene:s1:opening"] == "insufficient_evidence"
    assert statuses["scene:s2:opening"] == "needs_review"


@pytest.mark.asyncio
async def test_conditioning_wrong_opening_state_is_not_promoted_to_pass(video):
    subject, _, refs, constraints = inputs(video)
    with_expectations(subject, refs, constraints)
    media = {**refs[0], "id": "generated", "role": "conditioning"}
    subject = {
        "kind": "image",
        "projectId": "p1",
        "imageRole": "conditioning",
        "mediaHash": media["mediaHash"],
    }
    constraints["sceneIds"] = ["s1"]

    async def wrong_state(request):
        result = await passing_model(request)
        for finding in result["output"]["findings"]:
            if finding["requirementId"] == "scene:s1:opening":
                finding.update(
                    status="failed", observed="The lid is already open rather than closed."
                )
        return result

    report = await inspect_subject(subject, media, refs, constraints, wrong_state)
    assert report.status == "failed"
    assert (
        next(f for f in report.findings if f.requirementId == "scene:s1:opening").status == "failed"
    )
