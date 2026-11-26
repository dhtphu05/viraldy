# ruff: noqa: F811 -- pytest imports the shared offline fixture by name.
from __future__ import annotations

import json

import pytest
from test_smart_remake_inspection_expectations import with_expectations
from test_smart_remake_inspection_runtime import inputs, passing_model, video  # noqa: F401
from test_smart_remake_lifecycle_paid_conditioning import (
    check,
    conditioning,  # noqa: F401
    report_for,
)

from viraldy.modules.smart_remake.budgeted_analysis import stable_hash
from viraldy.modules.smart_remake.conditioning_inspection import _snapshot
from viraldy.modules.smart_remake.generation_expectations import expectations_hash
from viraldy.modules.smart_remake.inspection import core
from viraldy.modules.smart_remake.inspection.public import inspect_subject
from viraldy.modules.smart_remake.inspection_service import _model_adapter
from viraldy.shared.errors.base import AppError


def conditioning_inputs(video):
    original, _, refs, constraints = inputs(video)
    value = with_expectations(original, refs, constraints)
    scene = value["scenes"][0]
    scene["sourceRange"]["startFrame"] = 24
    scene["openingFrame"]["frame"] = 24
    constraints["expectationsHash"] = expectations_hash(value)
    constraints["sceneIds"] = ["s1"]
    media = {**refs[0], "id": "generated", "role": "conditioning"}
    subject = {
        "kind": "image",
        "projectId": "p1",
        "imageRole": "conditioning",
        "mediaHash": media["mediaHash"],
    }
    return subject, media, refs, constraints


@pytest.mark.asyncio
async def test_conditioning_wire_maps_each_attached_image_to_exact_observation(video):
    subject, media, refs, constraints = conditioning_inputs(video)
    seen = []

    async def budgeted(payload):
        seen.append(payload)
        prompt = json.loads(payload["prompt"])
        assert prompt["sourceMapped"] is True
        bindings = prompt["imageBindings"]
        assert bindings == [
            {"imageIndex": index + 1, "observationId": observation["id"]}
            for index, observation in enumerate(prompt["observations"])
        ]
        assert prompt["allowedObservationIds"] == [
            "ref-product", "ref-generated", "source-frame-24"
        ]
        assert len(payload["media"]) == len(bindings) == 3
        assert "Never cite mediaId" in payload["systemInstruction"]
        return {
            "findings": [
                {
                    "requirementId": rule["id"],
                    "status": "passed",
                    "observed": "The three supplied images match the intended opening.",
                    "observationIds": prompt["allowedObservationIds"],
                }
                for rule in prompt["requirements"]
            ]
        }

    report = await inspect_subject(subject, media, refs, constraints, _model_adapter(budgeted))
    assert len(seen) == 1
    assert report.status == "passed"
    opening = next(item for item in report.findings if item.requirementId.endswith(":opening"))
    assert {item.mediaId for item in opening.evidence} == {"product", "generated", "source"}
    assert next(item for item in opening.evidence if item.mediaId == "source").inFrame == 24


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "corruption", ["missing", "frame", "media_id", "hash", "clock", "binding", "pixels"]
)
async def test_conditioning_never_claims_source_mapping_for_unbound_frame(
    video, monkeypatch, corruption
):
    subject, media, refs, constraints = conditioning_inputs(video)
    decode = core.video_observations

    def corrupted(*args, **kwargs):
        observations, images = decode(*args, **kwargs)
        if corruption == "missing":
            return [], []
        if corruption == "frame":
            observations[0] = observations[0].model_copy(update={"inFrame": 25, "outFrame": 26})
        elif corruption == "media_id":
            observations[0] = observations[0].model_copy(update={"mediaId": "unrelated-source"})
        elif corruption == "hash":
            observations[0] = observations[0].model_copy(update={"mediaHash": "f" * 64})
        elif corruption == "clock":
            observations[0] = observations[0].model_copy(update={"timebase": "raw_group"})
        elif corruption == "binding":
            images[0] = images[0].model_copy(update={"observationId": "source-frame-25"})
        else:
            images[0] = images[0].model_copy(update={"data": b"unrelated-pixels"})
        return observations, images

    monkeypatch.setattr(core, "video_observations", corrupted)

    async def forbidden(request):
        pytest.fail("An unverified source opening must stop before the model.")

    report = await inspect_subject(subject, media, refs, constraints, forbidden)
    assert report.status == "insufficient_evidence"
    assert all(item.status != "passed" for item in report.findings if item.category != "technical")


