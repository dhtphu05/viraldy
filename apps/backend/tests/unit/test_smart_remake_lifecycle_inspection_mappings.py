from __future__ import annotations

import copy
import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake.assembly_snapshots import content_hash, record_assembly
from viraldy.modules.smart_remake.inspection_mappings import inspection_mapping_projection


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.fixture
def retained():
    workspace, project = uuid4(), uuid4()
    prefix = f"workspaces/{workspace}/smart-remake/{project}"
    scenes = [
        {
            "id": f"s{index}",
            "versions": [
                {
                    "id": f"v{index}",
                    "storageKey": f"{prefix}/shared-raw",
                    "mediaHash": digest("shared-raw"),
                    "frameCount": 192,
                }
            ],
        }
        for index in (1, 2)
    ]
    timeline = {
        "fps": 24,
        "totalFrames": 192,
        "items": [
            {
                "id": "i1",
                "renderUnitId": "s1",
                "sourceSceneId": "source1",
                "versionId": "v1",
                "targetStartFrame": 0,
                "targetDurationFrames": 72,
                "inFrame": 24,
                "outFrame": 96,
            },
            {
                "id": "i2",
                "renderUnitId": "s2",
                "sourceSceneId": "source2",
                "versionId": "v2",
                "targetStartFrame": 72,
                "targetDurationFrames": 120,
                "inFrame": 72,
                "outFrame": 192,
            },
        ],
    }
    state = {"scenes": scenes, "draftTimeline": timeline}
    p0 = record_assembly(
        {},
        project_id=str(project),
        timeline=timeline,
        state=state,
        storage_key=f"{prefix}/final",
        media_hash=digest("final"),
        technical_check={"status": "passed", "frameCount": 192},
        constraints_hash=digest("constraints"),
        context_hash=digest("assembly-context"),
        revision=3,
        actor_id="actor",
        operation_id="compose",
    )
    report = {
        "id": "scene-report",
        "schemaVersion": 1,
        "contextHash": digest("old-context"),
        "manifestHash": digest("scene-manifest"),
        "constraintsHash": digest("constraints"),
        "subject": {
            "kind": "scene",
            "projectId": str(project),
            "sceneId": "s1",
            "versionId": "v1",
            "mediaHash": digest("shared-raw"),
            "range": {"inFrame": 48, "outFrame": 120, "fps": 24, "timebase": "raw_group"},
        },
    }
    p0["inspections"] = {"reports": [report], "reviews": []}
    row = SimpleNamespace(
        id=project, workspace_id=workspace, state_json=state, context_json={"p0": p0}
    )
    return row, workspace, p0["assemblies"]["activeAssemblyId"]


def test_exact_trim_offsets_and_frozen_final_segments_are_explicit(retained):
    row, workspace, assembly_id = retained
    before = copy.deepcopy(row)
    projection = inspection_mapping_projection(row, workspace)
    mappings = projection["inspectionMappings"]
    local = next(
        item
        for item in mappings
        if item.get("reportId") == "scene-report" and item["to"]["mediaId"] == "subject"
    )
    assert local["from"]["timebase"] == "scene_local"
    assert (local["from"]["inFrame"], local["from"]["outFrame"]) == (0, 72)
    assert (local["to"]["inFrame"], local["to"]["outFrame"]) == (48, 120)
    assert local["contextHash"] == digest("old-context")
    final = next(
        item
        for item in mappings
        if item.get("assemblyId") == assembly_id
        and item.get("sceneId") == "s1"
        and item["from"]["timebase"] == "final"
    )
    assert final["from"]["mediaHash"] == digest("final")
    assert final["to"]["mediaHash"] == digest("shared-raw")
    assert final["to"]["mediaId"] == "subject"
    assert (final["from"]["inFrame"], final["from"]["outFrame"]) == (0, 72)
    assert (final["to"]["inFrame"], final["to"]["outFrame"]) == (24, 96)
    assert row.state_json == before.state_json and row.context_json == before.context_json
    assert all(
        edge["from"]["timebase"] != "source" and edge["to"]["timebase"] != "source"
        for edge in mappings
    )


