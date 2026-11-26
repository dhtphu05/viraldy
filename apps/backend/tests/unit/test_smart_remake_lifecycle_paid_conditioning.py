# ruff: noqa: F811 -- pytest imports the shared offline fixtures by name.
from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from test_smart_remake_grouped_workflow import grouped  # noqa: F401
from test_smart_remake_inspection_expectations import canonical
from test_smart_remake_inspection_runtime import video  # noqa: F401
from test_smart_remake_rights import (
    MemoryMedia,
    MemoryRepository,
    image_upload,
    intake_payload,
    source_upload,
)

from viraldy.modules.smart_remake.project_intake import create_intake
from viraldy.shared.errors.base import AppError


def report_for(kwargs, status="passed"):
    from viraldy.modules.smart_remake.inspection.contracts import (
        InspectionConstraints,
        InspectionSubject,
    )
    from viraldy.modules.smart_remake.inspection.public import inspection_profile
    from viraldy.modules.smart_remake.inspection.requirements import (
        TECHNICAL_REQUIREMENT,
        requirements_for,
    )

    media, constraints = kwargs["media"], kwargs["constraints"]
    observations, evidence = [], []
    for asset in [media, *kwargs["references"]]:
        sample = "observation-" + asset["id"]
        observations.append(
            {
                "id": sample,
                "mediaId": asset["id"],
                "mediaHash": asset["mediaHash"],
                "imageHash": asset["mediaHash"],
                "mimeType": "image/jpeg" if asset.get("role") == "source" else asset["mimeType"],
                **(
                    {
                        "inFrame": constraints["expectations"]["scenes"][0]["openingFrame"][
                            "frame"
                        ],
                        "outFrame": constraints["expectations"]["scenes"][0]["openingFrame"][
                            "frame"
                        ]
                        + 1,
                        "timebase": "source",
                    }
                    if asset.get("role") == "source"
                    else {}
                ),
            }
        )
        evidence.append(
            {
                "mediaId": asset["id"],
                "mediaHash": asset["mediaHash"],
                "sampleId": sample,
                **(
                    {
                        "inFrame": observations[-1]["inFrame"],
                        "outFrame": observations[-1]["outFrame"],
                        "timebase": "source",
                    }
                    if asset.get("role") == "source"
                    else {}
                ),
            }
        )
    rules = [
        TECHNICAL_REQUIREMENT,
        *requirements_for(
            InspectionSubject.model_validate(kwargs["subject"]),
            InspectionConstraints.model_validate(constraints),
        ),
    ]
    findings, coverage = [], []
    for rule in rules:
        outcome = "passed" if rule.id == "technical" else status
        findings.append(
            {
                "id": rule.id,
                "requirementId": rule.id,
                "category": rule.category,
                "expected": rule.expected,
                "observed": "Compared original and output",
                "status": outcome,
                "severity": "info" if outcome == "passed" else "warning",
                "evidence": evidence,
                "suggestedAction": "Keep or repair as needed",
                "blocking": False,
                "hardBlocking": False,
            }
        )
        coverage.append({"requirementId": rule.id, "status": outcome, "evidence": evidence})
    return {
        "id": str(uuid4()),
        "schemaVersion": 1,
        "subject": kwargs["subject"],
        "status": status,
        "checkedAt": datetime.now(UTC).isoformat(),
        **inspection_profile(),
        "modelProfile": {"provider": "offline"},
        "constraintsHash": constraints["constraintsHash"],
        "manifestHash": constraints["manifestHash"],
        "expectationsHash": constraints["expectationsHash"],
        "findings": findings,
        "coverage": coverage,
        "observations": observations,
        "notApplicableRequirements": []
        if constraints["requirements"].get("requiresCharacter")
        else [{"requirementId": "character", "reason": "This case has no character reference"}],
    }


