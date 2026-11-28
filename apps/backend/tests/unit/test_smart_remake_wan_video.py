"""Wan requests use their published contract and preserve owned scene directions."""
from __future__ import annotations

import copy
import json
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from jsonschema import validate

from viraldy.modules.smart_remake import generation_budget, provider_execution
from viraldy.modules.smart_remake.engine import kie_client
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError

MODEL = "wan/3-0-video"
SCHEMA = Path(__file__).parents[1] / "fixtures/smart_remake/kie_wan_request_schema.json"


def input_data():
    return {
        "prompt": "The same fictional presenter holds the pink cup, then places it on the table.",
        "first_frame_url": "https://8.8.8.8/opening.png",
        "last_frame_url": "https://8.8.8.8/ending.png",
        "resolution": "720P", "duration": 8, "aspect_ratio": "9:16", "audio": False,
    }


def group_args():
    scenes = [{
        "prompt": "Lift the exact pink cup.", "imagePrompt": "A hand beside the pink cup.",
        "videoPrompt": "Lift the pink cup using the right hand.",
        "targetDurationFrames": 96, "rawDurationFrames": 192,
    }, {
        "prompt": "Place the cup on the wooden table.", "imagePrompt": "A hand holds the cup.",
        "videoPrompt": "Place the pink cup on the wooden table and release the grip.",
        "targetDurationFrames": 96, "rawDurationFrames": 192,
    }]
    return {
        "scenes": scenes,
        "segments": [{"renderUnitId": "a", "inFrame": 0, "outFrame": 96},
                     {"renderUnitId": "b", "inFrame": 96, "outFrame": 192}],
        "reference_image_urls": ["https://8.8.8.8/opening.png", "https://8.8.8.8/ending.png"],
        "product_lock": {"productName": "Pink cup", "mustPreserve": ["Pink rigid body"]},
        "reference_analysis": {"setting": "wooden table", "subjectPresence": "person"},
    }


def test_wan_group_payload_matches_captured_schema_and_keeps_all_actions():
    from viraldy.modules.smart_remake.engine.video_requests import build_group_request

    args = group_args()
    before = copy.deepcopy(args)
    request = build_group_request(model=MODEL, **args)
    validate(request, json.loads(SCHEMA.read_text())["requestSchema"])
    assert request["model"] == MODEL
    assert set(request["input"]) == set(input_data())
    assert request["input"]["first_frame_url"] == args["reference_image_urls"][0]
    assert request["input"]["last_frame_url"] == args["reference_image_urls"][1]
    assert request["input"]["resolution"] == "720P"  # Retained plans without a resolution.
    prompt = request["input"]["prompt"]
    assert "Lift the pink cup using the right hand" in prompt
    assert "Place the pink cup on the wooden table and release the grip" in prompt
    assert "Pink rigid body" in prompt
    assert "[00:00.000–00:04.000] SCENE 1" in prompt
    assert "[00:04.000–00:08.000] SCENE 2" in prompt
    assert args == before


def test_legacy_group_dispatch_preserves_the_entire_saved_veo_request():
    from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_group_request
    from viraldy.modules.smart_remake.engine.video_requests import build_group_request

    original = build_kie_group_request(**group_args())
    assert build_group_request(model="veo3_lite", **group_args()) == original
    assert build_group_request(model="veo-3-1", **group_args()) == original


def test_wan_explicit_480p_matches_provider_schema_without_changing_clip_scope():
    from viraldy.modules.smart_remake.engine.video_requests import build_group_request

    request = build_group_request(model=MODEL, resolution="480P", **group_args())
    validate(request, json.loads(SCHEMA.read_text())["requestSchema"])
    assert request["input"]["resolution"] == "480P"
    assert request["input"]["duration"] == 8
    assert request["input"]["first_frame_url"] == group_args()["reference_image_urls"][0]


def test_wan_resolution_setting_does_not_change_a_legacy_veo_payload():
    from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_group_request
    from viraldy.modules.smart_remake.engine.video_requests import build_group_request

    assert build_group_request(model="veo3_lite", resolution="480P", **group_args()) == (
        build_kie_group_request(**group_args())
    )


def test_wan_prompt_limit_does_not_truncate_saved_directions():
    from viraldy.modules.smart_remake.engine.video_requests import validate_video_input

    data = input_data()
    data["prompt"] = "x" * 20000
    validate_video_input(MODEL, data)
    assert len(data["prompt"]) == 20000
    data["prompt"] += "x"
    with pytest.raises(SmartRemakeError, match="20,000"):
        validate_video_input(MODEL, data)
    assert len(data["prompt"]) == 20001


@pytest.mark.parametrize("changes", [
    {"duration": 1}, {"duration": 31}, {"duration": True}, {"duration": "8"},
    {"resolution": "720p"}, {"audio": 0}, {"aspect_ratio": "adaptive"},
    {"first_frame_url": "http://127.0.0.1/private"},
    {"last_frame_url": "http://localhost/private"},
    {"prompt": " "}, {"first_frame_url": None},
    {"reference_image_urls": ["https://8.8.8.8/actor.png"]},
    {"generation_type": "FIRST_AND_LAST_FRAMES_2_VIDEO"},
    {"image_urls": ["https://8.8.8.8/opening.png"]}, {"model": "veo3_lite"},
])
def test_wan_rejects_invalid_or_mixed_model_fields_before_network(changes):
    from viraldy.modules.smart_remake.engine.video_requests import validate_video_input

    with pytest.raises(SmartRemakeError):
        validate_video_input(MODEL, {**input_data(), **changes})


