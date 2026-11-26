"""Paid video requests follow the saved grouped plan, never an implicit Fast tier."""

from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from viraldy.modules.smart_remake.engine import kie_adapter
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.service import health_payload, require_openai_images
from viraldy.shared.errors.base import AppError

IMAGES = ["https://8.8.8.8/opening.png", "https://8.8.8.8/final.png"]


def group_request(**changes):
    values = {
        "scenes": [
            {
                "id": "a",
                "targetDurationFrames": 72,
                "videoPrompt": "ACTION_A",
                "imagePrompt": "LAYOUT_A",
            },
            {
                "id": "b",
                "targetDurationFrames": 120,
                "videoPrompt": "ACTION_B",
                "imagePrompt": "LAYOUT_B",
            },
        ],
        "segments": [
            {"renderUnitId": "a", "inFrame": 0, "outFrame": 72},
            {"renderUnitId": "b", "inFrame": 72, "outFrame": 192},
        ],
        "reference_image_urls": IMAGES,
        "product_lock": {"productName": "Pink cup", "mustPreserve": ["round handle"]},
    }
    return kie_adapter.build_kie_group_request(**{**values, **changes})


def test_group_prompt_has_exact_timestamps_and_each_scene_direction():
    request = group_request()
    assert request["model"] == "veo-3-1"
    payload = request["input"]
    assert payload["model"] == "veo3_lite"
    assert payload["generation_type"] == "FIRST_AND_LAST_FRAMES_2_VIDEO"
    assert payload["image_urls"] == IMAGES
    assert payload["duration"] == 8 and payload["aspect_ratio"] == "9:16"
    assert "enable_fallback" not in payload
    assert all(
        value in payload["prompt"]
        for value in [
            "00:00.000",
            "00:03.000",
            "00:08.000",
            "ACTION_A",
            "ACTION_B",
            "LAYOUT_A",
            "LAYOUT_B",
            "Pink cup",
            "round handle",
        ]
    )
    assert "Use split screen only where the scene explicitly calls for it" in payload["prompt"]


@pytest.mark.parametrize(
    "segments",
    [
        [{"renderUnitId": "a", "inFrame": 0, "outFrame": 72}],
        [
            {"renderUnitId": "a", "inFrame": 0, "outFrame": 72},
            {"renderUnitId": "b", "inFrame": 71, "outFrame": 191},
        ],
        [
            {"renderUnitId": "a", "inFrame": 0, "outFrame": 72},
            {"renderUnitId": "b", "inFrame": 72, "outFrame": 193},
        ],
        [
            {"renderUnitId": "a", "inFrame": False, "outFrame": 72},
            {"renderUnitId": "b", "inFrame": 72, "outFrame": 192},
        ],
    ],
)
def test_invalid_group_ranges_are_rejected_before_paid_submission(segments):
    with pytest.raises(SmartRemakeError):
        group_request(segments=segments)


def test_reference_limit_and_explicit_lite_are_enforced():
    with pytest.raises(SmartRemakeError):
        group_request(reference_image_urls=[*IMAGES, "https://8.8.8.8/four.png"])
    request = group_request()["input"]
    with pytest.raises(SmartRemakeError):
        kie_adapter.validate_kie_video_input({**request, "model": "veo3_fast"})


def test_single_scene_repair_also_selects_lite():
    request = kie_adapter.build_kie_video_request(
        scene={"videoPrompt": "Repair the lid action"}, product_image_url=IMAGES[0]
    )
    assert request["input"]["model"] == "veo3_lite"


def test_health_exposes_provider_readiness_without_credentials(monkeypatch):
    monkeypatch.setenv("KIE_API_KEY", "kie-test-secret")
    settings = SimpleNamespace(ai_mode="live", openai_api_key=SecretStr("openai-test-secret"))
    result = health_payload(settings)
    assert result["openaiImagesConfigured"] is True
    assert result["kieVideoModel"] == "veo3_lite"
    assert result["openaiImageModel"] == "gpt-image-2.6-sunburst"
    assert "secret" not in str(result)


@pytest.mark.parametrize(
    "mode,key,code",
    [
        ("fixture", SecretStr("fixture-key"), "SMART_REMAKE_FIXTURE_MODE"),
        ("live", None, "OPENAI_IMAGES_NOT_CONFIGURED"),
    ],
)
def test_openai_generation_guard_fails_before_queuing(mode, key, code):
    with pytest.raises(AppError) as error:
        require_openai_images(SimpleNamespace(ai_mode=mode, openai_api_key=key))
    assert error.value.code == code


def test_worker_budget_covers_sequential_image_and_video_calls():
    from viraldy.modules.jobs.registry import JobType, get_job_definition

    job = get_job_definition(JobType.SMART_REMAKE_KIE.value)
    # Four manually separated groups, including image edit, two reference uploads,
    # polling, download, layout extraction and technical probes at default limits.
    call_budget = 4 * (180 + 2 * 90 + 900 + 120 + 120 + 2 * 90)
    assert job.soft_timeout_seconds >= call_budget
    assert job.hard_timeout_seconds > job.soft_timeout_seconds