def test_twelve_second_assembly_maps_both_six_second_clips(retained):
    row, workspace, assembly_id = retained
    assembly = row.context_json["p0"]["assemblies"]["records"][0]
    assembly["timeline"]["totalFrames"] = 288
    assembly["technicalCheck"]["frameCount"] = 288
    for index, item in enumerate(assembly["timeline"]["items"]):
        item.update(targetStartFrame=index * 144, targetDurationFrames=144, inFrame=0, outFrame=144)
        assembly["stateSnapshot"]["scenes"][index]["versions"][0]["frameCount"] = 144
    assembly["manifest"]["timeline"] = copy.deepcopy(assembly["timeline"])
    assembly["manifestHash"] = content_hash(assembly["manifest"])
    mappings = inspection_mapping_projection(row, workspace)["inspectionMappings"]
    final = [item for item in mappings if item.get("assemblyId") == assembly_id
             and item["from"]["timebase"] == "final" and item["to"]["mediaId"] == "subject"]
    assert {(item["from"]["inFrame"], item["from"]["outFrame"]) for item in final} == {
        (0, 144), (144, 288),
    }


def test_shared_raw_clips_have_unique_virtual_ids_and_real_playback_clock(retained):
    row, workspace, assembly_id = retained
    projection = inspection_mapping_projection(row, workspace)
    virtual = [
        item
        for item in projection["virtualMedia"]
        if item.get("assemblyId") == assembly_id and not item.get("reportId")
    ]
    assert len(virtual) == 2 and len({item["mediaId"] for item in virtual}) == 2
    assert {item["mediaHash"] for item in virtual} == {digest("shared-raw")}
    assert {item["frameCount"] for item in virtual} == {72, 120}
    for item in virtual:
        assert item["timebase"] == "scene_local" and "url" not in item
        assert item["playbackTimebase"] == "raw_group"
        assert item["playbackMediaId"] == "subject"
        assert item["playbackMediaHash"] == item["mediaHash"]
    aliases = [
        item for item in projection["inspectionMappings"] if item["to"]["mediaId"] == "neighbor-s1"
    ]
    assert aliases and all(item["to"]["mediaHash"] == digest("shared-raw") for item in aliases)


def test_current_trim_changes_cannot_rewrite_historical_report_or_assembly_mapping(retained):
    row, workspace, assembly_id = retained
    before = inspection_mapping_projection(row, workspace)
    row.state_json["draftTimeline"]["items"][0].update(inFrame=0, outFrame=72)
    row.state_json["scenes"][0]["versions"][0]["id"] = "new-current-version"
    after = inspection_mapping_projection(row, workspace)
    assert after == before
    assert any(item.get("reportId") == "scene-report" for item in after["inspectionMappings"])
    assert any(item.get("assemblyId") == assembly_id for item in after["inspectionMappings"])


def test_new_expectations_selection_hash_preserves_mapping_and_rejects_mismatch(retained):
    row, workspace, assembly_id = retained
    assembly = row.context_json["p0"]["assemblies"]["records"][0]
    version = assembly["stateSnapshot"]["scenes"][0]["versions"][0]
    version["expectationsHash"] = digest("frozen-generation")
    selection = assembly["manifest"]["selections"][0]
    selection["expectationsHash"] = version["expectationsHash"]
    assembly["manifestHash"] = content_hash(assembly["manifest"])
    mappings = inspection_mapping_projection(row, workspace)["inspectionMappings"]
    assert any(item.get("assemblyId") == assembly_id for item in mappings)
    selection["expectationsHash"] = digest("other-generation")
    assembly["manifestHash"] = content_hash(assembly["manifest"])
    mappings = inspection_mapping_projection(row, workspace)["inspectionMappings"]
    assert not any(item.get("assemblyId") == assembly_id for item in mappings)