@pytest.mark.parametrize("duration", [2, 8, 16, 30])
def test_wan_duration_obeys_provider_range(duration):
    from viraldy.modules.smart_remake.engine.video_requests import validate_video_input

    validate_video_input(MODEL, {**input_data(), "duration": duration})


def test_unsupported_model_fails_closed():
    from viraldy.modules.smart_remake.engine.video_requests import (
        build_group_request,
        validate_video_input,
    )

    with pytest.raises(SmartRemakeError):
        build_group_request(model="wan/unknown", **group_args())
    with pytest.raises(SmartRemakeError):
        validate_video_input("wan/unknown", input_data())


@pytest.mark.asyncio
async def test_wan_create_sends_only_exact_model_schema_once():
    calls = []
    before = input_data()

    def respond(request):
        calls.append(request)
        body = json.loads(request.content)
        validate(body, json.loads(SCHEMA.read_text())["requestSchema"])
        assert body == {"model": MODEL, "input": before}
        assert request.url.path == "/api/v1/jobs/createTask"
        return httpx.Response(200, json={"code": 200, "data": {"taskId": "wan-task"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        result = await kie_client.KieClient(api_key="test-key", http_client=http).create_task(
            model=MODEL, input_data=before,
        )
    assert result == {"task_id": "wan-task", "status": "queued"}
    assert len(calls) == 1 and before == input_data()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timeout", "server_error", "missing_task"])
async def test_wan_uncertain_create_never_retries_or_falls_back(failure):
    calls = []

    def respond(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private", request=request)
        data = (
            {"code": 500, "msg": "error"}
            if failure == "server_error" else {"code": 200, "data": {}}
        )
        return httpx.Response(200, json=data)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        with pytest.raises(SmartRemakeError) as caught:
            await kie_client.KieClient(api_key="test-key", http_client=http).create_task(
                model=MODEL, input_data=input_data(),
            )
    assert caught.value.code == "KIE_SUBMISSION_UNCERTAIN" and len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("state,expected", [("waiting", "queued"), ("generating", "processing"),
                                           ("success", "completed"), ("fail", "failed")])
async def test_wan_polls_unified_only_and_retains_actual_credit_receipt(state, expected):
    calls = []

    def respond(request):
        calls.append(request)
        assert request.url.path == "/api/v1/jobs/recordInfo"
        data = {"taskId": "wan-task", "model": MODEL, "state": state, "creditsConsumed": 0,
                "response": {"resultUrls": ["https://8.8.8.8/video.mp4"]},
                "failCode": "500", "failMsg": "Internal Error"}
        return httpx.Response(200, json={"code": 200, "data": data})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        result = await kie_client.KieClient(api_key="test-key", http_client=http).get_task(
            "wan-task", model=MODEL,
        )
    assert result["status"] == expected and result["receipt"] == {"creditsConsumed": 0}
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["veo-3-1", None])
async def test_wan_task_model_mismatch_or_missing_model_is_not_accepted(model):
    def respond(request):
        return httpx.Response(200, json={"code": 200, "data": {
            "taskId": "wan-task", "state": "waiting", **({"model": model} if model else {}),
        }})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        with pytest.raises(SmartRemakeError) as caught:
            await kie_client.KieClient(api_key="test-key", http_client=http).get_task(
                "wan-task", model=MODEL,
            )
    assert caught.value.code == "KIE_INVALID_RESPONSE"


@pytest.mark.asyncio
async def test_wan_missing_fee_is_not_reported_as_zero():
    def respond(request):
        return httpx.Response(200, json={"code": 200, "data": {
            "taskId": "wan-task", "model": MODEL, "state": "waiting",
        }})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        result = await kie_client.KieClient(api_key="test-key", http_client=http).get_task(
            "wan-task", model=MODEL,
        )
    assert "receipt" not in result and "usage" not in result


@pytest.mark.asyncio
async def test_wan_physical_submit_and_poll_evidence_use_the_actual_model(monkeypatch):
    monkeypatch.setattr(provider_execution, "_verified_tls", lambda response, host: True)

    @asynccontextmanager
    async def owned_transport(self):
        def respond(request):
            data = ({"taskId": "wan-task"} if request.method == "POST" else
                    {"taskId": "wan-task", "model": MODEL, "state": "waiting"})
            return httpx.Response(200, json={"code": 200, "data": data})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            yield http

    monkeypatch.setattr(kie_client.KieClient, "_client", owned_transport)
    client = kie_client.KieClient(api_key="test-key")
    for operation in ["kie.tasks.create", "kie.tasks.get"]:
        if operation.endswith("create"):
            await client.create_task(model=MODEL, input_data=input_data())
        else:
            await client.get_task("wan-task", model=MODEL)
        result = generation_budget.generation_execution_receipt(
            client, attempt_id=str(uuid4()), request_hash="a" * 64, provider="kie",
            model=MODEL, operation=operation, task_id="wan-task",
        )
        assert result["executionEvidence"]["model"] == MODEL
        assert result["executionEvidence"]["operation"] == operation
