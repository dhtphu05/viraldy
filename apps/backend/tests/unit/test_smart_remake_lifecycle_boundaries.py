"""P0 live entry points must fence the very first provider transmission."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from viraldy.shared.errors.base import AppError


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["live", "LIVE", " live ", "production"])
async def test_live_compile_without_intake_never_reads_or_sends_media(monkeypatch, mode):
    module = import_module("viraldy.modules.smart_remake.timeline_compile")
    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    read = AsyncMock(side_effect=AssertionError("No intake, no media submission"))
    monkeypatch.setattr(module, "read_media", read)
    with pytest.raises(AppError) as raised:
        await module.compile_timeline_request(
            session=object(),
            settings=SimpleNamespace(ai_mode=mode),
            workspace_id=uuid4(),
            mode="smart_remake",
            target_duration="8",
            aspect_ratio="9:16",
            language="vi",
            prompt=None,
            description=None,
            product_url=None,
            product_title=None,
            product_description=None,
            reference_video=None,
            product_image=None,
        )
    assert raised.value.code == "SMART_REMAKE_INTAKE_REQUIRED"
    read.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_live_compile_cannot_bypass_owned_intake(monkeypatch):
    module = import_module("viraldy.modules.smart_remake.router")
    monkeypatch.setattr(module, "require_workspace_permission", AsyncMock())
    compile_legacy = AsyncMock(side_effect=AssertionError("Legacy paid bypass"))
    monkeypatch.setattr(module, "compile_request", compile_legacy)
    with pytest.raises(AppError) as raised:
        await module.compile_smart_remake_route(
            workspace_id=uuid4(),
            current_user=object(),
            db=object(),
            settings=SimpleNamespace(ai_mode="live"),
            mode="smart_remake",
            target_duration="8",
            aspect_ratio="9:16",
            language="vi",
            prompt=None,
            description=None,
            product_url=None,
            product_title=None,
            product_description=None,
            reference_video=None,
            product_image=None,
            timeline_mode=None,
            request_id="test",
        )
    assert raised.value.code == "SMART_REMAKE_INTAKE_REQUIRED"
    compile_legacy.assert_not_awaited()


@pytest.mark.asyncio
async def test_intake_can_be_presented_without_a_compiled_scene_map():
    from viraldy.modules.smart_remake.repair_service import RepairService

    media = SimpleNamespace(url=AsyncMock(return_value="private-preview"))
    row = SimpleNamespace(
        id=uuid4(),
        state_json={
            "id": "project",
            "revision": 1,
            "schemaVersion": 2,
            "phase": "intake",
            "status": "draft",
            "scenes": [],
            "finalVideoUrl": "",
        },
        context_json={
            "p0": {
                "schemaVersion": 1,
                "requirements": {"intent": "Demo"},
                "rights": {},
                "budgetPolicy": {"capUsd": "2.00"},
            },
            "productKey": "private/product",
            "sourceKey": "private/source",
        },
    )
    service = RepairService(SimpleNamespace(), media, uuid4())
    result = await service.present(row)
    assert result["phase"] == "intake"
    assert result["requirements"]["intent"] == "Demo"
    assert result["inspectionMappings"] == []
    assert "downloadUrl" not in result
    assert "productKey" not in result


@pytest.mark.asyncio
async def test_stopped_project_never_exposes_retained_keys_or_media_urls():
    from viraldy.modules.smart_remake.repair_service import RepairService

    media = SimpleNamespace(url=AsyncMock(side_effect=AssertionError("Use stopped")))
    row = SimpleNamespace(
        id=uuid4(),
        context_json={"p0": {"status": "suspended"}},
        state_json={
            "revision": 2,
            "finalStorageKey": "private/final",
            "finalVideoUrl": "expired-url",
            "productImageUrl": "expired-product",
            "scenes": [{"versions": [{"storageKey": "private/clip", "videoUrl": "expired-clip"}]}],
        },
    )
    result = await RepairService(SimpleNamespace(), media, uuid4()).present(row)
    assert "private/" not in str(result)
    assert "expired-" not in str(result)


@pytest.mark.asyncio
async def test_compile_pending_does_not_enter_video_reconciliation(monkeypatch):
    from viraldy.modules.smart_remake.repair_service import RepairService

    module = import_module("viraldy.modules.smart_remake.kie_workflow")
    reconcile = AsyncMock(side_effect=AssertionError("Compile is not a video task"))
    monkeypatch.setattr(module, "reconcile_kie_project", reconcile)
    row = SimpleNamespace(state_json={"provider": "kie"})
    operation = SimpleNamespace(id=uuid4(), status="running", result_json={"kind": "compile"})
    repo = SimpleNamespace(
        project=AsyncMock(return_value=row), running=AsyncMock(return_value=operation)
    )
    service = RepairService(repo, object(), uuid4())
    monkeypatch.setattr(service, "present", AsyncMock(return_value={}))
    result = await service.get(uuid4())
    assert result["pendingOperation"]["kind"] == "compile"
    reconcile.assert_not_awaited()


def test_public_projection_keeps_binding_but_omits_internal_snapshots():
    from viraldy.modules.smart_remake.project_presentation import project_policy_fields

    result = project_policy_fields(
        {
            "p0": {
                "constraintsHash": "binding",
                "inspectionSummary": {"status": "stale", "reason": "trim"},
                "assemblies": {
                    "records": [
                        {
                            "id": "a",
                            "mediaHash": "hash",
                            "stateSnapshot": {"secret": "internal"},
                            "contextSnapshot": {"secret": "internal"},
                        }
                    ]
                },
            }
        }
    )
    assert result["inspectionSummary"]["status"] == "stale"
    assert result["constraintsHash"] == "binding"
    assert "internal" not in str(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["live", "LIVE", " live ", "production"])
async def test_legacy_live_project_does_not_get_unchecked_download(mode):
    from viraldy.modules.smart_remake.repair_service import RepairService

    media = SimpleNamespace(url=AsyncMock(return_value="preview"), download_url=AsyncMock())
    row = SimpleNamespace(
        id=uuid4(),
        context_json={"productKey": "product"},
        state_json={"finalStorageKey": "output", "scenes": []},
    )
    service = RepairService(
        SimpleNamespace(), media, uuid4(), settings=SimpleNamespace(ai_mode=mode)
    )
    result = await service.present(row)
    assert "downloadUrl" not in result
    media.download_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_stopped_project_get_does_not_dispatch_worker(monkeypatch):
    from viraldy.modules.smart_remake.repair_service import RepairService

    module = import_module("viraldy.modules.smart_remake.timeline_service")
    reconcile = AsyncMock(side_effect=AssertionError("Stopped work must stay stopped"))
    monkeypatch.setattr(module, "reconcile_compose_project", reconcile)
    row = SimpleNamespace(
        state_json={"provider": "kie"}, context_json={"p0": {"status": "suspended"}}
    )
    operation = SimpleNamespace(id=uuid4(), status="running", result_json={"kind": "compose"})
    repo = SimpleNamespace(
        project=AsyncMock(return_value=row), running=AsyncMock(return_value=operation)
    )
    service = RepairService(repo, object(), uuid4())
    monkeypatch.setattr(service, "present", AsyncMock(return_value={}))
    await service.get(uuid4())
    reconcile.assert_not_awaited()
