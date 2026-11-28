"""Fresh Veo Lite requests use conditioned opening and closing image frames."""

import pytest

from viraldy.modules.smart_remake.engine.errors import SmartRemakeValidationError
from viraldy.modules.smart_remake.engine.kie_adapter import (
    build_kie_group_request,
    build_kie_video_request,
    validate_kie_video_input,
)

FRAMES = ["https://8.8.8.8/opening.png", "https://8.8.8.8/closing.png"]


def group_request(**changes):
    values = {
        "scenes": [{"id": "scene-a", "videoPrompt": "Lift the pink cup slowly."}],
        "segments": [{"renderUnitId": "scene-a", "inFrame": 0, "outFrame": 192}],
        "reference_image_urls": FRAMES,
        "product_lock": {"productName": "Pink cup", "mustPreserve": ["round handle"]},
    }
    return build_kie_group_request(**{**values, **changes})


def test_group_uses_ordered_first_and_last_conditioned_frames():
    payload = group_request(has_character_reference=True)
    assert payload["model"] == "veo-3-1"
    data = payload["input"]
    assert data["model"] == "veo3_lite"
    assert data["generation_type"] == "FIRST_AND_LAST_FRAMES_2_VIDEO"
    assert data["image_urls"] == FRAMES
    assert data["duration"] == 8 and data["aspect_ratio"] == "9:16"
    assert "FIRST image is the exact opening frame" in data["prompt"]
    assert "SECOND image is the exact final frame" in data["prompt"]
    assert "FIRST reference image is the exact target product" not in data["prompt"]
    assert "SECOND reference image is the authorized target character" not in data["prompt"]
    assert all(text in data["prompt"] for text in ("Lift", "Pink cup", "round handle"))


@pytest.mark.parametrize("frames", [[], FRAMES[:1], [*FRAMES, "https://8.8.8.8/product.png"]])
def test_group_requires_both_conditioned_bookends(frames):
    with pytest.raises(SmartRemakeValidationError, match="opening and final"):
        group_request(reference_image_urls=frames)


def test_single_scene_fallback_uses_initial_frame_image_to_video():
    data = build_kie_video_request(
        scene={"videoPrompt": "Lift the pink cup slowly."}, product_image_url=FRAMES[0]
    )["input"]
    assert data["generation_type"] == "FIRST_AND_LAST_FRAMES_2_VIDEO"
    assert data["image_urls"] == FRAMES[:1]
    assert "exact opening frame" in data["prompt"]
    assert "sole uploaded reference image is the exact target product" not in data["prompt"]


@pytest.mark.parametrize("frames", [FRAMES[:1], FRAMES])
def test_native_validation_accepts_provider_first_frame_or_first_last_frames(frames):
    data = {**group_request()["input"], "image_urls": frames}
    validate_kie_video_input(data)


@pytest.mark.parametrize(
    "change",
    [
        {"generation_type": "REFERENCE_2_VIDEO"},
        {"image_urls": []},
        {"image_urls": [*FRAMES, "https://8.8.8.8/product.png"]},
        {"image_urls": [FRAMES[0], None]},
    ],
)
def test_native_validation_rejects_incompatible_mode_or_reference_slots(change):
    with pytest.raises(SmartRemakeValidationError):
        validate_kie_video_input({**group_request()["input"], **change})