@pytest.fixture
async def conditioning(video):
    repository, media = MemoryRepository(), MemoryMedia()
    workspace = uuid4()
    row = await create_intake(
        repository,
        media,
        workspace,
        uuid4(),
        intake_payload(),
        source_upload().model_copy(update={"bytes": video}),
        image_upload(),
    )
    calls, writes = [], []

    async def merge_context(current, updates):
        current.context_json = {**current.context_json, **copy.deepcopy(updates)}
        writes.append(copy.deepcopy(updates))

    repository.merge_context = merge_context
    output = image_upload()
    key = f"workspaces/{workspace}/smart-remake/{row.id}/images/conditioning.png"
    media.objects[key] = output.bytes
    record = {
        "storageKey": key,
        "mediaHash": hashlib.sha256(output.bytes).hexdigest(),
        "mimeType": output.mime_type,
        "requestHash": "a" * 64,
        "model": "gpt-image-2.6-sunburst",
        "quality": "max",
        "complexity": "high",
    }
    row.context_json["imageAssets"] = {record["requestHash"]: record}
    repair = SimpleNamespace(
        repository=repository,
        media=media,
        workspace_id=workspace,
        settings=SimpleNamespace(ai_mode="live"),
    )
    operation = SimpleNamespace(id=uuid4(), result_json={"kind": "render"})

    async def inspector(**kwargs):
        calls.append(kwargs)
        assert "conditioningChecks" in row.context_json["p0"]
        await kwargs["invoke_model"]({"prompt": "check", "media": []})
        return report_for(kwargs)

    async def invoke(payload):
        return {"observed": True}

    value = SimpleNamespace(
        row=row,
        repair=repair,
        operation=operation,
        record=record,
        calls=calls,
        writes=writes,
        inspector=inspector,
        invoke=invoke,
    )
    freeze_expectations(value)
    return value


def freeze_expectations(value):
    from viraldy.modules.smart_remake.generation_expectations import (
        expectations_hash,
        validate_generation_expectations,
    )

    refs = [
        {"role": role, "mediaHash": asset["mediaHash"]}
        for role, asset in value.row.context_json["p0"]["assets"].items()
    ]
    expected = canonical({"sceneId": "unit-1"}, refs, value.row.context_json["p0"]["requirements"])
    second = copy.deepcopy(expected["scenes"][0])
    second.update(
        sceneIndex=1,
        renderUnitId="unit-2",
        sourceSceneId="src2",
        sourceRange={"startFrame": 72, "endFrame": 192},
    )
    second["openingFrame"]["frame"] = 72
    expected["scenes"].append(second)
    expected = validate_generation_expectations(expected)
    digest = expectations_hash(expected)
    first = expected["scenes"][0]
    value.record.update(
        expectationsHash=digest,
        renderUnitId=first["renderUnitId"],
        sourceSceneId=first["sourceSceneId"],
        openingFrame=first["openingFrame"],
    )
    value.binding = {
        "expectations": expected,
        "expectationsHash": digest,
        "sceneIndices": [0],
        "imageSceneIndices": [0],
    }


def image_binding(value, indices=None):
    return {
        **value.binding,
        **({"sceneIndices": indices, "imageSceneIndices": indices} if indices is not None else {}),
    }


async def check(value, **overrides):
    from viraldy.modules.smart_remake.conditioning_inspection import check_conditioning_images

    return await check_conditioning_images(
        value.repair,
        value.row,
        value.operation,
        [value.record],
        binding={**image_binding(value), "renderGroupId": "group-1"},
        inspector=overrides.get("inspector", value.inspector),
        invoke_model=value.invoke,
    )


@pytest.mark.asyncio
async def test_conditioning_inspection_persists_owned_asset_and_original_references(conditioning):
    value = conditioning
    records = await check(value)
    assert len(value.calls) == 1
    assert value.calls[0]["subject"]["imageRole"] == "conditioning"
    assert [ref["role"] for ref in value.calls[0]["references"]] == ["source", "product"]
    assert value.calls[0]["references"][1]["bytes"] == image_upload().bytes
    assert (
        value.calls[0]["media"]["bytes"] == value.repair.media.objects[value.record["storageKey"]]
    )
    assert records[0]["conditioningReportId"]
    reports = value.row.context_json["p0"]["inspections"]["reports"]
    assert reports[0]["stage"] == "conditioning"
    assert reports[0]["subject"]["mediaHash"] == value.record["mediaHash"]
    json.dumps(value.writes)  # Raw bytes cannot enter persisted JSON.
    await check(value)
    assert len(value.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["failed", "needs_review", "insufficient_evidence"])
