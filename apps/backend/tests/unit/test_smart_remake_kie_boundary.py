from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import UploadFile

from viraldy.modules.smart_remake import service
from viraldy.modules.smart_remake.engine.config import get_kie_api_key
from viraldy.modules.smart_remake.engine.render_orchestrator import render_smart_remake
from viraldy.modules.smart_remake.engine.schemas import RenderSmartRemakeInput, UploadedMedia
from viraldy.shared.errors.base import AppError


def compiled():
    return {
        "productLock": {"productReference": {"characterName": "Product"}},
        "sceneMap": {
            "targetDuration": 8,
            "sceneCount": 1,
            "scenes": [
                {
                    "displayOrder": 0,
                    "chainType": "ROOT",
                    "parentSceneId": None,
                    "characterNames": ["Product"],
                    "prompt": "Scene",
                    "imagePrompt": "Product on a desk",
                    "videoPrompt": "Show the product",
                }
            ],
        },
    }


def media():
    return UploadFile(
        filename="product.png",
        file=BytesIO(b"product"),
        headers={
            "content-type": "image/png",
        },
    )


def arguments():
    return {
        "settings": SimpleNamespace(ai_mode="live"),
        "compile_result": compiled(),
        "product_image": media(),
        "provider": "kie",
        "project_name": "Seller video",
        "audio_required": False,
    }


def test_kie_health_reports_configuration_without_exposing_key(monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    monkeypatch.setenv("KIE_API_KEY", "not-a-real-key")
    payload = service.health_payload(SimpleNamespace(ai_mode="live"))
    assert payload["kieConfigured"] is True
    assert "kie" in payload["providers"]
    assert "not-a-real-key" not in str(payload)
    fixture = service.health_payload(SimpleNamespace(ai_mode="fixture"))
    assert fixture["providers"] == ["fixture"]


@pytest.mark.asyncio
async def test_kie_validates_then_enqueues_without_inline_provider_call(monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    monkeypatch.setenv("KIE_API_KEY", "not-a-real-key")
    captured = []

    async def submit(input_data):
        captured.append(input_data)
        return {"status": "submitted", "repairProject": {"id": "persisted"}}

    result = await service.render_request(**arguments(), submit_render=submit)
    assert result["status"] == "submitted"
    assert captured[0].provider == "kie"
    assert captured[0].productImage.bytes == b"product"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case,code",
    [
        ("key", "KIE_NOT_CONFIGURED"),
        ("queue", "KIE_DURABLE_JOB_REQUIRED"),
        ("fixture", "SMART_REMAKE_FIXTURE_MODE"),
    ],
)
async def test_kie_fails_closed_before_paid_dispatch(monkeypatch, case, code):
    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    monkeypatch.setenv("KIE_API_KEY", "" if case == "key" else "not-a-real-key")
    values = arguments()
    if case == "fixture":
        values["settings"] = SimpleNamespace(ai_mode="fixture")
    with pytest.raises(AppError) as error:
        await service.render_request(**values)
    assert error.value.code == code


@pytest.mark.asyncio
async def test_kie_never_falls_through_to_inline_flowkit():
    from viraldy.modules.smart_remake.engine.errors import SmartRemakeValidationError

    input_data = RenderSmartRemakeInput(
        **compiled(),
        productImage=UploadedMedia(bytes=b"product", mime_type="image/png"),
        projectName="Seller video",
        provider="kie",
    )
    with pytest.raises(SmartRemakeValidationError) as error:
        await render_smart_remake(input_data)
    assert error.value.code == "KIE_DURABLE_JOB_REQUIRED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value,code",
    [
        ("targetDuration", 24, "INVALID_SMART_REMAKE_DURATION"),
        ("aspectRatio", "16:9", "INVALID_SMART_REMAKE_ASPECT_RATIO"),
    ],
)
async def test_kie_rejects_unsupported_output_before_queue(monkeypatch, field, value, code):
    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    monkeypatch.setenv("KIE_API_KEY", "not-a-real-key")
    values = arguments()
    values["compile_result"]["sceneMap"][field] = value
    if field == "targetDuration":
        values["compile_result"]["sceneMap"]["sceneCount"] = 3
        values["compile_result"]["sceneMap"]["scenes"] *= 3

    async def submit(_):
        pytest.fail("Invalid output must not be queued")

    with pytest.raises(AppError) as error:
        await service.render_request(**values, submit_render=submit)
    assert error.value.code == code


def test_empty_kie_key_is_not_configured(monkeypatch):
    monkeypatch.delenv("KIE_API_KEY", raising=False)
    assert get_kie_api_key() == ""


@pytest.mark.asyncio
async def test_legacy_live_render_requires_key_then_owned_intake(monkeypatch):
    import json
    from importlib import import_module
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from viraldy.modules.smart_remake import kie_workflow

    router = import_module("viraldy.modules.smart_remake.router")

    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    monkeypatch.setenv("KIE_API_KEY", "not-a-real-key")
    monkeypatch.setattr(router, "require_workspace_permission", AsyncMock())
    submit = AsyncMock(return_value={"status": "submitted", "repairProject": {"id": "owned"}})
    monkeypatch.setattr(kie_workflow, "enqueue_kie_render", submit)
    monkeypatch.setattr(router, "_repair_service", lambda *_: pytest.fail("Legacy path called"))
    values = dict(
        workspace_id=uuid4(),
        current_user=object(),
        db=object(),
        settings=SimpleNamespace(ai_mode="live"),
        compile_result=json.dumps(compiled()),
        product_image=media(),
        product_url=None,
        provider="kie",
        project_name="Seller video",
        audio_required=False,
        request_id="test",
        idempotency_key=None,
    )
    with pytest.raises(AppError) as error:
        await router.render_smart_remake_route(**values)
    assert error.value.code == "SMART_REMAKE_IDEMPOTENCY_KEY_REQUIRED"
    submit.assert_not_awaited()
    values["idempotency_key"] = "same-logical-render"
    with pytest.raises(AppError) as error:
        await router.render_smart_remake_route(**values)
    assert error.value.code == "SMART_REMAKE_INTAKE_REQUIRED"
    submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_kie_repair_route_cannot_dispatch_in_fixture_mode(monkeypatch):
    from importlib import import_module
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from viraldy.modules.smart_remake import kie_workflow
    from viraldy.modules.smart_remake.repair_schemas import RepairSceneRequest

    router = import_module("viraldy.modules.smart_remake.router")

    monkeypatch.setattr(router, "require_workspace_permission", AsyncMock())
    repository = SimpleNamespace(
        project=AsyncMock(
            return_value=SimpleNamespace(
                state_json={"provider": "kie"},
            )
        )
    )
    monkeypatch.setattr(
        router, "_repair_service", lambda *_: SimpleNamespace(repository=repository)
    )
    submit = AsyncMock()
    monkeypatch.setattr(kie_workflow, "enqueue_kie_repair", submit)
    with pytest.raises(AppError) as error:
        await router.repair_smart_remake_scene(
            workspace_id=uuid4(),
            project_id=uuid4(),
            scene_id=uuid4(),
            payload=RepairSceneRequest(
                expectedRevision=1,
                prompt="scene",
                imagePrompt="image",
                videoPrompt="video",
                idempotencyKey="same-logical-repair",
            ),
            current_user=object(),
            db=object(),
            settings=SimpleNamespace(ai_mode="fixture"),
            request_id="test",
        )
    assert error.value.code == "SMART_REMAKE_FIXTURE_MODE"
    submit.assert_not_awaited()
