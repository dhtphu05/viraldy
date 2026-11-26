from types import SimpleNamespace
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake.budgeted_analysis import (
    LedgerGeminiClient,
    inspection_invoke,
    request_snapshot,
)
from viraldy.shared.errors.base import AppError


def test_request_snapshot_hashes_bytes_and_keeps_clock_metadata():
    one = request_snapshot("system", "prompt", [{"bytes": b"first", "mime_type": "image/png"}])
    two = request_snapshot("system", "prompt", [{"bytes": b"second", "mime_type": "image/png"}])
    assert one != two
    assert "bytes" not in one["media"][0]
    assert one["media"][0]["mimeType"] == "image/png"
    for media in ([{"url": "https://external.test/a.png"}], [{"bytes": "not-bytes"}]):
        with pytest.raises(AppError):
            request_snapshot("system", "prompt", media)


async def test_limited_analysis_requires_configured_bound(monkeypatch):
    monkeypatch.delenv("SMART_REMAKE_P0_MAX_ANALYSIS_USD", raising=False)
    client = LedgerGeminiClient(None, uuid4(), uuid4(), uuid4(), uuid4())

    async def bounded_project():
        return SimpleNamespace(context_json={"p0": {"budgetPolicy": {
            "capUsd": "2", "maxAttempts": 5, "maxDurationSeconds": 3600,
        }}})

    monkeypatch.setattr(client, "_project", bounded_project)
    with pytest.raises(AppError) as missing:
        await client.generate_json(system_instruction="system", prompt="prompt")
    assert missing.value.code == "SMART_REMAKE_STAGE_BOUND_REQUIRED"
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_ANALYSIS_USD", "0")
    with pytest.raises(AppError) as zero:
        await client.generate_json(system_instruction="system", prompt="prompt")
    assert zero.value.code == "SMART_REMAKE_STAGE_BOUND_REQUIRED"
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_ANALYSIS_USD", "1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AppError) as no_provider:
        await client.generate_json(system_instruction="system", prompt="prompt")
    assert no_provider.value.code == "SMART_REMAKE_MODEL_NOT_CONFIGURED"


async def test_inspection_payload_requires_prompt_before_any_provider():
    invoke = inspection_invoke(None, uuid4(), uuid4(), uuid4(), uuid4())
    with pytest.raises(AppError):
        await invoke({"systemInstruction": "system", "media": []})
    assert invoke.model_profile["maxAttempts"] == 1
    with pytest.raises(AppError):
        await invoke({"systemInstruction": "system", "prompt": "inspect", "media": ["url"]})