async def test_nonpassing_conditioning_blocks_video_without_override(conditioning, status):
    value = conditioning

    async def inspector(**kwargs):
        value.calls.append(kwargs)
        return report_for(kwargs, status)

    with pytest.raises(AppError, match="SMART_REMAKE_CONDITIONING_BLOCKED"):
        await check(value, inspector=inspector)
    assert value.row.context_json["p0"]["inspections"]["reports"][0]["status"] == status
    with pytest.raises(AppError, match="SMART_REMAKE_CONDITIONING_BLOCKED"):
        await check(value, inspector=inspector)
    assert len(value.calls) == 1


@pytest.mark.asyncio
async def test_unknown_conditioning_never_invokes_again(conditioning):
    value = conditioning

    async def inspector(**kwargs):
        value.calls.append(kwargs)
        raise TimeoutError("lost model response")

    for _ in range(2):
        with pytest.raises(AppError, match="SMART_REMAKE_CONDITIONING_RECONCILIATION_REQUIRED"):
            await check(value, inspector=inspector)
    assert len(value.calls) == 1


@pytest.mark.asyncio
async def test_tampered_conditioning_bytes_never_reach_inspector(conditioning):
    value = conditioning
    value.repair.media.objects[value.record["storageKey"]] = b"changed"
    with pytest.raises(AppError, match="SMART_REMAKE_CONDITIONING_MEDIA_CHANGED"):
        await check(value)
    assert value.calls == []


@pytest.mark.asyncio
async def test_wrong_report_context_is_not_accepted(conditioning):
    value = conditioning

    async def inspector(**kwargs):
        result = report_for(kwargs)
        result["manifestHash"] = "0" * 64
        return result

    with pytest.raises(AppError, match="SMART_REMAKE_CONDITIONING_REPORT_INVALID"):
        await check(value, inspector=inspector)
    assert value.row.context_json["p0"].get("inspections", {}).get("reports", []) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("tamper", ["scene", "opening", "hash", "scope", "missing_scope"])
async def test_conditioning_rejects_unbound_image_or_scene_before_checker(conditioning, tamper):
    from viraldy.modules.smart_remake.conditioning_inspection import check_conditioning_images

    value = conditioning
    binding = copy.deepcopy(image_binding(value))
    if tamper == "scene":
        value.record["renderUnitId"] = "unit-2"
    elif tamper == "opening":
        value.record["openingFrame"] = {**value.record["openingFrame"], "frame": 1}
    elif tamper == "hash":
        value.record["expectationsHash"] = "f" * 64
    elif tamper == "scope":
        binding["imageSceneIndices"] = [1]
    else:
        binding.pop("imageSceneIndices")
    with pytest.raises(AppError, match="SMART_REMAKE_CONDITIONING_CONTEXT_INVALID"):
        await check_conditioning_images(
            value.repair,
            value.row,
            value.operation,
            [value.record],
            binding=binding,
            inspector=value.inspector,
            invoke_model=value.invoke,
        )
    assert not value.calls


@pytest.mark.asyncio
async def test_saved_requirements_are_checked_even_when_scene_prompt_is_edited(conditioning):
    value = conditioning
    value.row.context_json["p0"]["requirements"].update(
        forbid=["medical cure claim"], claims=["Only claim 250 ml capacity"]
    )
    freeze_expectations(value)
    await check(value)
    checked = value.calls[0]["constraints"]["requirements"]
    assert checked["forbid"] == ["medical cure claim"]
    assert checked["claims"] == ["Only claim 250 ml capacity"]


@pytest.mark.asyncio
async def test_kie_workflow_checks_conditioning_before_any_upload(grouped, monkeypatch):
    from viraldy.modules.smart_remake import conditioning_inspection

    value = grouped
    captures = []

    async def precheck(repair, row, operation, references, **kwargs):
        assert value.client.uploads == []
        captures.append(references)
        raise AppError("SMART_REMAKE_CONDITIONING_BLOCKED", "repair required", 409)

    monkeypatch.setattr(conditioning_inspection, "check_conditioning_images", precheck)
    await value.runner._freeze_plan(value.row, value.op)
    request, references = await value.runner._request(value.row, value.op, 0, value.groups[0])
    assert not captures and len(references) == 2
    assert len(value.client.uploads) == 3 and value.client.submits == []
    assert request["input"]["duration"] == 8


