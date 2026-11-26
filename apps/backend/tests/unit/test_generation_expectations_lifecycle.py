from __future__ import annotations

import copy

import pytest

from viraldy.modules.smart_remake.project_contracts import SmartRemakeRequirements
from viraldy.modules.smart_remake.project_policy import constraints_hash, context_with_requirements
from viraldy.modules.smart_remake.project_presentation import project_policy_fields
from viraldy.modules.smart_remake.release_policy import _inspectable
from viraldy.shared.errors.base import AppError


def test_constraints_bind_expectations_and_saved_generation_facts():
    context = {
        "p0": {"requirements": {"intent": "same product"}},
        "expectationsHash": "a" * 64,
        "generationExpectations": {"schemaVersion": 1},
        "productLock": {"name": "cup"},
    }
    original = constraints_hash(context)
    for key, value in (
        ("expectationsHash", "b" * 64),
        ("productLock", {"name": "bottle"}),
        ("sourceOpeningFrames", {"scene": {"frame": 25}}),
        ("sceneMap", {"scenes": [{"videoPrompt": "different action"}]}),
    ):
        changed = {**copy.deepcopy(context), key: value}
        assert constraints_hash(changed) != original


def test_new_requirements_mark_saved_plan_stale_but_keep_history():
    context = {
        "p0": {"requirements": {"intent": "old"}},
        "generationExpectations": {"old": True},
        "expectationsHash": "a" * 64,
    }
    changed = context_with_requirements(context, SmartRemakeRequirements(intent="new goal"))
    assert changed["expectationsStale"] is True
    assert changed["generationExpectations"] == context["generationExpectations"]
    assert "expectationsStale" not in context


def test_public_projection_exposes_only_binding_not_private_canonical_snapshot():
    context = {
        "expectationsHash": "a" * 64,
        "generationExpectations": {"schemaVersion": 1, "version": "generation-expectations-v1"},
        "p0": {
            "assemblies": {
                "records": [
                    {"generationExpectations": {"secret": True}, "expectationsHash": "b" * 64}
                ]
            }
        },
    }
    public = project_policy_fields(context)
    assert public["expectationsHash"] == "a" * 64
    assert public["expectationsVersion"] == 1
    assert public["assemblies"]["records"][0] == {"expectationsHash": "b" * 64}


def test_release_rejects_report_for_different_expectations_even_with_matching_old_bindings():
    assembly = {
        "id": "assembly",
        "projectId": "project",
        "mediaHash": "media",
        "constraintsHash": "constraints",
        "manifestHash": "manifest",
        "expectationsHash": "a" * 64,
    }
    report = {
        "subject": {
            "kind": "assembly",
            "projectId": "project",
            "assemblyId": "assembly",
            "mediaHash": "media",
        },
        "constraintsHash": "constraints",
        "manifestHash": "manifest",
        "expectationsHash": "b" * 64,
    }
    with pytest.raises(AppError, match="SMART_REMAKE_INSPECTION_STALE"):
        _inspectable(report, assembly, [])


def test_assembly_snapshot_uses_each_selected_version_and_exact_ranges():
    from tests.smart_remake_expectations import install_expectations
    from viraldy.modules.smart_remake.assembly_snapshots import assembly_expectations
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash

    timeline = {
        "items": [
            {
                "renderUnitId": "s1",
                "sourceSceneId": "source1",
                "versionId": "v1",
                "inFrame": 24,
                "outFrame": 96,
                "targetDurationFrames": 72,
            },
            {
                "renderUnitId": "s2",
                "sourceSceneId": "source2",
                "versionId": "v2",
                "inFrame": 72,
                "outFrame": 192,
                "targetDurationFrames": 120,
            },
        ]
    }
    state = {
        "draftTimeline": timeline,
        "scenes": [
            {"id": "s1", "versions": [{"id": "v1"}]},
            {"id": "s2", "versions": [{"id": "v2"}]},
        ],
    }
    context = {
        "p0": {
            "requirements": {"intent": "Preserve seller product"},
            "assets": {"source": {}, "product": {}},
        }
    }
    original = install_expectations(context, state=state)
    repaired = copy.deepcopy(original)
    repaired["scenes"][1]["videoPrompt"] = "A different accepted second-scene action"
    state["scenes"][1]["versions"][0].update(
        generationExpectations=repaired, expectationsHash=expectations_hash(repaired)
    )
    frozen = assembly_expectations(timeline, state, context)
    assert frozen["scenes"][0]["videoPrompt"] == original["scenes"][0]["videoPrompt"]
    assert frozen["scenes"][1]["videoPrompt"] == repaired["scenes"][1]["videoPrompt"]
    assert frozen["scenes"][0]["selection"] == {
        "versionId": "v1",
        "inFrame": 24,
        "outFrame": 96,
        "timebase": "raw_group",
    }
    changed = copy.deepcopy(timeline)
    changed["items"][0]["inFrame"] = 25
    assert expectations_hash(assembly_expectations(changed, state, context)) != expectations_hash(
        frozen
    )
    assert "selection" not in original["scenes"][0] or original["scenes"][0]["selection"] is None


