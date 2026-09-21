from __future__ import annotations

import asyncio

import httpx
import pytest

from viraldy.modules.smart_remake.engine.compiler import (
    compile_smart_remake_scene_map_with_diagnostics,
)
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError, SmartRemakeSecurityError
from viraldy.modules.smart_remake.engine.gemini_client import HttpGeminiClient
from viraldy.modules.smart_remake.engine.guards import assert_no_reference_video_in_render_payload
from viraldy.modules.smart_remake.fixture import FixtureGeminiClient
from viraldy.modules.smart_remake.service import _duration


@pytest.mark.parametrize("value, expected", [("8", 8), ("16", 16)])
def test_smart_remake_accepts_only_supported_durations(value: str, expected: int) -> None:
    assert _duration(value) == expected


def test_smart_remake_rejects_other_durations() -> None:
    with pytest.raises(Exception, match="8 or 16"):
        _duration("24")


@pytest.mark.parametrize("duration, scene_count", [(8, 1), (16, 2)])
def test_smart_remake_compiler_creates_eight_second_scene_units(
    duration: int, scene_count: int
) -> None:
    result = compile_smart_remake_scene_map_with_diagnostics(
        {
            "mode": "smart_remake",
            "targetDuration": duration,
            "aspectRatio": "9:16",
            "language": "English",
            "referenceAnalysis": {
                "subjectPresence": "hands_only",
                "format": "product demo",
                "cameraStyle": {"angle": "front", "framing": "close-up", "movement": "smooth"},
                "setting": {"locationType": "desk", "backgroundElements": []},
                "creativeConcept": {
                    "hook": "show product",
                    "adType": "product_demo",
                    "productMoment": "result",
                },
                "motionBeats": [
                    {"startSecond": 0, "endSecond": duration / 2, "action": "demo action"},
                    {"startSecond": duration / 2, "endSecond": duration, "action": "show result"},
                ],
                "audioPlan": {"mode": "silent", "referenceMusic": {"mode": "none"}},
                "pacingPlan": {"pace": "fast", "shotCount": 2, "averageShotDuration": duration / 2},
                "openingShot": {"durationSeconds": 1, "firstAction": "show product"},
            },
            "productLock": {
                "mode": "auto",
                "productName": "Target Product",
                "productType": "product",
                "visualIdentity": {"colors": []},
                "productUsage": {},
                "mustPreserve": ["shape"],
                "canChange": ["background"],
                "forbiddenErrors": [],
                "productReference": {
                    "characterName": "Target Product",
                    "entityType": "visual_asset",
                },
            },
        }
    )
    assert result["sceneMap"]["sceneCount"] == scene_count
    assert len(result["sceneMap"]["scenes"]) == scene_count
    assert all(scene["shotPlan"]["targetDuration"] == 8 for scene in result["sceneMap"]["scenes"])


def test_fixture_gemini_returns_analysis_and_product_lock_shapes() -> None:
    client = FixtureGeminiClient()
    analysis = asyncio.run(
        client.generate_json(system_instruction="", prompt="analyze 16 second video")
    )
    product = asyncio.run(
        client.generate_json(system_instruction="", prompt="generate product lock")
    )
    assert len(analysis["motionBeats"]) == 4
    assert product["productReference"]["characterName"] == "Target Product"


def test_render_guard_rejects_reference_video_fields() -> None:
    with pytest.raises(SmartRemakeSecurityError, match="Reference video"):
        assert_no_reference_video_in_render_payload({"sceneMap": {"referenceVideoUrl": "secret"}})


def test_live_gemini_timeout_is_reported_as_smart_remake_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TimeoutClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> TimeoutClient:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def post(self, *_: object, **__: object) -> httpx.Response:
            raise httpx.ReadTimeout(
                "mock timeout", request=httpx.Request("POST", "https://example.test")
            )

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        "viraldy.modules.smart_remake.engine.gemini_client.httpx.AsyncClient",
        TimeoutClient,
    )

    with pytest.raises(SmartRemakeError, match="timed out"):
        asyncio.run(
            HttpGeminiClient().generate_json(system_instruction="system", prompt="prompt")
        )