async def passing_model(payload):
    prompt = json.loads(payload["prompt"])
    observations = [observation["id"] for observation in prompt["observations"]]
    return {
        "findings": [
            {
                "requirementId": requirement["id"],
                "status": "passed",
                "observed": "Compared retained output and original identity references",
                "observationIds": observations,
            }
            for requirement in prompt["requirements"]
        ]
    }


@pytest.mark.asyncio
async def test_real_public_inspector_uses_original_product_and_retained_generated_image(
    conditioning,
):
    from viraldy.modules.smart_remake.conditioning_inspection import check_conditioning_images

    value = conditioning
    records = await check_conditioning_images(
        value.repair,
        value.row,
        value.operation,
        [value.record],
        binding=image_binding(value),
        invoke_model=passing_model,
    )
    assert records[0]["conditioningReportId"]
    report = value.row.context_json["p0"]["inspections"]["reports"][0]
    assert report["checkerVersion"].startswith("smart-remake-inspection-p0-v")
    assert {observation["mediaId"] for observation in report["observations"]} == {
        "product",
        "source",
        "conditioning-" + value.record["requestHash"],
    }


@pytest.mark.asyncio
async def test_two_conditioning_checks_get_distinct_stable_budget_invocation_ids(
    conditioning, monkeypatch
):
    from viraldy.modules.smart_remake import conditioning_inspection

    value, invocations = conditioning, []
    value.repair.repository.session = object()
    second_scene = value.binding["expectations"]["scenes"][1]
    second = {
        **value.record,
        "requestHash": "b" * 64,
        "renderUnitId": second_scene["renderUnitId"],
        "sourceSceneId": second_scene["sourceSceneId"],
        "openingFrame": second_scene["openingFrame"],
    }
    value.row.context_json["imageAssets"][second["requestHash"]] = second

    def factory(session, workspace, project, operation_id, actor, metadata):
        invocations.append((operation_id, metadata))
        return passing_model

    monkeypatch.setattr(conditioning_inspection, "inspection_invoke", factory)
    records = await conditioning_inspection.check_conditioning_images(
        value.repair,
        value.row,
        value.operation,
        [value.record, second],
        binding=image_binding(value, [0, 1]),
    )
    assert len(records) == len(invocations) == 2
    assert invocations[0][0] != invocations[1][0]
    assert all(
        metadata["parentOperationId"] == str(value.operation.id) for _, metadata in invocations
    )
    await conditioning_inspection.check_conditioning_images(
        value.repair,
        value.row,
        value.operation,
        [value.record, second],
        binding=image_binding(value, [0, 1]),
    )
    assert len(invocations) == 2


@pytest.mark.asyncio
async def test_changed_requirements_during_check_preserve_stale_report_and_block(conditioning):
    value = conditioning

    async def inspector(**kwargs):
        result = report_for(kwargs)
        value.row.context_json["p0"]["requirements"]["forbid"] = ["No clinical claim"]
        return result

    with pytest.raises(AppError, match="SMART_REMAKE_CONDITIONING_STALE"):
        await check(value, inspector=inspector)
    report = value.row.context_json["p0"]["inspections"]["reports"][0]
    assert report["stale"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code",
    [
        "SMART_REMAKE_BUDGET_EXCEEDED",
        "SMART_REMAKE_STAGE_BOUND_REQUIRED",
        "SMART_REMAKE_MODEL_NOT_CONFIGURED",
    ],
)
async def test_proven_preflight_rejection_can_retry_same_check_after_configuration_fix(
    conditioning, code
):
    from viraldy.modules.smart_remake.conditioning_inspection import check_conditioning_images

    value, configured, physical_calls = conditioning, False, []

    async def budgeted(payload):
        if not configured:
            raise AppError(code, "No provider submission occurred", 409)
        physical_calls.append(payload)
        return await passing_model(payload)

    kwargs = dict(binding=image_binding(value), invoke_model=budgeted)
    with pytest.raises(AppError, match=code):
        await check_conditioning_images(
            value.repair, value.row, value.operation, [value.record], **kwargs
        )
    assert not physical_calls
    check_before = next(iter(value.row.context_json["p0"]["conditioningChecks"].values()))
    assert check_before["phase"] == "retryable"
    configured = True
    records = await check_conditioning_images(
        value.repair, value.row, value.operation, [value.record], **kwargs
    )
    assert len(physical_calls) == 1 and records[0]["conditioningReportId"]


