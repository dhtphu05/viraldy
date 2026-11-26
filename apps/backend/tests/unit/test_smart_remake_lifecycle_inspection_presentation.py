from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from viraldy.modules.smart_remake import inspection_presentation as module
from viraldy.shared.errors.base import AppError


def test_current_reports_bind_snapshot_and_active_assembly(monkeypatch):
    row = SimpleNamespace(
        context_json={
            "p0": {
                "assemblies": {"activeAssemblyId": "active"},
                "inspections": {
                    "reports": [
                        {
                            "id": "current",
                            "contextHash": "same",
                            "subjectRequest": {"kind": "assembly", "assemblyId": "active"},
                        },
                        {
                            "id": "stale",
                            "contextHash": "old",
                            "subjectRequest": {"kind": "scene", "sceneId": "s", "versionId": "v"},
                        },
                        {
                            "id": "history",
                            "contextHash": "same",
                            "subjectRequest": {"kind": "assembly", "assemblyId": "previous"},
                        },
                        {"id": "invalid"},
                    ]
                },
            }
        }
    )
    monkeypatch.setattr(module, "_snapshot", lambda *a: {})
    monkeypatch.setattr(module, "_context_hash", lambda *a: "same")
    assert module.current_report_ids(row, uuid4()) == ["current"]

    def stopped(*args):
        raise AppError("SMART_REMAKE_USE_STOPPED", "Stopped", 403)

    monkeypatch.setattr(module, "_snapshot", stopped)
    assert module.current_report_ids(row, uuid4()) == []


async def test_evidence_preview_matches_exact_hash_clock_and_omits_foreign_key():
    workspace = uuid4()
    prefix = f"workspaces/{workspace}/smart-remake/project/"
    version = {"storageKey": prefix + "clip", "mediaHash": "clip-hash", "frameCount": 192}
    state = {"scenes": [{"id": "s", "versions": [version]}]}
    row = SimpleNamespace(
        state_json=state,
        context_json={
            "sourceFrameCount": 384,
            "p0": {
                "assets": {
                    "source": {"storageKey": prefix + "source", "mediaHash": "source-hash"},
                    "product": {"storageKey": prefix + "product", "mediaHash": "product-hash"},
                    "character": {"storageKey": "foreign/input", "mediaHash": "forbidden"},
                },
                "planHistory": [{"stateSnapshot": state}],
                "assemblies": {
                    "records": [
                        {
                            "storageKey": prefix + "final",
                            "mediaHash": "final-hash",
                            "timeline": {"totalFrames": 192},
                            "stateSnapshot": state,
                        }
                    ]
                },
            },
        },
    )
    media = SimpleNamespace(url=AsyncMock(side_effect=lambda key: "authorized/" + key))
    result = await module.evidence_previews(row, media, workspace)
    assert len(result) == 6
    assert len(media.url.await_args_list) == 4
    assert {item["timebase"] for item in result} == {"source", "image", "raw_group", "final"}
    assert "forbidden" not in str(result)
    assert all("storageKey" not in item for item in result)


def test_clock_fields_join_virtual_clock_only_to_authorized_raw_bytes(monkeypatch):
    from viraldy.modules.smart_remake import inspection_mappings

    raw = {"mediaId": "subject", "mediaHash": "a" * 64, "timebase": "raw_group",
           "frameCount": 192, "url": "private-raw"}
    virtual = {"mediaId": "scene-local:binding", "mediaHash": "a" * 64,
               "timebase": "scene_local", "frameCount": 48,
               "playbackTimebase": "raw_group", "playbackMediaId": "subject",
               "playbackMediaHash": "a" * 64}
    mapping = {"from": {**{key: virtual[key] for key in ("mediaId", "mediaHash", "timebase")},
                        "inFrame": 0, "outFrame": 48},
               "to": {**{key: raw[key] for key in ("mediaId", "mediaHash", "timebase")},
                      "inFrame": 72, "outFrame": 120},
               "reportId": "frozen-report"}
    monkeypatch.setattr(inspection_mappings, "inspection_mapping_projection",
                        lambda *args: {"virtualMedia": [virtual], "inspectionMappings": [mapping]})
    result = module.inspection_clock_fields(object(), uuid4(), [raw])
    assert result["inspectionMappings"] == [mapping]
    assert result["inspectionMedia"] == [raw, {**virtual, "url": "private-raw"}]
    # A virtual zero is not raw zero: the server exposes the playback clock and offset.
    assert result["inspectionMappings"][0]["to"]["inFrame"] == 72
    result = module.inspection_clock_fields(object(), uuid4(), [])
    assert result == {"inspectionMappings": [], "inspectionMedia": []}