@pytest.mark.asyncio
async def test_image_bindings_do_not_alias_media_ids_or_override_model_uncertainty(video):
    subject, media, refs, constraints = conditioning_inputs(video)

    async def model(request):
        result = await passing_model(request)
        for finding in result["output"]["findings"]:
            if finding["requirementId"] == "product":
                finding["observationIds"] = ["ref-product", "generated"]
            else:
                finding.update(status="insufficient_evidence", observationIds=[])
        return result

    report = await inspect_subject(subject, media, refs, constraints, model)
    assert report.status == "insufficient_evidence"
    assert all(item.status == "insufficient_evidence" for item in report.findings[1:])
    assert all(not item.evidence for item in report.findings[1:])


@pytest.mark.asyncio
async def test_ordinary_image_does_not_claim_a_source_frame_was_mapped(video):
    _, _, refs, constraints = inputs(video)
    media = {**refs[0], "id": "generated"}
    subject = {
        "kind": "image", "projectId": "p1", "imageRole": "product", "mediaHash": media["mediaHash"]
    }
    seen = []

    async def model(request):
        seen.append(json.loads(request.prompt))
        return await passing_model(request)

    await inspect_subject(subject, media, refs, constraints, model)
    assert len(seen) == 1
    assert seen[0]["sourceMapped"] is False
    assert all(not item["id"].startswith("source-frame-") for item in seen[0]["observations"])


@pytest.mark.asyncio
async def test_checker_version_changes_conditioning_cache_without_changing_expectations(
    conditioning, monkeypatch
):
    value = conditioning
    binding = {**value.binding, "imageSceneId": value.record["renderUnitId"]}
    current = _snapshot(value.row, value.record, binding)
    monkeypatch.setattr(core, "CHECKER_VERSION", "smart-remake-inspection-p0-v1.2")
    old = _snapshot(value.row, value.record, binding)
    assert current["expectations"] == old["expectations"]
    assert current["expectationsHash"] == old["expectationsHash"]
    assert stable_hash(current) != stable_hash(old)


@pytest.mark.asyncio
async def test_report_from_previous_checker_cannot_satisfy_new_conditioning_check(conditioning):
    async def old_checker(**kwargs):
        report = report_for(kwargs)
        return {**report, "checkerVersion": "smart-remake-inspection-p0-v1.2"}

    with pytest.raises(AppError) as error:
        await check(conditioning, inspector=old_checker)
    assert error.value.code == "SMART_REMAKE_CONDITIONING_REPORT_INVALID"


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["unknown", "invoking"])
async def test_checker_upgrade_cannot_replace_unknown_check_for_same_operation(
    conditioning, monkeypatch, phase
):
    calls = []

    async def uncertain(**kwargs):
        calls.append("old")
        raise RuntimeError("Unknown transport outcome")

    monkeypatch.setattr(core, "CHECKER_VERSION", "smart-remake-inspection-p0-v1.2")
    with pytest.raises(AppError, match="conditioning check needs reconciliation"):
        await check(conditioning, inspector=uncertain)
    p0 = conditioning.row.context_json["p0"]
    conditioning.row.context_json = {
        **conditioning.row.context_json,
        "p0": {
            **p0,
            "conditioningChecks": {
                key: {**value, "phase": phase} for key, value in p0["conditioningChecks"].items()
            },
        },
    }
    monkeypatch.setattr(core, "CHECKER_VERSION", "smart-remake-inspection-p0-v1.3")

    async def replacement(**kwargs):
        calls.append("new")
        return report_for(kwargs)

    with pytest.raises(AppError) as error:
        await check(conditioning, inspector=replacement)
    assert error.value.code == "SMART_REMAKE_CONDITIONING_RECONCILIATION_REQUIRED"
    assert calls == ["old"]
