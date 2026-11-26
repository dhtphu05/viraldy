# ruff: noqa: F811 -- pytest imports the shared offline video fixture by name.
"""One server snapshot crosses all three model boundaries without paid calls."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from test_smart_remake_generation_wiring import canonical_runtime
from test_smart_remake_inspection_runtime import inputs, passing_model, video  # noqa: F401

from viraldy.modules.smart_remake import conditioning_inspection, image_workflow, kie_workflow
from viraldy.modules.smart_remake.generation_expectations import (
    build_generation_expectations,
    expectations_hash,
)
from viraldy.modules.smart_remake.inspection.public import inspect_subject


@pytest.mark.asyncio
async def test_image_video_checker_share_sanitized_facts_edits_and_snapshot(monkeypatch, video):
    subject, media, refs, constraints = inputs(video)
    context = canonical_runtime()
    unit = context["renderPlan"]["units"][0]
    unit["id"] = subject["sceneId"]
    context["sourceSceneMap"]["scenes"][0].update(startFrame=0, endFrame=72)
    source_hash = refs[1]["mediaHash"]
    context.update(productMediaHash=refs[0]["mediaHash"], sourceMediaHash=source_hash)
    context["sourceOpeningFrames"]["source"].update(sourceMediaHash=source_hash, frame=0)
    raw_scene = context["sceneMap"]["scenes"][0]
    raw_scene.update(
        promptEdited=True,
        originalVideoPrompt=raw_scene["videoPrompt"],
        videoPrompt=raw_scene["videoPrompt"] + ". Use a low camera angle",
    )
    # This is a legitimate prohibition of the source identity, not the seller identity.
    requirements = {"intent": "Show the seller bottle", "forbid": ["Acme logo"]}
    context["p0"] = {"requirements": requirements}
    snapshot = build_generation_expectations(context)
    snapshot_hash = expectations_hash(snapshot)
    context.update(generationExpectations=snapshot, expectationsHash=snapshot_hash)
    row = SimpleNamespace(context_json=context)
    operation = SimpleNamespace(result_json={"tasks": {}})
    captured = {}

    async def finish(op, status, result):
        op.result_json = result

    async def policy(*args):
        return None

    async def read(key):
        return refs[0]["bytes"]

    async def upload(media):
        return "https://1.1.1.1/owned-reference.png"

    async def prepare(**kwargs):
        # Preserve production prompt construction, replacing only paid image transport.
        prompt_context = {
            **context,
            "productLock": snapshot["productLock"],
            "p0": {"requirements": snapshot["requirements"]},
        }
        captured["image"] = image_workflow._image_prompt(prompt_context, kwargs["compiled_scene"])
        return {
            "storageKey": "generated",
            "mimeType": "image/png",
            "mediaHash": refs[0]["mediaHash"],
        }

    async def conditioning(repair, project, op, references, *, binding):
        assert binding["expectations"] == snapshot
        assert binding["expectationsHash"] == snapshot_hash
        return references

    monkeypatch.setattr(kie_workflow, "require_generation_policy", policy)
    monkeypatch.setattr(image_workflow, "prepare_scene_image", prepare)
    monkeypatch.setattr(conditioning_inspection, "check_conditioning_images", conditioning)
    repair = SimpleNamespace(
        repository=SimpleNamespace(finish=finish), media=SimpleNamespace(read=read)
    )
    runner = kie_workflow.KieWorkflow(
        repair, client=SimpleNamespace(upload_file=upload), image_client=object()
    )
    await runner._freeze_plan(row, operation)
    request, _ = await runner._request(row, operation, 0, None)
    captured["video"] = request["input"]["prompt"]

    constraints.update(
        expectations=copy.deepcopy(snapshot),
        expectationsHash=snapshot_hash,
        requirements=snapshot["requirements"],
        requirementsHash=snapshot["requirementsHash"],
        sourceSceneMap=context["sourceSceneMap"],
        manifest={"selection": {"sourceSceneId": "source", "renderUnitId": subject["sceneId"]}},
    )

    async def checker(request):
        captured["checker"] = json.loads(request.prompt)
        return await passing_model(request)

    report = await inspect_subject(subject, media, refs, constraints, checker)
    assert captured["checker"]["expectations"] == snapshot
    assert captured["checker"]["expectationsHash"] == snapshot_hash
    assert report.expectationsHash == snapshot_hash
    for payload in (
        captured["image"],
        captured["video"],
        json.dumps(captured["checker"]["expectations"]),
    ):
        assert "Acme" not in payload
        expected = (
            "Seller Bottle",
            "pink",
            "red background",
            "wood table",
            "hand",
            "lid",
            "Use a low camera angle",
            "source product identity",
        )
        assert not [text for text in expected if text not in payload]
    assert snapshot_hash in captured["image"]
    assert snapshot_hash not in captured["video"]
    assert "GENERATION EXPECTATIONS HASH" not in captured["video"]
    assert operation.result_json["expectationsHash"] == snapshot_hash
    assert operation.result_json["generationExpectations"] == snapshot
    # The raw analysis is retained for traceability, outside generation payloads.
    assert context["referenceAnalysis"]["forbiddenReuse"] == ["Acme"]
