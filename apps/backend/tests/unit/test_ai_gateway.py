from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

import viraldy.modules.adaptations.provider as adaptation_provider_module
import viraldy.modules.ai_gateway.http_client as http_client_module
from viraldy.modules.ai_gateway.context import ViraldyOperationContextV1
from viraldy.modules.ai_gateway.http_client import OpenAICompatibleClient, extract_message_json
from viraldy.modules.ai_gateway.operations import (
    AI_OPERATION_DEFINITIONS,
    AiOperationName,
    build_ai_operation_fixture,
    get_ai_operation_definition,
)
from viraldy.modules.ai_gateway.readiness import ai_readiness
from viraldy.modules.ai_gateway.repository import _run
from viraldy.modules.ai_gateway.request_identity import structured_request_hash
from viraldy.modules.ai_gateway.schemas import ProviderResponse
from viraldy.modules.products.contracts import build_minimal_product_context
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


def _load_mock_provider() -> ModuleType:
    script = Path(__file__).parents[2] / "scripts" / "mock_openai_provider.py"
    spec = importlib.util.spec_from_file_location("mock_openai_provider", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load mock_openai_provider.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mock_openai_provider = _load_mock_provider()


def test_live_provider_configuration_is_key_ready() -> None:
    ready = ai_readiness(
        Settings(
            ai_mode="live",
            ai_provider="openai_compatible",
            ai_base_url="https://seed-provider.example/v1",
            ai_api_key="test-api-key",
            ai_text_model="seed-text-model",
            ai_vision_model="seed-vision-model",
            asr_provider="openai_compatible",
            asr_model="seed-asr-model",
        )
    )
    missing_key = ai_readiness(
        Settings(
            ai_mode="live",
            ai_provider="openai_compatible",
            ai_base_url="https://seed-provider.example/v1",
            ai_text_model="seed-text-model",
            ai_vision_model="seed-vision-model",
            asr_provider="openai_compatible",
            asr_model="seed-asr-model",
        )
    )

    assert ready.configured is True
    assert ready.state == "configured"
    assert ready.missing == []
    assert ready.capabilities.text_chat is True
    assert ready.capabilities.vision_chat is True
    assert missing_key.configured is False
    assert missing_key.state == "not_configured"
    assert missing_key.missing == ["AI_API_KEY"]


def test_native_openai_readiness_requires_qualification_after_configuration() -> None:
    settings = Settings(
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-openai-key",
    )

    configured = ai_readiness(settings)
    qualified = ai_readiness(settings, live_qualified=True)

    assert configured.configured is True
    assert configured.state == "not_yet_qualified"
    assert configured.capabilities.json_schema is True
    assert configured.capabilities.audio_transcription is True
    assert qualified.state == "qualified"


def test_mock_provider_supports_chat_failure_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(mock_openai_provider.app)

    monkeypatch.setenv("MOCK_AI_FAILURE", "429")
    response = client.post("/v1/chat/completions", headers=_headers(), json=_chat_payload())
    assert response.status_code == 429

    monkeypatch.setenv("MOCK_AI_FAILURE", "500")
    response = client.post("/v1/chat/completions", headers=_headers(), json=_chat_payload())
    assert response.status_code == 500

    monkeypatch.setenv("MOCK_AI_FAILURE", "malformed_json")
    response = client.post("/v1/chat/completions", headers=_headers(), json=_chat_payload())
    assert response.status_code == 200
    assert response.text == "{not-json"


def test_mock_provider_missing_field_breaks_adaptation_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(mock_openai_provider.app)
    monkeypatch.setenv("MOCK_AI_FAILURE", "missing_field")

    response = client.post("/v1/chat/completions", headers=_headers(), json=_adaptation_payload())
    content = response.json()["choices"][0]["message"]["content"]

    with pytest.raises(AppError) as exc_info:
        adaptation_provider_module._validate(json.loads(content))

    assert exc_info.value.code == "ADAPTATION_OUTPUT_INVALID"
    assert "concepts" not in content


def test_mock_provider_adaptation_payload_matches_current_contract() -> None:
    client = TestClient(mock_openai_provider.app)

    response = client.post("/v1/chat/completions", headers=_headers(), json=_adaptation_payload())
    content = response.json()["choices"][0]["message"]["content"]
    output = adaptation_provider_module._validate(json.loads(content))

    assert len(output.concepts) == 3
    assert all(concept.buyer_persona_label for concept in output.concepts)
    assert all(concept.creator_persona for concept in output.concepts)


def test_mock_vision_preserves_supplied_frame_provenance() -> None:
    prompt = (
        "Duration_ms: 4000\n"
        "Frame timestamp_ms=0, storage_key=workspace/frame_000.jpg\n"
        "Frame timestamp_ms=1000, storage_key=workspace/frame_001.jpg\n"
    )

    payload = mock_openai_provider._vision_payload(prompt)
    referenced = {
        key
        for section in (
            payload["hooks"],
            payload["product_appearances"],
            payload["demo"]["steps"],
            payload["proof_moments"],
            payload["ctas"],
            payload["offers"],
        )
        for item in section
        for key in item["frame_storage_keys"]
    }

    assert referenced
    assert referenced <= {
        "workspace/frame_000.jpg",
        "workspace/frame_001.jpg",
    }


def test_mock_vision_distinguishes_golden_pod_draft_and_revision() -> None:
    product_context = json.dumps(
        {"identity": {"category": "pod_personalized_apparel"}},
        separators=(",", ":"),
    )
    draft = mock_openai_provider._vision_payload(
        f'{{"source_filename":"smoke-ugc-draft.mp4","product_context":{product_context}}}'
    )
    revision = mock_openai_provider._vision_payload(
        f'{{"source_filename":"smoke-revision.mp4","product_context":{product_context}}}'
    )

    assert "Pet name: Miles" in draft["on_screen_text"][0]["text"]
    assert "Pet name: Milo" in revision["on_screen_text"][0]["text"]
    assert draft["ctas"][0]["cta_type"] == "product_tag"
    assert revision["ctas"][0]["product_tag_visible"] is True


def test_mock_provider_routes_canonical_operation_context() -> None:
    context = ViraldyOperationContextV1(
        operation=AiOperationName.PATTERN_KIT_EXTRACT,
        request_id=str(uuid4()),
        workspace_id=uuid4(),
        actor_user_id=uuid4(),
        operation_payload={"request": {}, "sources": []},
        schema_version="pattern_kit_v1",
        prompt_version="pattern_kit_extraction_v2",
    )

    operation, parsed_context = mock_openai_provider._operation_context(
        f"Developer instructions\n\n{context.stable_json()}"
    )

    assert operation == AiOperationName.PATTERN_KIT_EXTRACT.value
    assert parsed_context["operation_payload"] == context.operation_payload


def test_gateway_maps_rate_limit_server_error_invalid_json_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        ai_mode="mock",
        ai_base_url="http://mock/v1",
        ai_text_model="mock-text",
        ai_max_retries=0,
    )

    monkeypatch.setattr(http_client_module.httpx, "Client", _client_factory([_response(429)]))
    with pytest.raises(AppError) as exc_info:
        OpenAICompatibleClient(settings).chat_json(_chat_payload())
    assert exc_info.value.code == "AI_PROVIDER_RATE_LIMITED"

    monkeypatch.setattr(http_client_module.httpx, "Client", _client_factory([_response(500)]))
    with pytest.raises(AppError) as exc_info:
        OpenAICompatibleClient(settings).chat_json(_chat_payload())
    assert exc_info.value.code == "AI_PROVIDER_FAILED"

    monkeypatch.setattr(http_client_module.httpx, "Client", _client_factory([_response(200, b"{")]))
    with pytest.raises(AppError) as exc_info:
        OpenAICompatibleClient(settings).chat_json(_chat_payload())
    assert exc_info.value.code == "MODEL_RESPONSE_INVALID"

    monkeypatch.setattr(
        http_client_module.httpx,
        "Client",
        _client_factory([httpx.TimeoutException("timeout")]),
    )
    with pytest.raises(AppError) as exc_info:
        OpenAICompatibleClient(settings).chat_json(_chat_payload())
    assert exc_info.value.code == "AI_PROVIDER_TIMEOUT"