def test_legacy_assembly_cannot_be_upgraded_from_missing_source_and_product_facts():
    from viraldy.modules.smart_remake.assembly_snapshots import assembly_expectations

    with pytest.raises(AppError, match="SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED"):
        assembly_expectations(
            {"items": [{"renderUnitId": "s", "sourceSceneId": "source", "versionId": "v"}]},
            {"scenes": [{"id": "s", "versions": [{"id": "v"}]}]},
            {"p0": {"requirements": {}}},
            historical=True,
        )


def test_new_assembly_rebases_requirements_without_changing_original_clip_snapshot():
    from tests.smart_remake_expectations import install_expectations
    from viraldy.modules.smart_remake.assembly_snapshots import assembly_expectations
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash

    timeline = {
        "items": [
            {
                "renderUnitId": "s",
                "sourceSceneId": "source",
                "versionId": "v",
                "inFrame": 0,
                "outFrame": 192,
                "targetDurationFrames": 192,
            }
        ]
    }
    state = {"draftTimeline": timeline, "scenes": [{"id": "s", "versions": [{"id": "v"}]}]}
    context = {
        "p0": {
            "requirements": {"intent": "Original intent"},
            "assets": {"source": {}, "product": {}},
        }
    }
    saved = install_expectations(context, state=state)
    before = copy.deepcopy(saved)
    context["p0"]["requirements"] = {"intent": "Updated seller intent"}
    current = assembly_expectations(timeline, state, context)
    assert current["requirementsHash"] == expectations_hash(context["p0"]["requirements"])
    assert current["requirements"]["intent"] == "Updated seller intent"
    assert saved == before
    context["p0"]["assets"]["product"]["mediaHash"] = "f" * 64
    with pytest.raises(AppError, match="SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED"):
        assembly_expectations(timeline, state, context)


def test_new_version_retains_immutable_operation_expectations(monkeypatch):
    from viraldy.modules.smart_remake import repair_service

    monkeypatch.setattr(repair_service, "technical_check", lambda *a, **k: {"status": "passed"})
    metadata = {
        "generationExpectations": {"scenes": [{"videoPrompt": "frozen"}]},
        "expectationsHash": "a" * 64,
    }
    version = repair_service._new_version(
        b"video",
        "owned-key",
        {"prompt": "p", "imagePrompt": "i", "videoPrompt": "v"},
        None,
        metadata,
        source="generated",
        audio_required=False,
    )
    metadata["generationExpectations"]["scenes"][0]["videoPrompt"] = "changed later"
    assert version["generationExpectations"]["scenes"][0]["videoPrompt"] == "frozen"
    assert (
        version["providerMetadata"]["generationExpectations"]["scenes"][0]["videoPrompt"]
        == "frozen"
    )
    assert version["expectationsHash"] == "a" * 64


@pytest.fixture
def release_harness():
    from tests.unit.test_smart_remake_release_actions import harness

    return harness.__wrapped__()


async def test_restore_rebases_only_new_record_and_requires_new_inspection(release_harness):
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash
    from viraldy.modules.smart_remake.inspection_service import InspectionSubjectRequest, _snapshot
    from viraldy.modules.smart_remake.project_lifecycle import RestoreRequest

    h = release_harness
    old = copy.deepcopy(h.row.context_json["p0"]["assemblies"]["records"][0])
    h.row.context_json["p0"]["requirements"] = {"intent": "Focus on the cap and opening posture"}
    result = await h.service.restore(
        h.project,
        h.actor,
        RestoreRequest(
            expectedRevision=3, idempotencyKey="restore-expectations", assemblyId=old["id"]
        ),
    )
    records = h.row.context_json["p0"]["assemblies"]["records"]
    restored = records[-1]
    assert records[0] == old
    assert restored["id"] != old["id"]
    assert restored["expectationsHash"] != old["expectationsHash"]
    assert restored["generationExpectations"]["requirementsHash"] == expectations_hash(
        h.row.context_json["p0"]["requirements"]
    )
    assert restored["generationExpectations"]["scenes"][0]["selection"]["versionId"] == "v1"
    assert h.row.context_json["p0"]["release"]["activeApprovalId"] is None
    assert h.row.context_json["expectationsStale"] is True
    assert result["project"]["expectationsHash"] is None
    snapshot = _snapshot(
        h.row,
        InspectionSubjectRequest(kind="assembly", assemblyId=restored["id"]),
        h.row.workspace_id,
    )
    assert snapshot["expectationsHash"] == restored["expectationsHash"]
    with pytest.raises(AppError, match="SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED"):
        _snapshot(
            h.row,
            InspectionSubjectRequest(kind="assembly", assemblyId=old["id"]),
            h.row.workspace_id,
        )