def test_foreign_workspace_and_missing_or_invalid_ranges_fail_closed(retained):
    row, workspace, _ = retained
    assert inspection_mapping_projection(row, uuid4()) == {
        "inspectionMappings": [],
        "virtualMedia": [],
    }
    row.context_json["p0"]["assemblies"] = {"records": []}
    report = row.context_json["p0"]["inspections"]["reports"][0]
    original = copy.deepcopy(report)
    for changes in (
        {"outFrame": 193},
        {"inFrame": -1},
        {"outFrame": 48},
        {"inFrame": True},
        {"fps": 30},
        {"timebase": "source"},
    ):
        report["subject"]["range"] = {**original["subject"]["range"], **changes}
        assert not inspection_mapping_projection(row, workspace)["inspectionMappings"]
    report["subject"]["range"] = original["subject"]["range"]
    row.state_json["scenes"][0]["versions"][0].pop("frameCount")
    assert not inspection_mapping_projection(row, workspace)["inspectionMappings"]


@pytest.mark.parametrize(
    "change", ["foreign_key", "hash", "manifest", "missing_frozen", "wrong_project"]
)
def test_assembly_mapping_requires_owned_immutable_manifest_and_versions(retained, change):
    row, workspace, _ = retained
    p0 = row.context_json["p0"]
    p0["inspections"]["reports"] = []
    assembly = p0["assemblies"]["records"][0]
    if change == "foreign_key":
        assembly["storageKey"] = "workspaces/foreign/smart-remake/final"
    elif change == "hash":
        assembly["stateSnapshot"]["scenes"][0]["versions"][0]["mediaHash"] = digest("tampered")
    elif change == "manifest":
        assembly["timeline"]["items"][0]["inFrame"] = 0
    elif change == "missing_frozen":
        assembly.pop("stateSnapshot")
    else:
        assembly["projectId"] = str(uuid4())
    assert not inspection_mapping_projection(row, workspace)["inspectionMappings"]


def test_reports_require_exact_retained_subject_identity_and_context(retained):
    row, workspace, _ = retained
    row.context_json["p0"]["assemblies"] = {"records": []}
    report = row.context_json["p0"]["inspections"]["reports"][0]
    original = copy.deepcopy(report)
    for key, value in (
        ("mediaHash", digest("other")),
        ("projectId", str(uuid4())),
        ("versionId", "missing"),
    ):
        report["subject"] = {**original["subject"], key: value}
        assert not inspection_mapping_projection(row, workspace)["inspectionMappings"]
    report["subject"] = original["subject"]
    report.pop("contextHash")
    assert not inspection_mapping_projection(row, workspace)["inspectionMappings"]


@pytest.mark.parametrize("missing", ["id", "workspace_id"])
def test_incomplete_historical_rows_cannot_invent_ownership(retained, missing):
    row, workspace, _ = retained
    delattr(row, missing)
    assert inspection_mapping_projection(row, workspace) == {
        "inspectionMappings": [],
        "virtualMedia": [],
    }


def test_null_frozen_state_or_subject_omits_mapping_instead_of_breaking_project_get(retained):
    row, workspace, _ = retained
    row.context_json["p0"]["assemblies"]["records"][0]["stateSnapshot"] = None
    row.context_json["p0"]["inspections"]["reports"][0]["subject"] = None
    assert inspection_mapping_projection(row, workspace) == {
        "inspectionMappings": [],
        "virtualMedia": [],
    }


@pytest.mark.parametrize(
    "container", ["record", "plan_history", "timeline", "technical", "assemblies", "inspections"]
)
def test_malformed_historical_containers_are_omitted_without_crashing(retained, container):
    row, workspace, assembly_id = retained
    p0 = row.context_json["p0"]
    if container == "record":
        p0["assemblies"]["records"].append(None)
    elif container == "plan_history":
        p0["planHistory"] = [None]
    elif container == "timeline":
        p0["assemblies"]["records"][0]["timeline"] = None
    elif container == "technical":
        p0["assemblies"]["records"][0]["technicalCheck"] = None
    else:
        p0[container] = None
    projection = inspection_mapping_projection(row, workspace)
    if container in {"timeline", "technical", "assemblies"}:
        assert not any(
            edge.get("assemblyId") == assembly_id for edge in projection["inspectionMappings"]
        )
    if container == "inspections":
        assert not any(edge.get("reportId") for edge in projection["inspectionMappings"])