def test_extract_message_json_rejects_malformed_content() -> None:
    response = ProviderResponse(
        payload={"choices": [{"message": {"content": "{bad-json"}}]},
        http_status=200,
        provider_request_id="req",
        latency_ms=1,
    )

    with pytest.raises(AppError) as exc_info:
        extract_message_json(response)

    assert exc_info.value.code == "MODEL_RESPONSE_INVALID"


def test_model_run_populates_private_beta_trace_fields() -> None:
    request_hash = "a" * 64

    run = _run(
        workspace_id=uuid4(),
        processing_job_id=None,
        subject_type="asset",
        subject_id=uuid4(),
        capability="legacy_capability",
        analysis_mode="fixture",
        provider="fixture",
        model="fixture-model",
        prompt_version="prompt_v1",
        response_schema_version="schema_v1",
        request_hash=request_hash,
        input_summary={"source": "unit"},
        operation="media_observation",
        schema_version="media_observation_v1",
        input_hash=request_hash,
        attempt_count=2,
    )

    assert run.capability == "legacy_capability"
    assert run.operation == "media_observation"
    assert run.response_schema_version == "schema_v1"
    assert run.schema_version == "media_observation_v1"
    assert run.request_hash == structured_request_hash(
        operation="media_observation",
        model="fixture-model",
        prompt_version="prompt_v1",
        schema_version="media_observation_v1",
        input_hash=request_hash,
    )
    assert run.input_hash == request_hash
    assert run.attempt == 1
    assert run.attempt_count == 2
    assert run.repair_attempt_count == 0
    assert run.request_id == str(run.id)
    assert run.usage_json == {}