def test_legacy_assembly_qa_derives_only_from_complete_frozen_history(release_harness):
    from viraldy.modules.smart_remake.inspection_service import InspectionSubjectRequest, _snapshot

    h = release_harness
    old = h.row.context_json["p0"]["assemblies"]["records"][0]
    old.pop("generationExpectations")
    old.pop("expectationsHash")
    for scene in old["stateSnapshot"]["scenes"]:
        for version in scene["versions"]:
            version.pop("generationExpectations", None)
            version.pop("expectationsHash", None)
            version.pop("providerMetadata", None)
    before = copy.deepcopy(old)
    request = InspectionSubjectRequest(kind="assembly", assemblyId=old["id"])
    snapshot = _snapshot(h.row, request, h.row.workspace_id)
    assert snapshot["expectations"]["scenes"][0]["selection"]["versionId"] == "v1"
    assert old == before
    old["contextSnapshot"].pop("sourceOpeningFrames")
    with pytest.raises(AppError, match="SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED"):
        _snapshot(h.row, request, h.row.workspace_id)


def test_compose_operation_detects_selected_expectation_changes_before_media_work(release_harness):
    from viraldy.modules.smart_remake.assembly_snapshots import assembly_expectations
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash
    from viraldy.modules.smart_remake.project_policy import policy_hash
    from viraldy.modules.smart_remake.timeline_service import _compose_policy

    h = release_harness
    frozen = assembly_expectations(
        h.row.state_json["draftTimeline"], h.row.state_json, h.row.context_json
    )
    operation = {
        "actorId": str(h.actor),
        "constraintsHash": constraints_hash(h.row.context_json),
        "policyHash": policy_hash(h.row.context_json),
        "expectationsHash": expectations_hash(frozen),
    }
    _compose_policy(h.row, operation)
    version = h.row.state_json["scenes"][0]["versions"][0]
    changed = copy.deepcopy(version["generationExpectations"])
    changed["scenes"][0]["videoPrompt"] = "Different action after compose was queued"
    version.update(generationExpectations=changed, expectationsHash=expectations_hash(changed))
    with pytest.raises(AppError, match="SMART_REMAKE_COMPOSE_POLICY_CHANGED"):
        _compose_policy(h.row, operation)


def test_canonical_assembly_with_changed_product_facts_is_rejected_before_paid_qa(release_harness):
    from viraldy.modules.smart_remake.inspection_service import InspectionSubjectRequest, _snapshot

    h = release_harness
    h.row.context_json["productLock"]["visualIdentity"]["colors"] = ["amber"]
    request = InspectionSubjectRequest(kind="assembly", assemblyId=h.assembly["id"])
    with pytest.raises(AppError, match="SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED"):
        _snapshot(h.row, request, h.row.workspace_id)


def test_new_assembly_cannot_silently_use_old_product_facts(release_harness):
    from viraldy.modules.smart_remake.assembly_snapshots import assembly_expectations

    h = release_harness
    h.row.context_json["productLock"]["visualIdentity"]["colors"] = ["amber"]
    with pytest.raises(AppError, match="SMART_REMAKE_EXPECTATIONS_REQUIRED"):
        assembly_expectations(
            h.row.state_json["draftTimeline"], h.row.state_json, h.row.context_json
        )


@pytest.mark.parametrize("historical_requirements", ["unknown", "changed"])
def test_legacy_qa_requires_known_unchanged_historical_requirements(
    release_harness,
    historical_requirements,
):
    from viraldy.modules.smart_remake.inspection_service import InspectionSubjectRequest, _snapshot

    h = release_harness
    record = h.row.context_json["p0"]["assemblies"]["records"][0]
    record.pop("generationExpectations")
    record.pop("expectationsHash")
    if historical_requirements == "unknown":
        for key in ("requirementsSnapshot", "generationExpectations", "expectationsHash"):
            record["contextSnapshot"].pop(key, None)
    else:
        h.row.context_json["p0"]["requirements"] = {"intent": "Changed current seller requirements"}
    request = InspectionSubjectRequest(kind="assembly", assemblyId=record["id"])
    with pytest.raises(AppError, match="SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED"):
        _snapshot(h.row, request, h.row.workspace_id)
