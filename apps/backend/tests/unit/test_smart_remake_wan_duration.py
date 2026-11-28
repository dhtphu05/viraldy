"""Six-second Wan windows retain every scene without changing historical Veo requests."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest
from jsonschema import validate
from test_smart_remake_wan_video import MODEL, SCHEMA, group_args

from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.video_requests import build_group_request


def six_second_args():
    args = group_args()
    for index, scene in enumerate(args["scenes"]):
        scene.update(targetDurationFrames=72, rawDurationFrames=144)
        args["segments"][index].update(inFrame=index * 72, outFrame=(index + 1) * 72)
    return args


def test_six_second_wan_request_uses_actual_duration_in_wire_and_scene_prose():
    args = six_second_args()
    args["reference_analysis"]["audioPlan"] = {
        "music": "upbeat instrumental",
        "dialogue": "observed product explanation",
        "language": "Vietnamese",
        "ambience": "soft room tone",
    }
    before = copy.deepcopy(args)
    request = build_group_request(
        model=MODEL,
        duration_seconds=6,
        resolution="480P",
        audio=True,
        **args,
    )
    validate(request, json.loads(SCHEMA.read_text())["requestSchema"])
    assert request["input"]["duration"] == 6
    assert request["input"]["resolution"] == "480P"
    assert request["input"]["audio"] is True
    prompt = request["input"]["prompt"]
    assert prompt.startswith("Create exactly 6 seconds, vertical 9:16.")
    assert "[00:00.000–00:03.000] SCENE 1" in prompt
    assert "[00:03.000–00:06.000] SCENE 2" in prompt
    assert "8 seconds" not in prompt and "eight seconds" not in prompt
    assert "no sound" not in prompt.lower() and "silent" not in prompt.lower()
    assert "Generate synchronized audio" in prompt
    assert "original synthetic presenter voice" in prompt
    assert "do not imitate the source speaker" in prompt
    assert "no-speech source, do not invent dialogue" in prompt
    assert "upbeat instrumental" in prompt and "observed product explanation" in prompt
    assert "Vietnamese" in prompt and "soft room tone" in prompt
    assert "After 6 seconds" not in prompt
    assert "Lift the pink cup using the right hand" in prompt
    assert "Place the pink cup on the wooden table and release the grip" in prompt
    assert args == before


def test_two_six_second_requests_retain_all_source_actions_in_order():
    requests = []
    for window in range(2):
        args = six_second_args()
        args["scenes"] = [
            {
                "prompt": f"Action number {scene + window * 12 + 1:02d}.",
                "targetDurationFrames": 12,
                "rawDurationFrames": 144,
            }
            for scene in range(12)
        ]
        args["segments"] = [
            {
                "renderUnitId": f"unit-{window}-{scene}",
                "inFrame": scene * 12,
                "outFrame": (scene + 1) * 12,
            }
            for scene in range(12)
        ]
        requests.append(build_group_request(model=MODEL, duration_seconds=6, **args))
    assert len(requests) == 2
    assert sum(request["input"]["duration"] for request in requests) == 12
    for window, request in enumerate(requests):
        prompt = request["input"]["prompt"]
        positions = [
            prompt.index(f"Action number {scene + window * 12 + 1:02d}") for scene in range(12)
        ]
        assert positions == sorted(positions)
        assert "[00:05.500–00:06.000] SCENE 12" in prompt


@pytest.mark.parametrize("model", ["veo3_lite", "veo-3-1"])
def test_veo_cannot_be_dispatched_as_a_six_second_payload(model):
    with pytest.raises(SmartRemakeError) as caught:
        build_group_request(model=model, duration_seconds=6, **six_second_args())
    assert caught.value.code == "KIE_VALIDATION_FAILED"


def test_six_second_wan_rejects_scenes_extending_past_its_frozen_window():
    with pytest.raises(SmartRemakeError) as caught:
        build_group_request(model=MODEL, duration_seconds=6, **group_args())
    assert caught.value.code == "KIE_VALIDATION_FAILED"


@pytest.mark.parametrize("duration", [True, 1, 31, 6.0])
def test_invalid_wan_duration_is_rejected_before_prompt_compilation(duration):
    with pytest.raises(SmartRemakeError) as caught:
        build_group_request(model=MODEL, duration_seconds=duration, **six_second_args())
    assert caught.value.code == "KIE_VALIDATION_FAILED"


def test_wan_short_final_selection_continues_only_to_its_six_second_duration():
    args = six_second_args()
    args["segments"][-1]["outFrame"] = 120
    args["scenes"][-1]["targetDurationFrames"] = 48
    request = build_group_request(model=MODEL, duration_seconds=6, **args)
    assert "After 5 seconds, continue the last action naturally" in request["input"]["prompt"]
    assert request["input"]["duration"] == 6


def test_explicit_eight_second_duration_preserves_historical_veo_request_bytes():
    request = build_group_request(model="veo3_lite", duration_seconds=8, **group_args())
    assert hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest() == (
        "fa1842c0680ffc2f09d4c621564f9bae4d2430f538808d08cde177947c3c18f9"
    )
    assert build_group_request(model=MODEL, duration_seconds=8, **group_args()) == (
        build_group_request(model=MODEL, **group_args())
    )