def test_private_beta_ai_operation_registry_is_complete_and_typed() -> None:
    assert set(AI_OPERATION_DEFINITIONS) == {operation.value for operation in AiOperationName}

    for operation in AiOperationName:
        definition = get_ai_operation_definition(operation)
        assert definition.prompt_name
        assert definition.prompt_version
        assert definition.schema_version
        assert definition.timeout_seconds > 0
        assert definition.max_retries >= 0
        assert definition.mock_fixture_available
        assert definition.input_contract.model_fields
        assert definition.output_contract.model_fields

    assert (
        get_ai_operation_definition(AiOperationName.STORYBOARD_IMAGE_GENERATE).model_family
        == "image"
    )
    assert (
        get_ai_operation_definition(AiOperationName.CONCEPT_VIDEO_PREVIEW_GENERATE).model_family
        == "video"
    )


def test_every_ai_operation_has_a_deterministic_contract_valid_fixture() -> None:
    workspace_id = uuid4()
    asset_id = uuid4()
    asset_version_id = uuid4()
    product_id = uuid4()
    version_id = uuid4()
    inputs: dict[AiOperationName, dict[str, object]] = {
        AiOperationName.MEDIA_OBSERVATION: {
            "workspace_id": workspace_id,
            "asset_id": asset_id,
            "asset_version_id": asset_version_id,
        },
        AiOperationName.CREATIVE_DNA_BUILD: {
            "workspace_id": workspace_id,
            "asset_id": asset_id,
            "asset_version_id": asset_version_id,
            "evidence_item_ids": [uuid4()],
        },
        AiOperationName.PATTERN_KIT_EXTRACT: {
            "workspace_id": workspace_id,
            "creative_dna_version_ids": [version_id],
        },
        AiOperationName.VIRAL_KIT_COMPOSE: {
            "workspace_id": workspace_id,
            "product_id": product_id,
            "product_context_version": 1,
            "pattern_kit_version_ids": [version_id],
        },
        AiOperationName.ADAPTATION_GENERATE: {
            "workspace_id": workspace_id,
            "product_id": product_id,
            "product_context_version": 1,
            "creative_dna_version_id": version_id,
        },
        AiOperationName.CAMPAIGN_PACK_GENERATE: {
            "workspace_id": workspace_id,
            "viral_kit_version_id": version_id,
            "concept_id": "concept-1",
        },
        AiOperationName.SELLER_DECISION_SUMMARY: {
            "workspace_id": workspace_id,
            "preflight_run_id": uuid4(),
            "product_name": "SwiftPress Mini Garment Steamer",
            "objective": "Test the Late for Class concept",
        },
        AiOperationName.REVISION_MESSAGE_GENERATE: {
            "workspace_id": workspace_id,
            "preflight_run_id": uuid4(),
            "blocker_codes": ["PRODUCT_NOT_VISIBLE"],
        },
        AiOperationName.STORYBOARD_IMAGE_GENERATE: {
            "workspace_id": workspace_id,
            "viral_kit_version_id": version_id,
            "concept_id": "concept-1",
            "source_asset_ids": [asset_id],
        },
        AiOperationName.CONCEPT_VIDEO_PREVIEW_GENERATE: {
            "workspace_id": workspace_id,
            "viral_kit_version_id": version_id,
            "concept_id": "concept-1",
            "source_asset_ids": [asset_id],
        },
    }

    for operation, payload in inputs.items():
        first = build_ai_operation_fixture(operation, payload)
        second = build_ai_operation_fixture(operation, payload)
        definition = get_ai_operation_definition(operation)
        assert first == second
        assert isinstance(first, definition.output_contract)


@pytest.mark.asyncio
async def test_mock_provider_timeout_switch_is_cancellable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_AI_FAILURE", "timeout")
    task = asyncio.create_task(mock_openai_provider._maybe_fail())
    await asyncio.sleep(0)
    assert not task.done()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer test"}


def _chat_payload() -> dict[str, Any]:
    return {
        "model": "mock",
        "messages": [{"role": "user", "content": "Extract readable on-screen text"}],
    }


def _adaptation_payload() -> dict[str, Any]:
    context = ViraldyOperationContextV1(
        operation=AiOperationName.ADAPTATION_GENERATE,
        request_id=str(uuid4()),
        workspace_id=uuid4(),
        product_context=build_minimal_product_context(
            name="Portable Steamer",
            description="Observable garment refresh",
            market="US",
            metadata_json={"category": "home_travel_appliance"},
        ),
        product_context_version=1,
        objective="Create grounded UGC concepts.",
        target_market="US",
        schema_version="adaptation_v2",
        prompt_version="adaptation_generation_v2_few_shot_v1",
    )
    return {
        "model": "mock",
        "messages": [{"role": "user", "content": context.stable_json()}],
    }


def _response(status_code: int, content: bytes = b'{"ok": true}') -> httpx.Response:
    return httpx.Response(status_code, content=content)


def _client_factory(items: list[httpx.Response | httpx.TimeoutException]):
    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            item = items.pop(0)
            if isinstance(item, httpx.TimeoutException):
                raise item
            return item

    return FakeClient