@pytest.mark.asyncio
async def test_conditioning_is_attributed_to_operation_actor(conditioning, monkeypatch):
    from viraldy.modules.smart_remake import conditioning_inspection

    value, actors = conditioning, []
    operator = uuid4()
    value.operation.result_json["actorId"] = str(operator)
    value.repair.repository.session = object()

    def factory(session, workspace, project, operation, actor, metadata):
        actors.append(actor)
        return passing_model

    monkeypatch.setattr(conditioning_inspection, "inspection_invoke", factory)
    await conditioning_inspection.check_conditioning_images(
        value.repair,
        value.row,
        value.operation,
        [value.record],
        binding=image_binding(value),
    )
    assert actors == [operator]
    assert value.row.context_json["p0"]["inspections"]["reports"][0]["actorId"] == str(operator)


@pytest.mark.asyncio
@pytest.mark.parametrize("tamper", ["product", "image-0"])
async def test_substitution_between_conditioning_and_upload_never_sends_unchecked_bytes(
    grouped, monkeypatch, tamper
):
    from viraldy.modules.smart_remake import kie_workflow

    value = grouped
    value.row.context_json["p0"] = {"actorId": str(uuid4())}
    value.row.context_json["productMediaHash"] = hashlib.sha256(b"product").hexdigest()

    async def gate(*args):
        return None

    original_prepare = value.helper.prepare_scene_image

    async def prepare(**kwargs):
        record = await original_prepare(**kwargs)
        if kwargs["index"] == 1:
            original_read = value.repair.media.read

            async def changed(key):
                return b"unchecked replacement" if key == tamper else await original_read(key)

            value.repair.media.read = changed
        return {**record, "mediaHash": hashlib.sha256(record["storageKey"].encode()).hexdigest()}

    monkeypatch.setattr(kie_workflow, "require_generation_policy", gate)
    monkeypatch.setattr(value.helper, "prepare_scene_image", prepare)
    await value.runner._freeze_plan(value.row, value.op)
    with pytest.raises(AppError, match="SMART_REMAKE_INPUT_CHANGED"):
        await value.runner._request(value.row, value.op, 0, value.groups[0])
    assert value.client.uploads == [] and value.client.submits == []


@pytest.mark.asyncio
async def test_revocation_during_first_upload_blocks_remaining_references_and_veo(
    grouped, monkeypatch
):
    from viraldy.modules.smart_remake import conditioning_inspection, kie_workflow

    value, revoked = grouped, False
    original_upload = value.client.upload_file

    async def gate(*args):
        if revoked:
            raise AppError("SMART_REMAKE_RIGHTS_REVOKED", "Stop use was requested", 409)

    async def upload(media):
        nonlocal revoked
        result = await original_upload(media)
        revoked = True
        return result

    async def precheck(repair, row, operation, references, **kwargs):
        return references

    monkeypatch.setattr(kie_workflow, "require_generation_policy", gate)
    monkeypatch.setattr(conditioning_inspection, "check_conditioning_images", precheck)
    monkeypatch.setattr(value.client, "upload_file", upload)
    await value.runner._freeze_plan(value.row, value.op)
    with pytest.raises(AppError, match="SMART_REMAKE_RIGHTS_REVOKED"):
        await value.runner._task(
            value.row, value.op, 0, reconcile_only=False, group=value.groups[0]
        )
    assert value.client.uploads == [b"product"]
    assert value.client.submits == []
