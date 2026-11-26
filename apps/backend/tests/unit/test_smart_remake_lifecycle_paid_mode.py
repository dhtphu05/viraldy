# ruff: noqa: F811 -- shared offline fixture is injected by pytest.
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from test_smart_remake_inspection_runtime import video  # noqa: F401
from test_smart_remake_lifecycle_paid_conditioning import check, conditioning  # noqa: F401

from viraldy.modules.smart_remake.generation_budget import require_generation_policy
from viraldy.modules.smart_remake.image_workflow import prepare_scene_image
from viraldy.modules.smart_remake.kie_workflow import KieWorkflow
from viraldy.modules.smart_remake.project_intake import assert_input_binding
from viraldy.modules.smart_remake.project_policy import assert_project_policy
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["fixture", "mock", " MOCK "])
async def test_explicit_offline_mode_blocks_all_generation_provider_calls(
    conditioning, monkeypatch, mode
):
    value = conditioning
    assert_project_policy(value.row, purpose="generation")
    await assert_input_binding(value.row, value.repair.media)
    # Real Settings with configured ceilings/keys must still be safe after a
    # queued live operation is picked up by a worker restarted in offline mode.
    value.repair.settings = Settings.model_construct(ai_mode=mode)
    for stage in ("IMAGE", "VIDEO", "INSPECTION"):
        monkeypatch.setenv(f"SMART_REMAKE_P0_MAX_{stage}_USD", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-key")
    monkeypatch.setenv("KIE_API_KEY", "offline-test-key")
    client = SimpleNamespace(
        edit=AsyncMock(), upload_file=AsyncMock(), create_task=AsyncMock(), get_task=AsyncMock()
    )
    workflow = KieWorkflow(value.repair, client=client, image_client=client)
    with pytest.raises(AppError, match="SMART_REMAKE_FIXTURE_MODE"):
        await prepare_scene_image(
            repair=value.repair,
            row=value.row,
            operation=value.operation,
            index=0,
            compiled_scene={"imagePrompt": "Product on a table"},
            image_client=client,
            save=AsyncMock(),
            ensure_active=lambda: None,
        )
    with pytest.raises(AppError, match="SMART_REMAKE_FIXTURE_MODE"):
        await workflow._task(value.row, value.operation, 0, reconcile_only=False)
    value.operation.result_json = {
        **value.operation.result_json,
        "tasks": {"0": {"taskId": "already-accepted", "status": "submitted"}},
    }
    with pytest.raises(AppError, match="SMART_REMAKE_FIXTURE_MODE"):
        await workflow._task(value.row, value.operation, 0, reconcile_only=True)
    with pytest.raises(AppError, match="SMART_REMAKE_FIXTURE_MODE"):
        await check(value)
    assert value.calls == []
    for call in (client.edit, client.upload_file, client.create_task, client.get_task):
        call.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("settings", [None, SimpleNamespace()])
async def test_legacy_offline_doubles_without_runtime_mode_remain_compatible(
    conditioning, settings
):
    value = conditioning
    value.repair.settings = settings
    await require_generation_policy(value.repair, value.row)
